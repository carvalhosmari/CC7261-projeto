import json
import os
import threading
import time

import zmq

import chat_pb2
import utils as u


# ===============================
# CONFIG
# ===============================

SERVER_NAME = os.environ.get(
    "HOSTNAME",
    "server-1"
)

DATA_FILE = f"/app/data/server-{SERVER_NAME}.json"

SERVER_PORT = 7000

COORDINATOR = None
SERVERS = []

CLOCK_OFFSET = 0
MESSAGE_COUNT = 0
count = 0


# ===============================
# CONTEXT
# ===============================

context = zmq.Context()


# ===============================
# SOCKETS
# ===============================

# Cliente ↔ Servidor (Broker)
rep_socket = context.socket(zmq.REP)
rep_socket.connect("tcp://broker:5556")

# Pub/Sub
pub_socket = context.socket(zmq.PUB)
pub_socket.connect("tcp://pubsub-proxy:5557")

# Heartbeat
hb_socket = context.socket(zmq.REQ)
hb_socket.connect("tcp://heartbeat:6667")

# Comunicação interna
internal_socket = context.socket(zmq.REP)
internal_socket.bind(f"tcp://*:{SERVER_PORT}")


# ===============================
# FUNÇÕES AUXILIARES
# ===============================

def get_coordinator_socket():

    sock = context.socket(zmq.REQ)
    sock.setsockopt(zmq.RCVTIMEO, 2000)
    sock.setsockopt(zmq.SNDTIMEO, 2000)

    sock.connect(
        f"tcp://{COORDINATOR}:{SERVER_PORT}"
    )

    return sock


def announce_coordinator():

    msg = f"COORDINATOR:{SERVER_NAME}"

    pub_socket.send_string(
        f"servers {msg}"
    )

    print(
        f"[COORD] Coordenador anunciado: {SERVER_NAME}",
        flush=True
    )


def listen_servers():

    global COORDINATOR

    sub = context.socket(zmq.SUB)

    sub.connect("tcp://pubsub-proxy:5558")

    sub.setsockopt_string(
        zmq.SUBSCRIBE,
        "servers"
    )

    while True:

        try:

            _, msg = sub.recv_string().split(" ", 1)

            if msg.startswith("COORDINATOR:"):

                COORDINATOR = msg.split(":")[1]

                print(
                    f"[COORD] Novo coordenador: {COORDINATOR}",
                    flush=True
                )

        except Exception as e:

            print(
                f"[COORD] Erro: {e}",
                flush=True
            )


def sync_clock():

    global CLOCK_OFFSET
    global COORDINATOR

    if COORDINATOR == SERVER_NAME:
        return

    try:

        sock = get_coordinator_socket()

        req = chat_pb2.ChatRequest()
        req.type = "GET_TIME"

        sock.send(req.SerializeToString())

        reply = sock.recv()

        res = chat_pb2.ChatResponse()
        res.ParseFromString(reply)

        coordinator_time = int(res.message)

        local_time = int(time.time() * 1000)

        CLOCK_OFFSET = (
            coordinator_time - local_time
        )

        print(
            f"[CLOCK] Offset atualizado: {CLOCK_OFFSET}",
            flush=True
        )

        sock.close()

    except Exception:

        print(
            "[CLOCK] Coordenador caiu → nova eleição",
            flush=True
        )

        COORDINATOR = u.elect_coordinator(SERVERS)

        print(f"NOVO COORDENADOR APOS NOVA ELEICAO: {COORDINATOR}")



def merge_state(local_data, remote_data):

    # ===========================
    # LOGINS
    # ===========================

    for login in remote_data["logins"]:

        if login not in local_data["logins"]:
            local_data["logins"].append(login)

    # ===========================
    # CHANNELS
    # ===========================

    for channel in remote_data["channels"]:

        if channel not in local_data["channels"]:
            local_data["channels"].append(channel)

    # ===========================
    # SUBSCRIPTIONS
    # ===========================

    for channel, users in remote_data["subscriptions"].items():

        if channel not in local_data["subscriptions"]:
            local_data["subscriptions"][channel] = []

        for user in users:

            if user not in local_data["subscriptions"][channel]:
                local_data["subscriptions"][channel].append(user)

    # ===========================
    # MESSAGES
    # ===========================

    for message in remote_data["messages"]:

        exists = any(
            msg["timestamp"] == message["timestamp"]
            and msg["username"] == message["username"]
            and msg["message"] == message["message"]
            for msg in local_data["messages"]
        )

        if not exists:
            local_data["messages"].append(message)

    return local_data


