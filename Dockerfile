FROM python:3.8

LABEL name="kik-bot-api-unofficial"

WORKDIR /app

COPY setup* /app/

RUN pip install /app

COPY . /app
COPY ./kik_unofficial/utilities/docker_bootstrapper.py /app/bootstrap.py

CMD python bootstrap.py
