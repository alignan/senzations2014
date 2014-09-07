#!/usr/bin/python

# DreamTeam presents:
# Very basic and simple Citizen Karma Kit application, reuses most of the
# Basic mqtt client example for the Galileo tutorial
#
# As the client is subscribed to the same message topic, it will also print 
# the message that it received. 
#
# TODO list:
# - Set proper QoS values
# - Take care of WiFI initialization by ourselves

import mosquitto
import time
from datetime import datetime
import os
import pyGalileo as pyGal
import random

VERSION_REF = "Version 0.9b"

# To initialize the ETH0 interface
ETHERNET_ADDR = "169.254.1.232"
ETHERNET_MASK = "255.255.0.0"

# Fixed Location, latitude, longitude
LOCATION = "43.94305555555555, 15.45346111111111"

TOPIC_ALARM_SEVERE = "/senzations/citizenkarmakit/panic_alert"
TOPIC_ALARM_ASSIST = "/senzations/citizenkarmakit/assistant_alert"
TOPIC_MIC_ALARM    = "/senzations/citizenkarmakit/mic_alert"
TOPIC_RESPONSE     = "/senzations/citizenkarmakit/responses"

MSG_ALARM_SEVERE = "Someone needs urgent help at"
MSG_ALARM_ASSIST = "Someone could use some help at"
MSG_ALARM_SHOUT  = "A shout has been detected at"

ID_ALARM_SEVERE = "3"
ID_ALARM_MIC    = "2"
ID_ALARM_ASSIST = "1"

lock = 0
timeout = 0

buttonPin_severe = 2
buttonPin_assistant = 3

sensor_mic = "A0"
SENSOR_MIC_THR = 800

send_led = 7
recv_led = 8

pyGal.pinMode(send_led, pyGal.OUTPUT)
pyGal.pinMode(recv_led, pyGal.OUTPUT)

pyGal.digitalWrite(send_led, pyGal.LOW)
pyGal.digitalWrite(recv_led, pyGal.LOW)

my_id = 0
release_subscribe_lock = 1

data_string = ""

MQTT_SERVER = "iot.eclipse.org"
MQTT_PORT = 1883

# When connected, subscribe to out topics of interest
def on_connect(mosq, obj, rc):
    print "MQTT. Connected !!!"
    mosq.subscribe(TOPIC_ALARM_ASSIST, 0)
    mosq.subscribe(TOPIC_ALARM_SEVERE, 0)
    mosq.subscribe(TOPIC_MIC_ALARM, 0)
    mosq.subscribe(TOPIC_RESPONSE, 0)
    # print("rc: " + str(rc))

def on_message(mosq, obj, msg):
    global lock
    if msg.payload == data_string:
        print "Alert published"
    else:
        if msg.topic == TOPIC_RESPONSE:
            print "Message received with topic: %s, QoS: %s, Payload %s\n"%(msg.topic, str(msg.qos), str(msg.payload))

            # Parse the message
            data = msg.payload.split(" ")

            if (data[0] == str(my_id)):
                lock = 0
                pyGal.digitalWrite(recv_led, pyGal.HIGH)
                pyGal.digitalWrite(send_led, pyGal.LOW)
                print "Response received from {0}, help is on its way !!!".format(data[1])
            
    
def on_publish(mosq, obj, mid):
    print("MQTT: Message published with ID: " + str(mid))

def on_subscribe(mosq, obj, mid, granted_qos):
    global release_subscribe_lock
    msg_sub = "MQTT: Subscribed: " + str(mid) + " to " + str(granted_qos)
    if mid == 1:
        msg_sub = msg_sub + TOPIC_ALARM_ASSIST
    elif mid == 2:
        msg_sub = msg_sub + TOPIC_ALARM_SEVERE
    elif mid == 3:
        msg_sub = msg_sub + TOPIC_MIC_ALARM
    elif mid == 4:
        msg_sub = msg_sub + TOPIC_RESPONSE
    else:
        msg_sub = "UNKNOWN TOPIC !!! "
    print msg_sub

    release_subscribe_lock = 0