def sync_state():

    global SERVERS

    SERVERS = u.get_servers(hb_socket)

    local_data = u.read_data(DATA_FILE)

    synced = False

    for server in SERVERS:

        if server.server == SERVER_NAME:
            continue

        try:

            print(
                f"[SYNC] Recuperando estado de {server.server}",
                flush=True
            )

            sock = context.socket(zmq.REQ)
            sock.setsockopt(zmq.RCVTIMEO, 2000)
            sock.setsockopt(zmq.SNDTIMEO, 2000)

            sock.connect(
                f"tcp://{server.server}:{SERVER_PORT}"
            )

            req = chat_pb2.ChatRequest()
            req.type = "GET_STATE"

            sock.send(req.SerializeToString())

            reply = sock.recv()

            res = chat_pb2.ChatResponse()
            res.ParseFromString(reply)

            remote_data = json.loads(res.message)

            local_data = merge_state(
                local_data,
                remote_data
            )

            sock.close()

            synced = True

        except Exception as e:

            print(
                f"[SYNC] Falha ao recuperar "
                f"de {server.server}: {e}",
                flush=True
            )

    if synced:

        u.write_data(
            local_data,
            DATA_FILE
        )

        print(
            "[SYNC] Estado sincronizado",
            flush=True
        )

def sync_state_loop():
    """
    Tenta sincronizar estado periodicamente.
    """

    while True:

        try:
            sync_state()

        except Exception as e:
            print(
                f"[SYNC_LOOP] Erro: {e}",
                flush=True
            )

        time.sleep(10)

def replicate_data(event_type, payload):

    global SERVERS

    SERVERS = u.get_servers(hb_socket)

    for server in SERVERS:

        if server.server == SERVER_NAME:
            continue

        try:

            sock = context.socket(zmq.REQ)
            sock.setsockopt(zmq.RCVTIMEO, 2000)
            sock.setsockopt(zmq.SNDTIMEO, 2000)

            sock.connect(
                f"tcp://{server.server}:{SERVER_PORT}"
            )

            req = chat_pb2.ChatRequest()

            req.type = "REPLICATION"

            req.message = json.dumps({
                "event": event_type,
                "payload": payload
            })

            sock.send(req.SerializeToString())

            sock.recv()

            sock.close()

            print(
                f"[REPL] Replicado para {server.server}",
                flush=True
            )

        except Exception as e:

            print(
                f"[REPL] Falha ao replicar "
                f"para {server.server}: {e}",
                flush=True
            )


# ===============================
# COMUNICAÇÃO INTERNA
# ===============================

def handle_internal_requests():

    global count

    while True:

        try:

            message = internal_socket.recv()

            req = chat_pb2.ChatRequest()
            req.ParseFromString(message)

            res = chat_pb2.ChatResponse()

            # =======================
            # GET TIME
            # =======================

            if req.type == "GET_TIME":

                res.message = str(
                    u.now(CLOCK_OFFSET)
                )

            # =======================
            # GET STATE
            # =======================

            elif req.type == "GET_STATE":

                data = u.read_data(DATA_FILE)

                res.message = json.dumps(data)

            # =======================
            # REPLICATION
            # =======================

            elif req.type == "REPLICATION":

                replication = json.loads(req.message)

                event = replication["event"]
                payload = replication["payload"]

                data = u.read_data(DATA_FILE)

                # ===================
                # LOGIN
                # ===================

                if event == "LOGIN":

                    if payload not in data["logins"]:

                        data["logins"].append(payload)

                # ===================
                # CREATE CHANNEL
                # ===================

                elif event == "CREATE_CHANNEL":

                    if payload not in data["channels"]:

                        data["channels"].append(payload)

                # ===================
                # SUBSCRIBE
                # ===================

                elif event == "SUBSCRIBE":

                    channel = payload["channel"]
                    user = payload["username"]

                    if channel not in data["subscriptions"]:

                        data["subscriptions"][channel] = []

                    if user not in data["subscriptions"][channel]:

                        data["subscriptions"][channel].append(user)

                # ===================
                # PUBLISH
                # ===================

                elif event == "PUBLISH":

                    exists = any(
                        msg["timestamp"] == payload["timestamp"]
                        and msg["username"] == payload["username"]
                        and msg["message"] == payload["message"]
                        for msg in data["messages"]
                    )

                    if not exists:

                        count = max(
                            count,
                            payload["count"]
                        ) + 1

                        data["messages"].append(payload)

                u.write_data(
                    data,
                    DATA_FILE
                )

                res.message = "REPLICATION_OK"

            else:

                res.message = "INVALID_INTERNAL_REQUEST"

            res.count = count

            internal_socket.send(
                res.SerializeToString()
            )

        except Exception as e:

            print(
                f"[INTERNAL] Erro: {e}",
                flush=True
            )


