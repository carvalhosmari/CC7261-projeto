import zmq
import chat_pb2
import json
import os
from datetime import datetime, timezone, timedelta
import utils as u

DATA_FILE = "/app/data/data.json"
SERVER_NAME = os.environ.get("HOSTNAME", "server")
count = 0

context = zmq.Context()

# Worker (REQ/REP via broker)
socket = context.socket(zmq.REP)
socket.connect("tcp://broker:5556")

# Publisher (Pub/Sub)
pub_socket = context.socket(zmq.PUB)
pub_socket.connect("tcp://pubsub-proxy:5557")

# Heartbeat (REQ/REP)
socket_req = context.socket(zmq.REQ)
socket_req.connect("tcp://heartbeat:6667")


# ===============================
# INIT
# ===============================

u.init_data(DATA_FILE)

my_rank = u.register_server(socket_req, SERVER_NAME)
u.get_servers(socket_req)


# ===============================
# LOOP PRINCIPAL
# ===============================

while True:

    message = socket.recv()

    req = chat_pb2.ChatRequest()
    req.ParseFromString(message)

    print(f"[SERVER] Recebendo: {req.type}", flush=True)

    res = chat_pb2.ChatResponse()
    dt = u.get_timestamp(socket_req)

    if req.type == "LOGIN":
        data = u.read_data(DATA_FILE)

        data["logins"].append({
            "username": req.username,
            "timestamp": dt
        })

        u.write_data(data, DATA_FILE)

        res.message = f"Login OK: {req.username}"

    elif req.type == "LIST_CHANNELS":
        data = u.read_data(DATA_FILE)

        res.message = "Lista de canais"
        res.channels.extend(data["channels"])

    elif req.type == "CREATE_CHANNEL":
        data = u.read_data(DATA_FILE)

        if req.channel not in data["channels"]:
            data["channels"].append(req.channel)
            u.write_data(data, DATA_FILE)
            res.message = f"Canal criado: {req.channel}"
        else:
            res.message = f"Canal já existe: {req.channel}"

    elif req.type == "PUBLISH":
        print(f"Publicando em {req.channel}", flush=True)

        data = u.read_data(DATA_FILE)

        if req.count > count:
            count = req.count

        # salva mensagem
        data["messages"].append({
            "channel": req.channel,
            "username": req.username,
            "message": req.message,
            "timestamp": dt,
            "count": count
        })

        u.write_data(data, DATA_FILE)

        # envia via Pub/Sub
        pub_socket.send_multipart([
            req.channel.encode(),
            req.SerializeToString()
        ])

        res.message = "Mensagem publicada"

    elif req.type == "SUBSCRIBE":
        data = u.read_data(DATA_FILE)

        user = req.username
        channel = req.channel

        if user not in data["subscriptions"]:
            data["subscriptions"][user] = []

        if channel not in data["subscriptions"][user]:
            data["subscriptions"][user].append(channel)

            u.write_data(data, DATA_FILE)

            res.message = f"{user} inscrito em {channel}"
        
        else:
            res.message = f"{user} já inscrito em {channel}"
    
    else:
        res.message = "Tipo inválido"

    socket.send(res.SerializeToString())