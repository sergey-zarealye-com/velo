FROM base_image

WORKDIR /app
RUN mkdir -p /app/project/celery
RUN apt-get install software-properties-common -y
RUN add-apt-repository -y ppa:jonathonf/ffmpeg-4
RUN apt install ffmpeg -y

COPY ./requirements.txt ./

RUN pip install -r requirements.txt
RUN mkdir /storage

COPY ./ /app/project/celery

ENTRYPOINT [ "celery", "-A", "project.celery.tasks", "worker", "-l", "info" ]