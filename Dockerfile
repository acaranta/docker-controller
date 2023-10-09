FROM acaranta/dind-compose:latest

ENV REDIS_SRV localhost
ENV YAML_PATH /appdata


RUN apt update -qq && apt install -y python3-pip python3-yaml && pip3 install paho-mqtt
ADD docker-controller.py /app/docker-controller.py
RUN rm -f /etc/supervisor/conf.d/supervisord.conf
CMD ["/usr/bin/python3", "-u", "/app/docker-controller.py"]
