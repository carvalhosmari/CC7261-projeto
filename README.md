# CC7261-projeto - Sistema para troca de mensagem instantânea 📨



## 📌 Introdução

Este projeto consiste na implementação de um sistema distribuído para troca de mensagens instantâneas, inspirado em sistemas clássicos como BBS (Bulletin Board System) e IRC (Internet Relay Chat).

A aplicação permite que múltiplos clientes (bots) interajam com servidores para:

- realizar login
- criar e listar canais
- publicar mensagens
- se inscrever em canais
- receber mensagens em tempo real

O sistema evoluiu para incluir **coordenação entre múltiplos servidores**, utilizando um serviço de heartbeat responsável por descoberta de servidores e sincronização de tempo.



## 🏗️ Arquitetura do Sistema

O sistema é composto pelos seguintes componentes:



### 🔹 Cliente (Java)

- Simula usuários (bots)
- Envia requisições (REQ) ao servidor
- Se inscreve em canais via Pub/Sub
- Publica mensagens e escuta eventos em tempo real



### 🔹 Servidor (Python)

- Processa requisições dos clientes
- Gerencia:
  - usuários
  - canais
  - mensagens
  - inscrições
- Realiza persistência em JSON
- Publica mensagens via Pub/Sub
- Consulta o heartbeat para:
  - obter seu rank
  - sincronizar relógio
  - descobrir outros servidores



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



### 🔹 Heartbeat (Python)

Serviço responsável pela **coordenação do sistema distribuído**.

Funções:

- atribuir rank único aos servidores
- manter lista de servidores ativos
- fornecer lista de servidores
- atuar como **fonte de tempo (clock de referência)**

```
Servidor → Heartbeat → (rank + lista + tempo)
```



---



## 🔄 Comunicação



### 📡 REQ/REP (Síncrono)

Utilizado para:

- LOGIN

- CREATE_CHANNEL

- LIST_CHANNELS

- SUBSCRIBE

- PUBLISH

- REGISTER (heartbeat)

- GET_SERVERS (heartbeat)

- SYNC (heartbeat)

  

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

message HBRequest {
  string type = 1;
  string server = 2;
}

message HBResponse {
  string message = 1;
  int32 rank = 2;
  repeated ServerInfo servers = 3;
  int64 timestamp = 4;
}

