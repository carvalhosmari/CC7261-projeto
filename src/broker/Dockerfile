FROM python:3.10

WORKDIR /app

COPY broker ./broker

WORKDIR /app/broker

RUN pip install pyzmq

CMD ["python", "broker.py"]