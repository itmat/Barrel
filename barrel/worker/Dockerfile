FROM python:3.11

ENV PIP_NO_CACHE_DIR=true

RUN apt-get update                                          \
 && apt-get install -y default-jdk                          \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install boto3

WORKDIR /root

COPY worker worker

RUN pip install ./worker && rm --recursive worker

ARG STUDY_NAME

COPY studies/${STUDY_NAME} ${STUDY_NAME}
