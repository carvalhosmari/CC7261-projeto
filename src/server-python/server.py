import zmq
import chat_pb2
import os
import json

context = zmq.Context()
socket = context.socket(zmq.REP)

socket.connect("tcp://broker:5556")

print("Worker conectado ao broker", flush=True)

DATA_DIR = "/app/data" 
DATA_FILE = os.path.join(DATA_DIR, "data.json")

os.makedirs(DATA_DIR, exist_ok=True) 

def init_data(): 
    if not os.path.exists(DATA_FILE): 
        with open(DATA_FILE, "w") as f: 
            json.dump({ "logins": [], "channels": [] }, f) 


def read_data():
    # Se não existe, cria
    if not os.path.exists(DATA_FILE):
        return {"logins": [], "channels": []}

    # Se existe mas está vazio
    if os.path.getsize(DATA_FILE) == 0:
        data = {"logins": [], "channels": []}
        write_data(data)
        return data

    # Tenta ler normalmente
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        data = {"logins": [], "channels": []}
        write_data(data)
        return data
 

def write_data(data): 
    with open(DATA_FILE, "w") as f: 
        json.dump(data, f, indent=2) 
        
# Inicializa arquivo 
init_data()

data = read_data() 
channels = set(data.get("channels", []))

while True:
    try:   
        message = socket.recv()

        req = chat_pb2.ChatRequest()
        req.ParseFromString(message)

        print(f"[SERVER] Recebendo: {req.type}", flush=True)

        res = chat_pb2.ChatResponse()

        if req.type == "LOGIN":
            data = read_data()
            data["logins"].append({ "username": req.username, "timestamp": req.timestamp })
            write_data(data)
            res.message = f"Login OK: {req.username}"

        elif req.type == "LIST_CHANNELS":
            data = read_data()
            res.message = "Lista de canais"
            res.channels.extend(list(channels))

        elif req.type == "CREATE_CHANNEL":
            channels.add(req.channel)
            data = read_data() 
            data["channels"].append(req.channel) 
            write_data(data)

            res.message = f"Canal criado: {req.channel}"

        socket.send(res.SerializeToString())
    except Exception as e: 
        print(f"🔥 ERRO NO LOOP: {e}", flush=True)
