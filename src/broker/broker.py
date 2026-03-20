import zmq

context = zmq.Context()

frontend = context.socket(zmq.ROUTER)
frontend.bind("tcp://*:5555")   # clientes

backend = context.socket(zmq.DEALER)
backend.bind("tcp://*:5556")   # servidores

print("🚀 Broker iniciado (5555 ↔ 5556)", flush=True)

zmq.proxy(frontend, backend)