message ServerInfo {
  string server = 1;
  int32 rank = 2;
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



## ❤️ Heartbeat (Coordenação)

### 🔹 Registro de servidor

```
REGISTER → recebe rank
```

### 🔹 Descoberta

```
GET_SERVERS → lista de servidores
```

### 🔹 Tempo

```
SYNC → timestamp global
```



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
| Heartbeat    | 6667  |



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

## 🔄 Sincronização de Relógio entre Servidores

Foi implementada sincronização de relógio inspirada no algoritmo de
Berkeley.

### 🔹 Funcionamento

-   um servidor é eleito como coordenador
-   os demais servidores solicitam o horário ao coordenador:

```{=html}
<!-- -->
```

    Servidor → Coordenador: GET_TIME
    Coordenador → Servidor: timestamp

-   cada servidor calcula um offset local para ajustar seu relógio

### 🔹 Frequência

-   a sincronização ocorre a cada 15 mensagens processadas

------------------------------------------------------------------------

## 🏆 Eleição de Coordenador

Para suportar múltiplos servidores, foi implementado um mecanismo de
eleição.

### 🔹 Critério

-   baseado no rank atribuído pelo heartbeat
-   menor rank → maior prioridade

### 🔹 Divulgação

-   o coordenador publica sua identidade via Pub/Sub:

```{=html}
<!-- -->
```

    Tópico: servers
    Mensagem: COORDINATOR:<nome>

### 🔹 Tolerância a falhas

-   caso o coordenador não responda:
    -   uma nova eleição é realizada automaticamente

------------------------------------------------------------------------

## 🔗 Comunicação entre Servidores

Foi adicionada comunicação direta entre servidores para suportar
sincronização.

### 📡 Porta interna

    tcp://<server>:7000

### 🔹 Uso

-   requisição de tempo (`GET_TIME`)
-   suporte à sincronização distribuída

---

## 🔁 Replicação e Consistência dos Dados

### 📌 Problema

Inicialmente, o sistema utilizava o broker com balanceamento de carga Round-Robin.  
Com isso, cada servidor recebia apenas parte das mensagens trocadas pelos clientes.

Exemplo:

- servidor A → recebe mensagens 1, 3 e 5
- servidor B → recebe mensagens 2, 4 e 6

Esse comportamento gerava dois problemas principais:

1. perda parcial do histórico caso um servidor falhasse
2. inconsistência nos dados entre os servidores

Além disso, clientes conectados a servidores diferentes poderiam visualizar históricos distintos.

---

### ✅ Solução Implementada

Foi implementado um mecanismo de replicação ativa entre os servidores utilizando comunicação servidor ↔ servidor via ZeroMQ.

O modelo adotado foi baseado em:

- replicação total (full replication)
- consistência eventual (eventual consistency)

Nesse modelo:

- todos os servidores mantêm uma cópia completa dos dados
- atualizações são propagadas para todas as réplicas
- servidores recuperam automaticamente o estado após falhas

---

### 🏗️ Arquitetura da Replicação

Cada servidor passou a possuir um socket interno:

```python
internal_socket = context.socket(zmq.REP)
internal_socket.bind(f"tcp://*:{SERVER_PORT}")
```

Esse socket é utilizado exclusivamente para:

- replicação de eventos
- sincronização de estado
- sincronização de relógio
- comunicação interna entre servidores

### 📡 Replicação de Eventos

Sempre que um servidor recebe uma operação que altera o estado do sistema, ele replica essa alteração para os demais servidores ativos.

Eventos replicados:

LOGIN
CREATE_CHANNEL
SUBSCRIBE
PUBLISH

A replicação ocorre através da função:
```python
replicate_data(event_type, payload)
```
Cada réplica recebe um evento contendo:
```json
{
  "event": "PUBLISH",
  "payload": {
    "channel": "canal_1",
    "username": "bot_x",
    "message": "hello",
    "timestamp": "...",
    "count": 42
  }
}
```

### 🧠 Relógio Lógico Distribuído

Para manter ordenação consistente entre mensagens replicadas, foi implementado um contador lógico distribuído baseado no algoritmo de Lamport.

Cada mensagem possui:

- timestamp físico
- contador lógico (count)

Isso garante:

- ordenação causal
- sincronização lógica entre servidores
- prevenção de conflitos de ordenação

### 🔄 Recuperação Automática de Estado

Quando um servidor reinicia após falha, ele executa sincronização automática com os demais servidores.

A sincronização utiliza:
```python
GET_STATE
```

O servidor ativo envia todo seu estado atual:
```json
{
  "logins": [],
  "channels": [],
  "subscriptions": {},
  "messages": []
}
```
O servidor recuperado realiza merge do estado recebido com seu estado local.

### 🔀 Merge de Dados

Foi implementado um mecanismo de merge incremental para:

- evitar duplicatas
- recuperar mensagens perdidas
- consolidar estados divergentes

O merge compara:

- timestamp
- username
- conteúdo da mensagem
- contador lógico

Exemplo:
```python
exists = any(
    msg["timestamp"] == message["timestamp"]
    and msg["username"] == message["username"]
    and msg["message"] == message["message"]
    for msg in local_data["messages"]
)
```
### ⏱️ Tolerância a Falhas

Foi adicionada tolerância a falhas utilizando timeout nos sockets internos do ZeroMQ.

Configuração:
```python
sock.setsockopt(zmq.RCVTIMEO, 2000)
sock.setsockopt(zmq.SNDTIMEO, 2000)
```

Com isso:

- servidores não travam caso outro servidor falhe
- replicações falhas são ignoradas
- o sistema continua funcionando normalmente

### 🔁 Sincronização Contínua

Foi implementada uma thread de sincronização periódica:
```python
sync_state_loop()
```

Essa thread:

- tenta recuperar estado continuamente
- reintegra servidores recuperados
- garante convergência eventual dos dados

### ✅ Resultado Final

Com a solução implementada:

- todos os servidores mantêm cópia completa dos dados
- falhas não causam perda de histórico
- servidores recuperam automaticamente o estado
- clientes recebem visão consistente do sistema
- o sistema continua operando mesmo com falha de réplicas

A solução implementa uma arquitetura distribuída tolerante a falhas baseada em ***replicação ativa e consistência eventual***.

--- 

## ✅ Conclusão

O sistema implementado representa uma versão simplificada, porém funcional, de uma plataforma de mensagens distribuída, incorporando conceitos fundamentais de sistemas modernos como desacoplamento, comunicação assíncrona e persistência de estado.

O projeto demonstra na prática como arquiteturas distribuídas podem ser construídas utilizando ferramentas leves como ZeroMQ, Docker e Protobuf.