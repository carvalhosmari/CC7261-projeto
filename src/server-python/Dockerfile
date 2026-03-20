FROM python:3.10

WORKDIR /app

# Copia proto
COPY proto ./proto

# Copia servidor
COPY server-python ./server-python

WORKDIR /app/server-python

# Instala dependências
RUN pip install pyzmq protobuf grpcio-tools

# REMOVE versão antiga
RUN rm -f chat_pb2.py

# GERA novamente
RUN python -m grpc_tools.protoc \
    -I../proto \
    --python_out=. \
    ../proto/chat.proto

CMD ["python", "server.py"]