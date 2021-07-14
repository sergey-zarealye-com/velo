FROM pytorch/pytorch
WORKDIR /improch

ENV PATH="/root/miniconda3/bin:${PATH}"
ARG PATH="/root/miniconda3/bin:${PATH}"

RUN apt-get update
RUN apt-get install -y --upgrade cmake
RUN apt-get -y upgrade
RUN apt-get install -y python3-pip
RUN apt-get install -y build-essential libssl-dev libffi-dev python3-dev
RUN apt-get install -y wget
RUN wget \
    https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && mkdir /root/.conda \
    && bash Miniconda3-latest-Linux-x86_64.sh -b \
    && rm -f Miniconda3-latest-Linux-x86_64.sh 

RUN conda install pytorch torchvision cudatoolkit=10.2 -c pytorch
RUN yes | conda install -c pytorch faiss-gpu
COPY ./requirements.txt ./
RUN pip install -r requirements.txt

RUN apt-get install ffmpeg libsm6 libxext6  -y
RUN pip install pyyaml
RUN pip install pillow

COPY ./ ./

ENTRYPOINT [ "python", "run.py" ]
