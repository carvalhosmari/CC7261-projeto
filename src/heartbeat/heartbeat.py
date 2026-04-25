import zmq
from datetime import datetime, timezone, timedelta
import chat_pb2
import time

context = zmq.Context()

rep = context.socket(zmq.REP)
rep.bind("tcp://*:6667")
 
servers = {}  # {nome: rank}
next_rank = 1

def get_timestamp():
    dt = datetime.now()

    dt = dt - timedelta(hours=3)

    return dt.timestamp()

while True:
    message = rep.recv()

    req = chat_pb2.HBRequest()
    req.ParseFromString(message)
    

    res = chat_pb2.HBResponse()

    res.timestamp = int(time.time() * 1000)

    if req.type == "REGISTER":
        name_server = req.server
        
        if name_server not in servers:
            servers[name_server] = next_rank
            res.rank = servers[name_server]
            next_rank += 1

            res.message = f"Registrado: {name_server} (rank {servers[name_server]})"
    
    elif req.type == "GET_SERVERS":
        for name_server, rank in servers.items():
            s = res.servers.add()
            s.server = name_server
            s.rank = rank

            res.message = f"Servers: {servers}"

    elif req.type == "SYNC":
        pass

    else:
        res.message = "Tipo inválido"

    rep.send(res.SerializeToString())