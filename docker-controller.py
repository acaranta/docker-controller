#!/usr/bin/python3
import json 
import yaml
import glob
import sys
import os
import re
import time
import subprocess
import socket
import paho.mqtt.client as mqtt

from pprint import pprint
from datetime import datetime

#### OPTS ####
mqttServer = "127.0.0.1"
if os.getenv('MQTT_SRV') != None:
  mqttServer = os.getenv('MQTT_SRV')
mqttPort = 1883
if os.getenv('MQTT_PORT') != None:
  mqttPort = int(os.getenv('MQTT_PORT'))
yamlpath = "/appdata"
if os.getenv('YAML_PATH') != None:
  yamlpath = os.getenv('YAML_PATH')
deamonName = socket.gethostname()
if os.getenv('CTRL_HOST') != None:
  deamonName = os.getenv('CTRL_HOST')

mqttRootTopic = "dkr-ctrl"
mqttTopics = [(mqttRootTopic + "/" + deamonName + "/action",1),(mqttRootTopic + "/ALL/action",2)]

def special_match(strg, search=re.compile(r'[^a-zA-Z0-9\-_:/]').search):
  return not bool(search(strg))

def publish(mqttClient, route, payload, msgtype):
    resp = {}
    resp['type'] = msgtype
    resp['host'] = deamonName
    resp['message'] = payload
    return mqttClient.publish(mqttRootTopic + "/" + deamonName + "/" + route, json.dumps(resp))

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to broker")
        global Connected                #Use global variable
        Connected = True                #Signal connection
    else:
        print("Connection failed")


def on_message(client, userdata, message):
    data = message.payload
    receive=data.decode("utf-8")
    imgdata = json.loads(receive)
    print ("Message received: "  + str(imgdata))

    action = imgdata['action'] 
    if action == "imgupdate":
        checkimg = imgdata['imgfull'] 
        print("\n##################################################")
        print(datetime.now())
        print("Received hook call for " + checkimg)
        print("--------------------------------------------------")
        # Find if image is used in compose files, prepare cmd if so and run it
        rescmd = ""
        list_of_files = glob.glob(yamlpath + '/docker*.yml')           # create the list of file
        for file_name in list_of_files:
          with open(file_name, 'r') as file:
            composeconfig = yaml.load(file, Loader=yaml.FullLoader)
            for svc in composeconfig["services"]:
              if composeconfig["services"][svc]["image"] == checkimg or "library/" + composeconfig["services"][svc]["image"] == checkimg:
                 publish(client,"status", "Pulling " + checkimg + " in " + file_name, "info")
                 rescmd = "cd " + yamlpath + " ; ./stack.sh " + file_name + " pull " + svc + " ; "
                 print("Executing : " + rescmd)
                 os.system(rescmd)
                 publish(client,"status", "Updating " + checkimg + " in " + file_name, "info")
                 rescmd = "cd " + yamlpath + " ; ./stack.sh " + file_name + " up " + svc + " ; "
                 print("Executing : " + rescmd)
                 os.system(rescmd)
        if rescmd:
          print("Done for : " + checkimg)
          print("##################################################")
          publish(client,"status", "Work done for " + checkimg, "info")
        else:
          print("Image " + checkimg + " not found in compose files")
          print("##################################################")
          publish(client,"status", "Image " + checkimg + " not found in compose files", "info")
    elif action == "pruning":
        rescmd = "docker system prune --volumes -f"
        print("##################################################")
        print("Executing : " + rescmd)
        pruningresult = subprocess.check_output(rescmd, shell=True).decode("utf-8")
        print("Pruning Results : " + pruningresult)
        print("##################################################")
        publish(client,"status", "Pruning done : " + pruningresult, "info")
    elif action == "restart-image":
        checkimg = imgdata['imgfull'] 
        if special_match(checkimg):
            print("\n##################################################")
            print(datetime.now())
            print("Restart containers by image : " + checkimg)
            print("--------------------------------------------------")
            # Find if image is used in compose files, prepare cmd if so and run it
            rescmd = ""
            list_of_files = glob.glob(yamlpath + '/docker*.yml')           # create the list of file
            for file_name in list_of_files:
              with open(file_name, 'r') as file:
                composeconfig = yaml.load(file, Loader=yaml.FullLoader)
                for svc in composeconfig["services"]:
                  if composeconfig["services"][svc]["image"] == checkimg or "library/" + composeconfig["services"][svc]["image"] == checkimg:
                     publish(client,"status", "Restarting " + checkimg + " in " + file_name, "info")
                     rescmd = "cd " + yamlpath + " ; ./stack.sh " + file_name + " restart " + svc + " ; "
                     print("Executing : " + rescmd)
                     os.system(rescmd)
            if rescmd:
              print("Done restarting : " + checkimg)
              print("##################################################")
              publish(client,"status", "Work done for " + checkimg, "info")
            else:
              print("Image " + checkimg + " not found in compose files")
              print("##################################################")
              publish(client,"status", "Image " + checkimg + " not found in compose files", "info")
        else:
            print("##################################################")
            print("Restart by image : image name contains forbidden characters")
            print("##################################################")
            publish(client,"status", "Image restart failed, '"+checkimg+"' contains illegal characters ", "info")
    elif action == "restart-container":
        container = imgdata['container'] 
        if special_match(container):
            rescmd = "docker restart " + container
            print("##################################################")
            print("Trying to restart " + container)
            restartresult = subprocess.check_output(rescmd, shell=True).decode("utf-8")
            print("Restart Results : " + restartresult)
            print("##################################################")
            publish(client,"status", "Restart done : " + restartresult, "info")
        else:
            print("##################################################")
            print("Container restart : container name contains forbidden characters")
            print("##################################################")
            publish(client,"status", "Restart failed, '"+container+"' contains illegal characters ", "info")
    elif action == "container-list":
            rescmd = "docker ps --format='{{json .}}'"
            print("##################################################")
            restartresult = subprocess.check_output(rescmd, shell=True).decode("utf-8")
            print("Docker PS Done")
            print("##################################################")
            publish(client,"pslist", restartresult, "pslist")

    else: 
        print("##################################################")
        print("Action unknown : "+action)
        print("##################################################")
        publish(client,"status", "Action unknown, '"+action+"'" , "info")
    


#Setup MQTT Connection
Connected = False 
client = mqtt.Client(deamonName)
client.on_connect = on_connect   
client.on_message = on_message
client.connect(mqttServer, mqttPort)
client.loop_start()
while Connected != True:    #Wait for connection
    time.sleep(0.1)
client.subscribe(mqttTopics)

try:
    while not client.connected_flag and not client.bad_connection_flag: #wait in loop
	time.sleep(1)
except KeyboardInterrupt:
    print ("exiting")

client.disconnect()
client.loop_stop()
