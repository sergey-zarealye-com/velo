FROM python:3.8-buster

WORKDIR /app
RUN mkdir -p /app/project/celery
RUN apt update
RUN apt install -y --upgrade cmake
RUN apt -y upgrade
RUN apt install -y python3-pip
RUN apt install -y build-essential libssl-dev libffi-dev python3-dev
RUN apt-get install software-properties-common -y
RUN add-apt-repository -y ppa:jonathonf/ffmpeg-4
RUN apt install ffmpeg -y

COPY ./requirements.txt ./

RUN pip install -r requirements.txt
RUN pip install urllib3
RUN mkdir /storage

COPY ./ /app/project/celery

ENTRYPOINT [ "celery", "-A", "project.celery.tasks", "worker", "-l", "info" ]