# ===============================
# INIT
# ===============================

u.init_data(DATA_FILE)

u.register_server(
    hb_socket,
    SERVER_NAME
)

SERVERS = u.get_servers(hb_socket)


COORDINATOR = u.elect_coordinator(SERVERS)

if COORDINATOR == SERVER_NAME:
    announce_coordinator()


# ===============================
# THREADS
# ===============================

threading.Thread(
    target=handle_internal_requests,
    daemon=True
).start()

threading.Thread(
    target=listen_servers,
    daemon=True
).start()

threading.Thread(
    target=sync_state_loop,
    daemon=True
).start()

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

    res = chat_pb2.ChatResponse()

    timestamp = u.now(CLOCK_OFFSET)

    print(
        f"[SERVER {SERVER_NAME}] "
        f"Recebendo: {req.type}",
        flush=True
    )

    # ==========================
    # RELÓGIO LÓGICO
    # ==========================

    count = max(count, req.count) + 1

    # ==========================
    # LOGIN
    # ==========================

    if req.type == "LOGIN":

        data = u.read_data(DATA_FILE)

        login_data = {
            "username": req.username,
            "timestamp": timestamp,
            "count": count
        }

        if login_data not in data["logins"]:

            data["logins"].append(login_data)

            u.write_data(
                data,
                DATA_FILE
            )

            replicate_data(
                "LOGIN",
                login_data
            )

        res.message = f"Login OK: {req.username}"

    # ==========================
    # LIST CHANNELS
    # ==========================

    elif req.type == "LIST_CHANNELS":

        data = u.read_data(DATA_FILE)

        res.message = "Lista de canais"

        res.channels.extend(
            data["channels"]
        )

    # ==========================
    # CREATE CHANNEL
    # ==========================

    elif req.type == "CREATE_CHANNEL":

        data = u.read_data(DATA_FILE)

        if req.channel not in data["channels"]:

            data["channels"].append(
                req.channel
            )

            u.write_data(
                data,
                DATA_FILE
            )

            replicate_data(
                "CREATE_CHANNEL",
                req.channel
            )

            res.message = (
                f"Canal criado: {req.channel}"
            )

        else:

            res.message = (
                f"Canal já existe: {req.channel}"
            )

    # ==========================
    # SUBSCRIBE
    # ==========================

    elif req.type == "SUBSCRIBE":

        data = u.read_data(DATA_FILE)

        user = req.username
        channel = req.channel

        if channel not in data["subscriptions"]:

            data["subscriptions"][channel] = []

        if user not in data["subscriptions"][channel]:

            data["subscriptions"][channel].append(user)

            u.write_data(
                data,
                DATA_FILE
            )

            replicate_data(
                "SUBSCRIBE",
                {
                    "username": user,
                    "channel": channel
                }
            )

            res.message = (
                f"{user} inscrito em {channel}"
            )

        else:

            res.message = (
                f"{user} já inscrito em {channel}"
            )

    # ==========================
    # PUBLISH
    # ==========================

    elif req.type == "PUBLISH":

        print(
            f"[PUB] Publicando em "
            f"{req.channel}",
            flush=True
        )

        data = u.read_data(DATA_FILE)

        message_data = {
            "channel": req.channel,
            "username": req.username,
            "message": req.message,
            "timestamp": timestamp,
            "count": count
        }

        exists = any(
            msg["timestamp"] == message_data["timestamp"]
            and msg["username"] == message_data["username"]
            and msg["message"] == message_data["message"]
            for msg in data["messages"]
        )

        if not exists:

            data["messages"].append(
                message_data
            )

            u.write_data(
                data,
                DATA_FILE
            )

            replicate_data(
                "PUBLISH",
                message_data
            )

        pub_socket.send_multipart([
            req.channel.encode(),
            req.SerializeToString()
        ])

        res.message = "Mensagem publicada"

    # ==========================
    # GET TIME
    # ==========================

    elif req.type == "GET_TIME":

        res.message = str(
            u.now(CLOCK_OFFSET)
        )

    # ==========================
    # DEFAULT
    # ==========================

    else:

        res.message = "Tipo inválido"

    res.count = count

    rep_socket.send(
        res.SerializeToString()
    )