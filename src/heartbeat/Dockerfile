FROM python:3.10
WORKDIR /app

# Copia proto
COPY proto ./proto

COPY heartbeat ./heartbeat

WORKDIR /app/heartbeat

RUN pip install pyzmq protobuf grpcio-tools

RUN rm -f chat_pb2.py

# GERA novamente
RUN python -m grpc_tools.protoc \
    -I../proto \
    --python_out=. \
    ../proto/chat.proto


RUN pip install pyzmq

CMD ["python", "heartbeat.py"]