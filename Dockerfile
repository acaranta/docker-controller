FROM acaranta/dind-compose:latest

ENV REDIS_SRV localhost
ENV YAML_PATH /appdata


RUN apt update -qq && apt install -y python3-pip && pip3 install asyncio aioredis
ADD docker-controller.py /app/docker-controller.py

CMD ["/usr/bin/pyton3 /app/docker-controller.py"]
