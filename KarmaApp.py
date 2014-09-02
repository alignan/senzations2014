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

wait_until_subscribed = 1

ETHERNET_ADDR = "169.254.1.232"
ETHERNET_MASK = "255.255.0.0"

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

ID_ALARM_SEVERE = 3
ID_ALARM_MIC    = 2
ID_ALARM_ASSIST = 1

buttonPin_severe = 2
buttonPin_assistant = 3

sensor_mic = "A0"
SENSOR_MIC_THR = 150

# configure digital port for button readout
pyGal.pinMode(buttonPin_severe, pyGal.INPUT)
pyGal.pinMode(buttonPin_assistant, pyGal.INPUT)

# connect to a mosquitto test broker on the web
mqttc.connect("test.mosquitto.org", 1883, 60)

# And create an alarm flag, the alarms should be placed from lower priority to higher,
# so it will overwrite any low-priority alarm/event
alarm_flag = ""

# With a string to send the data
data_string = ""

while True:
    mqttc.loop(1)
    pressed_severe = pyGal.digitalRead(buttonPin_severe)
    pressed_assist = pyGal.digitalRead(buttonPin_assistant)

    if (wait_until_subscribed) return

    data_string = str(ID_ALARM_ASSIST) + ":"
    if (pressed_assist == pyGal.HIGH):  
      alarm_flag = TOPIC_ALARM_ASSIST
      data_string = data_string + "HIGH"
    else:
      data_string = data_string + "LOW"
    
    # Check the status of the analog sensors
    sensor_mic_val = pyGal.analogRead(sensor_mic)

    data_string = data_string + " " + str(ID_ALARM_MIC) + ":" + str(sensor_mic_val) + ":"
    if (sensor_mic_val >= SENSOR_MIC_THR):
        alarm_flag = TOPIC_MIC_ALARM
        data_string = data_string + "HIGH"
    else:
        data_string = data_string + "LOW"

    # Check if any button was pressed
    data_string = data_string + " " + str(ID_ALARM_SEVERE) + ":"
    if (pressed_severe == pyGal.HIGH):
        alarm_flag = TOPIC_ALARM_SEVERE
        data_string = data_string + "HIGH"
    else:
        data_string = data_string + "LOW"

    if (alarm_flag):
        print "Sending a message to the broker in 1 second:"
        print alarm_flag, data_string

        time.sleep(1)

        # Check to which topic should I post, the priority is post to critital alarms first!
        mqttc.publish(alarm_flag, data_string)

        # Clear the alarm afterwards
        alarm_flag = ""

    #  and data (we not collect data)
    data_string = ""

    # and backoff a bit
    time.sleep(0.1)