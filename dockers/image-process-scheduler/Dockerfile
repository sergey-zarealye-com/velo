FROM base_image
WORKDIR /improch

RUN apt-get install ffmpeg libsm6 libxext6  -y

COPY ./requirements.txt ./
RUN pip install -r requirements.txt

COPY ./ ./

ENTRYPOINT [ "celery", "-A", "run", "worker", "--loglevel=INFO", "-P", "threads"]