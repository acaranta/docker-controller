#!/usr/bin/python3
import asyncio
import aioredis
import json 
import yaml
import glob
import sys
import os
import subprocess

from pprint import pprint
from datetime import datetime

#### OPTS ####
redisserver = "localhost:6379"
if os.getenv('REDIS_SRV') != None:
  redisserver = os.getenv('REDIS_SRV')
yamlpath = "/appdata"
if os.getenv('YAML_PATH') != None:
  yamlpath = os.getenv('YAML_PATH')

async def main():
  # Get messages from REDIS queue
  redis = await aioredis.create_redis('redis://'+redisserver+'/0', encoding='utf-8')

  while True:
    msg = await redis.blpop('docker-controller')
    imgdata = json.loads(msg[1])

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
                 send_status(redis, "Pulling " + checkimg + " in " + file_name, "info")
                 rescmd = "cd " + yamlpath + " ; ./stack.sh " + file_name + " pull " + svc + " ; "
                 print("Executing : " + rescmd)
                 os.system(rescmd)
                 send_status(redis, "Updating " + checkimg + " in " + file_name, "info")
                 rescmd = "cd " + yamlpath + " ; ./stack.sh " + file_name + " up " + svc + " ; "
                 print("Executing : " + rescmd)
                 os.system(rescmd)
        if rescmd:
          print("Done for : " + checkimg)
          print("##################################################")
          send_status(redis, "Work done for " + checkimg, "info")
        else:
          print("Image " + checkimg + " not found in compose files")
          print("##################################################")
          send_status(redis, "Image " + checkimg + " not found in compose files", "info")
    if action == "pruning":
        rescmd = "docker system prune --volumes -f"
        print("##################################################")
        print("Executing : " + rescmd)
        pruningresult = subprocess.check_output(rescmd, shell=True).decode("utf-8")
        print("Pruning Results : " + pruningresult)
        print("##################################################")
        send_status(redis, "Pruning done : " + pruningresult, "info")


def send_status(redis, message, msgtype):
    resp = {}
    resp['message'] = message
    resp['type'] = msgtype
    return redis.rpush('docker-controller-resp', json.dumps(resp))

print(str(datetime.now()) + " -- Starting Work Loop ...")
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
