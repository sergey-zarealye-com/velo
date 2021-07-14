FROM pytorch/pytorch
WORKDIR /improch

COPY ./requirements.txt ./
RUN pip install -r requirements.txt
RUN conda install -c pytorch faiss-gpu

COPY ./ ./

ENTRYPOINT [ "python", "run.py" ]