#!/usr/bin/python3
import asyncio
import aioredis
import json 
import yaml
import glob
import sys
import os

from pprint import pprint
from datetime import datetime

#### OPTS ####
redisserver = "localhost"
if os.getenv('REDIS_SRV') != None:
  redisserver = os.getenv('REDIS_SRV')
yamlpath = "/appdata"
if os.getenv('YAML_PATH') != None:
  redisserver = os.getenv('YAML_PATH')

async def main():

  redis = await aioredis.create_redis('redis://'+redisserver+':6379/0', encoding='utf-8')

  while True:
    msg = await redis.blpop('dockerhub')
    imgdata = json.loads(msg[1])

    checkimg = imgdata['imgfull'] 
    print("\n##################################################")
    print(datetime.now())
    print("Received hook call for " + checkimg)
    print("##################################################")
    rescmd = ""
    list_of_files = glob.glob(yamlpath + '/docker*.yml')           # create the list of file
    for file_name in list_of_files:
      with open(file_name, 'r') as file:
        composeconfig = yaml.load(file)
        for svc in composeconfig["services"]:
          if composeconfig["services"][svc]["image"] == checkimg:
             rescmd += "cd " + yamlpath + " ; "
             rescmd += "./stack.sh " + file_name + " pull " + svc + " ; "
             rescmd += "./stack.sh " + file_name + " up " + svc + " ; "
    if rescmd:
      print("Executing : " + rescmd)
      os.system(rescmd)
    else:
      print("Image " + checkimg + " not found in compose files")
    print("##################################################")



loop = asyncio.get_event_loop()
loop.run_until_complete(main())
