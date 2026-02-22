package com.example.grpc;

import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;

public class Cliente {

    public static void main(String[] args) {

        ManagedChannel channel = ManagedChannelBuilder
                .forTarget("dns:///servidor:50051")
                .usePlaintext()
                .build();

        HelloServiceGrpc.HelloServiceBlockingStub stub =
                HelloServiceGrpc.newBlockingStub(channel);

        HelloRequest request = HelloRequest.newBuilder()
                .setMessage("hello world")
                .build();

        HelloReply response = stub.sayHello(request);

        System.out.println("Resposta do servidor: " + response.getMessage());

        channel.shutdown();
    }
}