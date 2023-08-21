FROM python:3.11

ENV PIP_NO_CACHE_DIR=true

RUN pip install boto3

WORKDIR /root

COPY worker worker

RUN pip install ./worker && rm --recursive worker
