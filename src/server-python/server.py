import zmq
import chat_pb2
import json
import os
from datetime import datetime, timezone, timedelta

# ===============================
# CONFIG
# ===============================

DATA_FILE = "/app/data/data.json"

# ===============================
# PERSISTÊNCIA
# ===============================

def init_data():
    if not os.path.exists(DATA_FILE):
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w") as f:
            json.dump({
                "logins": [],
                "subscriptions": {},
                "channels": [],
                "messages": []
            }, f)

def read_data():
    try:
        with open(DATA_FILE, "r") as f:
            content = f.read().strip()

            if not content:
                return {"logins": [],"subscriptions": {}, "channels": [], "messages": []}

            return json.loads(content)

    except Exception:
        return {"logins": [], "subscriptions": {}, "channels": [], "messages": []}

def write_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_timestamp(millis):
    dt = datetime.fromtimestamp(millis/1000)

    dt = dt - timedelta(hours=3)

    return str(dt)

count = 0

# ===============================
# ZEROMQ SETUP
# ===============================

context = zmq.Context()

# Worker (REQ/REP via broker)
socket = context.socket(zmq.REP)
socket.connect("tcp://broker:5556")

# Publisher (Pub/Sub)
pub_socket = context.socket(zmq.PUB)
pub_socket.connect("tcp://pubsub-proxy:5557")

print("Worker conectado ao broker", flush=True)

# ===============================
# INIT
# ===============================

init_data()

# ===============================
# LOOP PRINCIPAL
# ===============================

while True:

    message = socket.recv()

    req = chat_pb2.ChatRequest()
    req.ParseFromString(message)

    print(f"[SERVER] Recebendo: {req.type}", flush=True)

    res = chat_pb2.ChatResponse()
    dt = get_timestamp(req.timestamp)

    # ===============================
    # LOGIN
    # ===============================
    if req.type == "LOGIN":
        data = read_data()

        data["logins"].append({
            "username": req.username,
            "timestamp": dt
        })

        write_data(data)

        res.message = f"Login OK: {req.username}"

    # ===============================
    # LIST CHANNELS
    # ===============================
    elif req.type == "LIST_CHANNELS":
        data = read_data()

        res.message = "Lista de canais"
        res.channels.extend(data["channels"])

    # ===============================
    # CREATE CHANNEL
    # ===============================
    elif req.type == "CREATE_CHANNEL":
        data = read_data()

        if req.channel not in data["channels"]:
            data["channels"].append(req.channel)
            write_data(data)
            res.message = f"Canal criado: {req.channel}"
        else:
            res.message = f"Canal já existe: {req.channel}"

    # ===============================
    # PUBLISH
    # ===============================
    elif req.type == "PUBLISH":
        print(f"Publicando em {req.channel}", flush=True)

        data = read_data()

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

        write_data(data)

        # envia via Pub/Sub
        pub_socket.send_multipart([
            req.channel.encode(),
            req.SerializeToString()
        ])

        res.message = "Mensagem publicada"

    elif req.type == "SUBSCRIBE":
        data = read_data()

        user = req.username
        channel = req.channel

        if user not in data["subscriptions"]:
            data["subscriptions"][user] = []

        if channel not in data["subscriptions"][user]:
            data["subscriptions"][user].append(channel)

            write_data(data)

            res.message = f"{user} inscrito em {channel}"
        
        else:
            res.message = f"{user} já inscrito em {channel}"
    # ===============================
    # DEFAULT
    # ===============================
    else:
        res.message = "Tipo inválido"

    socket.send(res.SerializeToString())