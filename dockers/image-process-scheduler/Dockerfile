FROM base_image
WORKDIR /improch

#RUN apt-get update
#RUN apt-get install ffmpeg libsm6 libxext6  -y
RUN apt-get install libgl1-mesa-glx libgtk2.0-dev -y
RUN conda install --force --yes mkl mkl-service

COPY ./requirements.txt ./
RUN pip install -r requirements.txt

COPY ./ ./

ENTRYPOINT [ "celery", "-A", "run", "worker", "--loglevel=INFO", "-P", "threads"]