def on_log(mosq, obj, level, string):
    print(string)

def create_json_message(msg_type, msg_val, msg_string):
    global my_id
    my_id = str(random.randrange(0,65535))
    string = '{ "alarm_type":"'
    string = string + msg_type + '", "alarm_value":"'
    string = string + msg_val + '", "alarm_msg":"'
    string = string + msg_string + '", "location":"'
    string = string + LOCATION + '", "id":"'
    string = string + my_id + '", "timestamp":"'
    string = string + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '" }'
    return string

def start_application():
    # And create an alarm flag, the alarms should be placed from lower priority to higher,
    # so it will overwrite any low-priority alarm/event
    alarm_flag = ""

    # With a string to send the data
    global data_string
    global lock
    global timeout

    while True:
        mqttc.loop(1)

        if (lock < 1) or (release_subscribe_lock < 1):

            pressed_severe = pyGal.digitalRead(buttonPin_severe)
            pressed_assist = pyGal.digitalRead(buttonPin_assistant)

            # Checks the assist button status
            if (pressed_assist == pyGal.HIGH):
                print "ASSIST button pressed"
                alarm_flag = TOPIC_ALARM_ASSIST
                data_string = create_json_message(ID_ALARM_ASSIST, "HIGH", MSG_ALARM_ASSIST)
            
            # Check the status of the analog sensors
            sensor_mic_val = pyGal.analogRead(sensor_mic)

            if (sensor_mic_val >= SENSOR_MIC_THR):
                print "MIC event detected"
                alarm_flag = TOPIC_MIC_ALARM
                data_string = create_json_message(ID_ALARM_MIC, str(sensor_mic_val), MSG_ALARM_SHOUT)

            # Check if severe alarm button has been pressed
            if (pressed_severe == pyGal.HIGH):
                print "SEVERE button pressed"
                alarm_flag = TOPIC_ALARM_SEVERE
                data_string = create_json_message(ID_ALARM_SEVERE, "HIGH", MSG_ALARM_SEVERE)

            if (alarm_flag):
                print "MQTT: Sending a message to the broker in 1 second:"
                print data_string

                lock = 1
                time.sleep(1)

                # Check to which topic should I post, the priority is post to critital alarms first!
                mqttc.publish(alarm_flag, data_string)

                # Clear the alarm afterwards
                alarm_flag = ""

                # Turn on the RED led
                pyGal.digitalWrite(recv_led, pyGal.LOW)
                pyGal.digitalWrite(send_led, pyGal.HIGH)

                # And restart the counter
                timeout = 0

        # Increment the counter
        timeout = timeout + 1
        if timeout > 45:
            print "\n*** Timeout, unlocking\n"
            lock = 0
            timeout = 0
            pyGal.digitalWrite(send_led, pyGal.LOW)
            # pyGal.digitalWrite(recv_led, pyGal.LOW)

        # and backoff a bit
        time.sleep(0.1)

# Create an ethernet backdoor if directly connected to the board
os.system("telnetd -l /bin/sh");
os.system("ifconfig eth0 {0} netmask {1} up".format(ETHERNET_ADDR, ETHERNET_MASK));

# Create the WiFI connection
# FIXME: Do it here or prior executing this? block below will fail if skips a check

# Create moquitto client instance and configure call backs for event handling
mqttc = mosquitto.Mosquitto()
mqttc.on_message = on_message
mqttc.on_connect = on_connect
mqttc.on_publish = on_publish
mqttc.on_subscribe = on_subscribe

# configure digital port for button readout
pyGal.pinMode(buttonPin_severe, pyGal.INPUT)
pyGal.pinMode(buttonPin_assistant, pyGal.INPUT)

# connect to a mosquitto test broker on the web
mqttc.connect(MQTT_SERVER, MQTT_PORT, 60)

# Launch
print "*****************************************"
print "CITY KARMA APPLICATION {0}".format(VERSION_REF)
print "*****************************************"

start_application()