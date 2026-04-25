import zmq
import chat_pb2
import json
import os
from datetime import datetime, timezone, timedelta

def init_data(data_file):
    if not os.path.exists(data_file):
        os.makedirs(os.path.dirname(data_file), exist_ok=True)
        with open(data_file, "w") as f:
            json.dump({
                "logins": [],
                "subscriptions": {},
                "channels": [],
                "messages": []
            }, f)

def read_data(data_file):
    try:
        with open(data_file, "r") as f:
            content = f.read().strip()

            if not content:
                return {"logins": [],"subscriptions": {}, "channels": [], "messages": []}

            return json.loads(content)

    except Exception:
        return {"logins": [], "subscriptions": {}, "channels": [], "messages": []}

def write_data(data, data_file):
    with open(data_file, "w") as f:
        json.dump(data, f, indent=2)

def get_timestamp(socket):
    req = chat_pb2.HBRequest()
    req.type = "SYNC"

    socket.send(req.SerializeToString())

    hb_message = socket.recv()
    res = chat_pb2.HBResponse()
    res.ParseFromString(hb_message)

    print(res.timestamp)

    dt = datetime.fromtimestamp(res.timestamp/1000)

    dt = dt - timedelta(hours=3)

    return str(dt)

def register_server(socket, server_name):
    req = chat_pb2.HBRequest()
    
    req.type = "REGISTER"
    req.server = server_name

    socket.send(req.SerializeToString())

    hb_message = socket.recv()
    res = chat_pb2.HBResponse()
    res.ParseFromString(hb_message)

    print(res.message)

    rank = res.rank

    return rank
    
def get_servers(socket):
    req = chat_pb2.HBRequest()
    
    req.type = "GET_SERVERS"
    
    socket.send(req.SerializeToString())

    hb_message = socket.recv()
    res = chat_pb2.HBResponse()
    res.ParseFromString(hb_message)
    
    print(res.message)
    servers = res.servers

    return servers