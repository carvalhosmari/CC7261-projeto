FROM python:3.10
WORKDIR /app

COPY pub-sub ./pub-sub

WORKDIR /app/pub-sub

RUN pip install pyzmq

CMD ["python", "proxy.py"]