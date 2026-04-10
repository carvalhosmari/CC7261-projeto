import zmq
import chat_pb2
import json
import os

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
                "channels": [],
                "messages": []
            }, f)

def read_data():
    try:
        with open(DATA_FILE, "r") as f:
            content = f.read().strip()

            if not content:
                return {"logins": [], "channels": [], "messages": []}

            return json.loads(content)

    except Exception:
        return {"logins": [], "channels": [], "messages": []}

def write_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

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

    # ===============================
    # LOGIN
    # ===============================
    if req.type == "LOGIN":
        data = read_data()

        data["logins"].append({
            "username": req.username,
            "timestamp": req.timestamp
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

        # salva mensagem
        data["messages"].append({
            "channel": req.channel,
            "message": req.message,
            "timestamp": req.timestamp
        })

        write_data(data)

        # envia via Pub/Sub
        pub_socket.send_multipart([
            req.channel.encode(),
            req.SerializeToString()
        ])

        res.message = "Mensagem publicada"

    # ===============================
    # DEFAULT
    # ===============================
    else:
        res.message = "Tipo inválido"

    socket.send(res.SerializeToString())