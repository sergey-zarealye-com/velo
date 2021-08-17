FROM nvidia/cuda:11.0-base
WORKDIR /improch

ENV PATH="/root/miniconda3/bin:${PATH}"
ARG PATH="/root/miniconda3/bin:${PATH}"
ENV IS_DOCKER="True"

RUN apt update
RUN apt install -y --upgrade cmake
RUN apt -y upgrade
RUN apt install -y python3-pip
RUN apt install -y build-essential libssl-dev libffi-dev python3-dev
RUN apt install -y wget
RUN wget \
    https://repo.anaconda.com/miniconda/Miniconda3-py38_4.10.3-Linux-x86_64.sh \
    && mkdir /root/.conda \
    && bash Miniconda3-py38_4.10.3-Linux-x86_64.sh -b \
    && rm -f Miniconda3-py38_4.10.3-Linux-x86_64.sh
#RUN conda install pytorch torchvision cudatoolkit=10.2 -c pytorch
RUN yes | pip install torch==1.9.0 torchvision==0.10.0
RUN yes | conda install -c pytorch faiss-gpu
