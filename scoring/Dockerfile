FROM nvidia/cuda:11.0-base
WORKDIR /app

RUN apt update
RUN apt install -y --upgrade cmake
RUN apt -y upgrade
RUN apt install -y python3-pip
RUN apt install -y build-essential libssl-dev libffi-dev python3-dev
RUN apt-get install ffmpeg libsm6 libxext6  -y

COPY ./requirements.txt ./

RUN pip install -r requirements.txt

COPY ./ ./

ENTRYPOINT ["celery", "-A", "main", "worker", "--loglevel=INFO", "-P", "threads"]
