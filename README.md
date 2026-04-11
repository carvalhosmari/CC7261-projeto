# CC7261-projeto - Sistema para troca de mensagem instantânea 📨

## 📌 Introdução

Este projeto consiste na implementação de um sistema distribuído para troca de mensagens instantâneas, inspirado em sistemas clássicos como BBS (Bulletin Board System) e IRC (Internet Relay Chat).

A aplicação permite que múltiplos clientes (bots) interajam com servidores para:

* realizar login
* criar e listar canais
* publicar mensagens
* se inscrever em canais
* receber mensagens em tempo real

O sistema foi projetado seguindo princípios de **Sistemas Distribuídos**, com foco em comunicação desacoplada, escalabilidade e persistência de dados.

---

## 🏗️ Arquitetura do Sistema

O sistema é composto pelos seguintes componentes:

### 🔹 Cliente (Java)

* Responsável por simular usuários (bots)
* Envia requisições (REQ) ao servidor
* Se inscreve em canais via Pub/Sub
* Publica mensagens e escuta eventos em tempo real

### 🔹 Servidor (Python)

* Processa requisições dos clientes
* Gerencia usuários, canais e mensagens
* Realiza persistência em disco (JSON)
* Publica mensagens para o sistema Pub/Sub

### 🔹 Broker (ZeroMQ)

* Intermedia comunicação síncrona (REQ/REP)
* Implementa padrão **Load Balancing Broker**

```
Cliente → Broker → Servidor
```

### 🔹 Pub/Sub Proxy (ZeroMQ)

* Responsável pela distribuição de mensagens em tempo real
* Implementa padrão **Publisher-Subscriber**

```
Servidor → Proxy → Clientes
```

---

## 🔄 Comunicação

### 📡 REQ/REP (Síncrono)

Utilizado para operações de controle:

* LOGIN
* CREATE_CHANNEL
* LIST_CHANNELS
* SUBSCRIBE
* PUBLISH

### 📡 PUB/SUB (Assíncrono)

Utilizado para distribuição de mensagens:

* cada canal = um tópico
* clientes recebem mensagens dos canais inscritos

---

## 📦 Serialização

O sistema utiliza **Protocol Buffers (Protobuf)** para serialização binária das mensagens.

### 📄 Estrutura principal:

```proto
message ChatRequest {
  string type = 1;
  string username = 2;
  string channel = 3;
  string message = 4;
  int64 timestamp = 5;
}

message ChatResponse {
  string message = 1;
  repeated string channels = 2;
}
```

### ✔ Vantagens

* alta performance
* baixo uso de banda
* compatível entre linguagens (Java ↔ Python)

---

## 💾 Persistência de Dados

O servidor mantém persistência em arquivo JSON:

📂 `/app/data/data.json`

### 📄 Estrutura:

```json
{
  "logins": [
    {
      "username": "bot_quod",
      "timestamp": 1775872400273
    }
  ],
  "subscriptions": {
    "bot_quod": [
      "canal_41"
    ]
  },
  "channels": [
    "canal_41"
  ],
  "messages": [
    {
      "channel": "canal_41",
      "username": "bot_quod",
      "message": " placeat tempora id consequatur delectus ab impedit quaerat ipsam cumque a quod nam ut dolorem corporis sequi qui dolor laudantium et optio veritatis autem ut perferendis",
      "timestamp": 1775872400389
    },
    {
      "channel": "canal_41",
      "username": "bot_quod",
      "message": " corporis eaque ipsam consequatur et illum consequatur suscipit aperiam et est ut doloribus veniam vitae ut deserunt occaecati nisi fugit voluptatum tempora laudantium nulla nihil iusto error repellat rerum dolorem",
      "timestamp": 1775872401424
    }
  ]
}
```

### ✔ Dados armazenados

* logins realizados
* canais criados
* inscrições dos usuários
* mensagens publicadas

## 🐳 Containers (Docker)

O sistema é orquestrado com Docker Compose:

### 📄 Serviços

* `client` → cliente Java
* `server` → servidor Python
* `broker` → REQ/REP
* `pubsub-proxy` → PUB/SUB

### 📄 Portas

| Serviço      | Porta |
| ------------ | ----- |
| Broker Front | 5555  |
| Broker Back  | 5556  |
| XSUB         | 5557  |
| XPUB         | 5558  |

---

## 🤖 Comportamento do Cliente (Bot)

Cada cliente executa automaticamente:

1. Realiza login
2. Cria canais até atingir 5 canais
3. Se inscreve em até 3 canais
4. Entra em loop infinito:

   * escolhe um canal aleatório
   * envia 10 mensagens (1s intervalo)
   * escuta mensagens dos canais inscritos

---

## 🔁 Fluxo de Mensagens

### 📌 Publicação

```
Cliente → Broker → Servidor → PubSub Proxy → Clientes inscritos
```

### 📌 Recebimento

* cliente recebe:

  * canal
  * usuário
  * mensagem
  * timestamp de envio
  * timestamp de recebimento



---

## ✅ Conclusão

O sistema implementado representa uma versão simplificada, porém funcional, de uma plataforma de mensagens distribuída, incorporando conceitos fundamentais de sistemas modernos como desacoplamento, comunicação assíncrona e persistência de estado.

O projeto demonstra na prática como arquiteturas distribuídas podem ser construídas utilizando ferramentas leves como ZeroMQ, Docker e Protobuf.
