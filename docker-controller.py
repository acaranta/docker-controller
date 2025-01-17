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

def publish(mqttClient, route, payload, msgtype, reqconfig):
    resp = {}
    resp['type'] = msgtype
    resp['host'] = deamonName
    resp['message'] = payload
    resp['reqconf'] = reqconfig
    return mqttClient.publish(mqttRootTopic + "/" + deamonName + "/" + route, json.dumps(resp))

def on_connect(client, userdata, flags, rc, properties):
    global Connected                #Use global variable
    if rc == 0:
        print("Connected to broker")
        Connected = True                #Signal connection
    else:
        print("Connection failed")
        Connected = False


def on_disconnect(client, userdata, flags, rc, properties):
    global Connected                #Use global variable
    print("Connection failed")
    Connected = False


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
              if 'image' in composeconfig["services"][svc]:
                  if composeconfig["services"][svc]["image"] == checkimg or "library/" + composeconfig["services"][svc]["image"] == checkimg:
                      publish(client,"status", "Pulling " + checkimg + " in " + file_name, "info", imgdata)
                      rescmd = "cd " + yamlpath + " ; ./stack.sh " + file_name + " pull " + svc + " ; "
                      print("Executing : " + rescmd)
                      os.system(rescmd)
                      publish(client,"status", "Updating " + checkimg + " in " + file_name, "info", imgdata)
                      rescmd = "cd " + yamlpath + " ; ./stack.sh " + file_name + " up " + svc + " ; "
                      print("Executing : " + rescmd)
                      os.system(rescmd)
        if rescmd:
          print("Done for : " + checkimg)
          print("##################################################")
          publish(client,"status", "Work done for " + checkimg, "info", imgdata)
        else:
          print("Image " + checkimg + " not found in compose files")
          print("##################################################")
          publish(client,"status", "Image " + checkimg + " not found in compose files", "info", imgdata)
    elif action == "pruning":
        rescmd = "docker system prune --volumes -a -f"
        print("##################################################")
        print("Executing : " + rescmd)
        pruningresult = subprocess.check_output(rescmd, shell=True).decode("utf-8")
        print("Pruning Results : " + pruningresult)
        print("##################################################")
        publish(client,"status", "Pruning done : " + pruningresult, "info", imgdata)
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
                      publish(client,"status", "Restarting " + checkimg + " in " + file_name, "info", imgdata)
                      rescmd = "cd " + yamlpath + " ; ./stack.sh " + file_name + " restart " + svc + " ; "
                      print("Executing : " + rescmd)
                      os.system(rescmd)
            if rescmd:
              print("Done restarting : " + checkimg)
              print("##################################################")
              publish(client,"status", "Work done for " + checkimg, "info", imgdata)
            else:
              print("Image " + checkimg + " not found in compose files")
              print("##################################################")
              publish(client,"status", "Image " + checkimg + " not found in compose files", "info", imgdata)
        else:
            print("##################################################")
            print("Restart by image : image name contains forbidden characters")
            print("##################################################")
            publish(client,"status", "Image restart failed, '"+checkimg+"' contains illegal characters ", "info", imgdata)
    elif action == "restart-container":
        container = imgdata['container'] 
        if special_match(container):
            rescmd = "docker restart " + container
            print("##################################################")
            print("Trying to restart " + container)
            try:
              restartresult = subprocess.check_output(rescmd, shell=True).decode("utf-8")
              print("Restart Results : " + restartresult)
              print("##################################################")
              publish(client,"status", "Restart done : " + restartresult, "info", imgdata)
            except Exception as e:
              print("Restart Results : " + str(e))
              print("##################################################")
              publish(client,"status", "Restart NOT OK see logs", "info", imgdata)
        else:
            print("##################################################")
            print("Container restart : container name contains forbidden characters")
            print("##################################################")
            publish(client,"status", "Restart failed, '"+container+"' contains illegal characters ", "info", imgdata)
    elif action == "stop-container":
        container = imgdata['container'] 
        if special_match(container):
            rescmd = "docker stop " + container
            print("##################################################")
            print("Trying to stop " + container)
            restartresult = subprocess.check_output(rescmd, shell=True).decode("utf-8")
            print("Stop Results : " + restartresult)
            print("##################################################")
            publish(client,"status", "Stop done : " + restartresult, "info", imgdata)
        else:
            print("##################################################")
            print("Container stop : container name contains forbidden characters")
            print("##################################################")
            publish(client,"status", "stop failed, '"+container+"' contains illegal characters ", "info", imgdata)
    elif action == "container-list":
            rescmd = "docker ps --format='{{json .}}'"
            print("##################################################")
            restartresult = subprocess.check_output(rescmd, shell=True).decode("utf-8")
            print("Docker PS Done")
            print("##################################################")
            publish(client,"pslist", restartresult, "pslist", imgdata)

    else: 
        print("##################################################")
        print("Action unknown : "+action)
        print("##################################################")
        publish(client,"status", "Action unknown, '"+action+"'" , "info", imgdata)
    


#Setup MQTT Connection
Connected = False 
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, deamonName)
client.on_connect = on_connect   
client.on_disconnect = on_disconnect   
client.on_message = on_message
while True:
    while Connected != True:    #Wait for connection
        try:
            client.connect(mqttServer, mqttPort)
            client.loop_start()
            client.subscribe(mqttTopics)
            time.sleep(5)
        except (ConnectionError, OSError) as e:
            print("Error connecting")
            sys.exit(1)

    try:
        while Connected == True: #wait in loop
          time.sleep(1)
        print("Detected connection error to MQTT, exiting")
    except KeyboardInterrupt:
        print ("exiting")

    client.disconnect()
    client.loop_stop()

