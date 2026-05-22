import json
import os
import time
from datetime import datetime


def init_data(data_file):
    os.makedirs(os.path.dirname(data_file), exist_ok=True)

    if not os.path.exists(data_file):
        data = {
            "logins": [],
            "subscriptions": {},
            "channels": [],
            "messages": []
        }

        write_data(data, data_file)


def read_data(data_file):
    try:
        with open(data_file, "r") as f:
            content = f.read().strip()

            if not content:
                return {
                    "logins": [],
                    "subscriptions": {},
                    "channels": [],
                    "messages": []
                }

            return json.loads(content)

    except Exception:
        return {
            "logins": [],
            "subscriptions": {},
            "channels": [],
            "messages": []
        }


def write_data(data, data_file):
    with open(data_file, "w") as f:
        json.dump(data, f, indent=2)


def now(clock_offset=0):
    return str(datetime.fromtimestamp(
        (time.time() * 1000 + clock_offset) / 1000
    ))


def register_server(socket, server_name):
    import chat_pb2

    req = chat_pb2.HBRequest()

    req.type = "REGISTER"
    req.server = server_name

    socket.send(req.SerializeToString())

    reply = socket.recv()

    res = chat_pb2.HBResponse()
    res.ParseFromString(reply)

    print(f"[HB] Rank recebido: {res.rank}", flush=True)

    return res.rank


def get_servers(socket):
    import chat_pb2

    req = chat_pb2.HBRequest()

    req.type = "GET_SERVERS"

    socket.send(req.SerializeToString())

    reply = socket.recv()

    res = chat_pb2.HBResponse()
    res.ParseFromString(reply)

    return res.servers


def elect_coordinator(servers):
    if not servers:
        return None

    ordered = sorted(servers, key=lambda s: s.rank)
    return ordered[0].server


def replicate_to_servers(context, servers, current_server, req):
    import zmq

    for server in servers:

        server_name = server.server

        if server_name == current_server:
            continue

        try:
            sock = context.socket(zmq.REQ)

            sock.connect(f"tcp://{server_name}:7000")

            sock.send(req.SerializeToString())

            sock.recv()

            sock.close()

            print(
                f"[REPL] Replicado para {server_name}",
                flush=True
            )

        except Exception as e:
            print(
                f"[REPL] Falha ao replicar para {server_name}: {e}",
                flush=True
            )