FROM base_image
WORKDIR /improch

RUN apt-get install ffmpeg libsm6 libxext6  -y

COPY ./requirements.txt ./
RUN pip install -r requirements.txt
RUN pip install pyyaml
RUN pip install pillow

COPY ./ ./

ENTRYPOINT [ "python", "run.py" ]
