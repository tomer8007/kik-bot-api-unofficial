FROM python:3.8

LABEL name="kik-bot-api-unofficial"

WORKDIR /app

COPY setup* /app/

RUN pip install /app

COPY . /app
COPY examples/echo_bot.py /app/bot.py

CMD python bot.py
