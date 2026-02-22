from concurrent import futures
import grpc
import hello_pb2
import hello_pb2_grpc

class HelloServiceServicer(hello_pb2_grpc.HelloServiceServicer):

    def SayHello(self, request, context):
        print("Mensagem recebida do cliente:", request.message)
        return hello_pb2.HelloReply(message="hello world")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    hello_pb2_grpc.add_HelloServiceServicer_to_server(HelloServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Servidor rodando na porta 50051...")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()