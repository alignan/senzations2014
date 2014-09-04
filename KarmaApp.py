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
# - Take care of WiFI initialization
# - React on received message, use message ID to maybe filter responses to my request, etc

import mosquitto
import time
import os
import pyGalileo as pyGal

MY_ID = "ABCD"

wait_until_subscribed = 1

ETHERNET_ADDR = "169.254.1.232"
ETHERNET_MASK = "255.255.0.0"

# Fixed Location, latitude, longitude
LOCATION = "43.94305555555555, 15.45346111111111"

# When connected, subscribe to out topics of interest
def on_connect(mosq, obj, rc):
    mosq.subscribe(TOPIC_ALARM_ASSIST, 0)
    mosq.subscribe(TOPIC_ALARM_SEVERE, 0)
    mosq.subscribe(TOPIC_MIC_ALARM, 0)

    print("rc: " + str(rc))

def on_message(mosq, obj, msg):
    print "Message received with topic: %s, QoS: %s, Payload %s\n"%(msg.topic, str(msg.qos), str(msg.payload))
    
def on_publish(mosq, obj, mid):
    print("Message published with ID: " + str(mid))

def on_subscribe(mosq, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))

    # Wait until we received the last mid to release the initial lock
    wait_until_subscribed = 0

def on_log(mosq, obj, level, string):
    print(string)

def create_json_message(msg_type, msg_val, msg_string):
    string = "{alarm_type:"
    string = string + msg_type + "; alarm_value:"
    string = string + msg_val + "; alarm_msg:"
    string = string + msg_string + "; location:"
    string = string + location + "; id:"
    string = string + MY_ID
    return string

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

TOPIC_ALARM_SEVERE = "/senzations/citizenkarmakit/panic_alert"
TOPIC_ALARM_ASSIST = "/senzations/citizenkarmakit/assistant_alert"
TOPIC_MIC_ALARM    = "/senzations/citizenkarmakit/mic_alert"

MSG_ALARM_SEVERE = "Someone needs urgent help at"
MSG_ALARM_ASSIST = "Someone could use some help at"
MSG_ALARM_SHOUT  = "A shout has been detected at"

ID_ALARM_SEVERE = 3
ID_ALARM_MIC    = 2
ID_ALARM_ASSIST = 1

buttonPin_severe = 2
buttonPin_assistant = 3

sensor_mic = "A0"
SENSOR_MIC_THR = 150

MQTT_SERVER = "iot.eclipse.org"
MQTT_PORT = 1883

# configure digital port for button readout
pyGal.pinMode(buttonPin_severe, pyGal.INPUT)
pyGal.pinMode(buttonPin_assistant, pyGal.INPUT)

# connect to a mosquitto test broker on the web
mqttc.connect(MQTT_SERVER, MQTT_PORT, 60)

# And create an alarm flag, the alarms should be placed from lower priority to higher,
# so it will overwrite any low-priority alarm/event
alarm_flag = ""

# With a string to send the data
data_string = ""

while True:
    mqttc.loop(1)
    pressed_severe = pyGal.digitalRead(buttonPin_severe)
    pressed_assist = pyGal.digitalRead(buttonPin_assistant)

    if not wait_until_subscribed:

        # Checks the assist button status
        if (pressed_assist == pyGal.HIGH):
            alarm_flag = TOPIC_ALARM_ASSIST
            data_string = create_json_message(ID_ALARM_ASSIST, "HIGH", MSG_ALARM_ASSIST)
        
        # Check the status of the analog sensors
        sensor_mic_val = pyGal.analogRead(sensor_mic)

        if (sensor_mic_val >= SENSOR_MIC_THR):
            alarm_flag = TOPIC_MIC_ALARM
            data_string = create_json_message(ID_ALARM_MIC, str(sensor_mic_val), MSG_ALARM_SHOUT)

        # Check if severe alarm button has been pressed
        if (pressed_severe == pyGal.HIGH):
            alarm_flag = TOPIC_ALARM_SEVERE
            data_string = create_json_message(ID_ALARM_SEVERE, "HIGH", MSG_ALARM_SEVERE)

        if (alarm_flag):
            print "Sending a message to the broker in 1 second:"
            print data_string

            time.sleep(1)

            # Check to which topic should I post, the priority is post to critital alarms first!
            # mqttc.publish(alarm_flag, data_string)

            # Clear the alarm afterwards
            alarm_flag = ""

        #  and data (we not collect data)
        data_string = ""

    # and backoff a bit
    time.sleep(0.1)