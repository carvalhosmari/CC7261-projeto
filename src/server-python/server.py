import os
import time
import threading
import zmq
import chat_pb2
import utils as u

# ===============================
# CONFIG
# ===============================


SERVER_NAME = os.environ.get("HOSTNAME", "server")
DATA_FILE = f"/app/data/data_{SERVER_NAME}.json"
SERVER_PORT = 7000  # comunicação entre servidores

COORDINATOR = None
SERVERS = []
CLOCK_OFFSET = 0
MESSAGE_COUNT = 0
count = 0  # relógio lógico (Lamport)

context = zmq.Context()

# ===============================
# SOCKETS
# ===============================

# Cliente ↔ Servidor (via broker)
rep_socket = context.socket(zmq.REP)
rep_socket.connect("tcp://broker:5556")

# Pub/Sub
pub_socket = context.socket(zmq.PUB)
pub_socket.connect("tcp://pubsub-proxy:5557")

# Heartbeat
hb_socket = context.socket(zmq.REQ)
hb_socket.connect("tcp://heartbeat:6667")

# Servidor ↔ Servidor
internal_socket = context.socket(zmq.REP)
internal_socket.bind(f"tcp://*:{SERVER_PORT}")


# ===============================
# COMUNICAÇÃO INTERNA
# ===============================

def handle_internal_requests():
    while True:
        try:
            message = internal_socket.recv()

            req = chat_pb2.ChatRequest()
            req.ParseFromString(message)

            res = chat_pb2.ChatResponse()

            if req.type == "GET_TIME":
                res.message = str(u.now(CLOCK_OFFSET))
            else:
                res.message = "INVALID_INTERNAL_REQUEST"

            internal_socket.send(res.SerializeToString())

        except Exception as e:
            print(f"[INTERNAL] Erro: {e}", flush=True)


def get_coordinator_socket():
    sock = context.socket(zmq.REQ)
    sock.connect(f"tcp://{COORDINATOR}:{SERVER_PORT}")
    return sock


# ===============================
# COORDENAÇÃO
# ===============================

def announce_coordinator():
    msg = f"COORDINATOR:{SERVER_NAME}"
    pub_socket.send_string(f"servers {msg}")
    print(f"[COORD] Coordenador anunciado: {SERVER_NAME}", flush=True)


def listen_servers():
    sub = context.socket(zmq.SUB)
    sub.connect("tcp://pubsub-proxy:5558")
    sub.setsockopt_string(zmq.SUBSCRIBE, "servers")

    global COORDINATOR

    while True:
        _, msg = sub.recv_string().split(" ", 1)

        if msg.startswith("COORDINATOR:"):
            COORDINATOR = msg.split(":")[1]
            print(f"[COORD] Novo coordenador: {COORDINATOR}", flush=True)


def sync_clock():
    global CLOCK_OFFSET, COORDINATOR

    if COORDINATOR == SERVER_NAME:
        return

    try:
        sock = get_coordinator_socket()

        req = chat_pb2.ChatRequest(type="GET_TIME")
        sock.send(req.SerializeToString())
        reply = sock.recv()

        res = chat_pb2.ChatResponse()
        res.ParseFromString(reply)

        coordinator_time = int(res.message)
        local_time = int(time.time() * 1000)

        CLOCK_OFFSET = coordinator_time - local_time

        print(f"[CLOCK] Offset atualizado: {CLOCK_OFFSET}", flush=True)

        sock.close()

    except Exception:
        print("[CLOCK] Coordenador caiu → nova eleição", flush=True)
        COORDINATOR = u.elect_coordinator(SERVERS)


# ===============================
# INIT
# ===============================

u.init_data(DATA_FILE)

u.register_server(hb_socket, SERVER_NAME)

SERVERS = u.get_servers(hb_socket)
COORDINATOR = u.elect_coordinator(SERVERS)

if COORDINATOR == SERVER_NAME:
    announce_coordinator()

threading.Thread(target=handle_internal_requests, daemon=True).start()
threading.Thread(target=listen_servers, daemon=True).start()


# ===============================
# LOOP PRINCIPAL
# ===============================

while True:
    MESSAGE_COUNT += 1

    if MESSAGE_COUNT % 15 == 0:
        sync_clock()

    message = rep_socket.recv()

    req = chat_pb2.ChatRequest()
    req.ParseFromString(message)

    
    # ===========================
    # LAMPORT (RECEIVE)
    # ===========================
    received_count = req.count if req.count > 0 else 0
    count = max(count, received_count) 

    print(f"[SERVER] Recebendo: {req.type} | clock={count}", flush=True)

    res = chat_pb2.ChatResponse()
    timestamp = u.now(CLOCK_OFFSET)

    # ===========================
    # LOGIN
    # ===========================
    if req.type == "LOGIN":
        data = u.read_data(DATA_FILE)

        data["logins"].append({
            "username": req.username,
            "timestamp": timestamp
        })

        u.write_data(data, DATA_FILE)

        res.message = f"Login OK: {req.username}"

    # ===========================
    # LIST CHANNELS
    # ===========================
    elif req.type == "LIST_CHANNELS":
        data = u.read_data(DATA_FILE)

        res.message = "Lista de canais"
        res.channels.extend(data["channels"])

    # ===========================
    # CREATE CHANNEL
    # ===========================
    elif req.type == "CREATE_CHANNEL":
        data = u.read_data(DATA_FILE)

        if req.channel not in data["channels"]:
            data["channels"].append(req.channel)
            u.write_data(data, DATA_FILE)
            res.message = f"Canal criado: {req.channel}"
        else:
            res.message = f"Canal já existe: {req.channel}"

    # ===========================
    # PUBLISH
    # ===========================
    elif req.type == "PUBLISH":
        print(f"[PUB] Publicando em {req.channel}", flush=True)

        data = u.read_data(DATA_FILE)

        data["messages"].append({
            "channel": req.channel,
            "username": req.username,
            "message": req.message,
            "timestamp": timestamp
        })

        u.write_data(data, DATA_FILE)

        # reenviar com clock atualizado
        pub_req = chat_pb2.ChatRequest(
            type=req.type,
            username=req.username,
            channel=req.channel,
            message=req.message,
            timestamp=req.timestamp,
            count=count
        )

        pub_socket.send_multipart([
            req.channel.encode(),
            pub_req.SerializeToString()
        ])

        res.message = "Mensagem publicada"

    # ===========================
    # SUBSCRIBE
    # ===========================
    elif req.type == "SUBSCRIBE":
        data = u.read_data(DATA_FILE)

        user = req.username
        channel = req.channel

        if channel not in data["subscriptions"]:
            data["subscriptions"][channel] = []

        if user not in data["subscriptions"][channel]:
            data["subscriptions"][channel].append(user)
            u.write_data(data, DATA_FILE)
            res.message = f"{user} inscrito em {channel}"
        else:
            res.message = f"{user} já inscrito em {channel}"

    # ===========================
    # GET TIME (coordenador)
    # ===========================
    elif req.type == "GET_TIME":
        res.message = str(u.now(CLOCK_OFFSET))

    # ===========================
    # DEFAULT
    # ===========================
    else:
        res.message = "Tipo inválido"

    # ===========================
    # RESPONSE (Lamport)
    # ===========================
    res.count = count

    rep_socket.send(res.SerializeToString())