# CC7261-projeto - Sistema para troca de mensagem instantânea 📨

## 📌 Introdução

Este projeto implementa um sistema de troca de mensagens inspirado em arquiteturas modernas de sistemas distribuídos. A aplicação simula um ambiente de comunicação entre clientes e servidores utilizando um **broker intermediário**, permitindo desacoplamento, escalabilidade e flexibilidade na comunicação.

A arquitetura geral do sistema segue o modelo:

```
Client → Broker → Server (Worker)
```

Onde:

* **Client** envia requisições (login, criação de canais, etc.)
* **Broker** atua como intermediário e roteador de mensagens
* **Server (Worker)** processa as requisições e mantém o estado da aplicação

---

## 🏗️ Arquitetura do Sistema

O sistema é composto por três componentes principais:

### 🔹 Client (Java)

Responsável por enviar requisições ao sistema.

### 🔹 Broker (Python + ZeroMQ)

Atua como intermediário entre clientes e servidores, utilizando o padrão **ROUTER/DEALER** para encaminhamento de mensagens.

### 🔹 Server / Worker (Python)

Processa as requisições recebidas e mantém o estado da aplicação (ex: canais criados).

---

## ⚙️ Tecnologias e Escolhas de Projeto

### 💻 Linguagens

* **Java (Client)**

  * Escolhida para simular um cliente tipicamente usado em aplicações reais.
  * Forte tipagem e integração com Protobuf.
  * Uso de Maven para gerenciamento de dependências.

* **Python (Server e Broker)**

  * Simplicidade e rapidez no desenvolvimento.
  * Excelente suporte para ZeroMQ e Protobuf.
  * Ideal para prototipação de sistemas distribuídos.

---

### 🔄 Comunicação (ZeroMQ)

Foi utilizado o **ZeroMQ** como middleware de comunicação por ser:

* Leve e de alto desempenho
* Sem necessidade de servidor central (broker implementado manualmente)
* Suporte a múltiplos padrões de comunicação

#### Padrão utilizado:

* **REQ/REP** (Client ↔ Server via Broker)
* **ROUTER/DEALER** (no Broker)

Esse modelo permite:

* Desacoplamento entre cliente e servidor
* Possibilidade de múltiplos servidores (load balancing)
* Facilidade de evolução para outros padrões (ex: PUB/SUB)

---

### 📦 Serialização (Protocol Buffers)

Foi utilizado **Protocol Buffers (Protobuf)** para serialização de mensagens.

#### Motivações:

* Alto desempenho (binário e compacto)
* Forte tipagem
* Compatível com múltiplas linguagens (Java + Python)
* Facilita evolução do contrato (schema evolution)

#### Estrutura das mensagens:

* `ChatRequest` → enviado pelo cliente
* `ChatResponse` → retornado pelo servidor

---

### 📦 Persistência

Atualmente, o sistema utiliza **armazenamento em disco** no servidor:

#### 📂 Implementação

Cada servidor mantém seu próprio arquivo:

```
/app/data/data.json
```

Com Docker:

```
./data → /app/data
```

---

##### 📌 Estrutura do arquivo

```json
{
  "logins": [
    {
      "username": "bot1",
      "timestamp": 1710880000000
    }
  ],
  "channels": [
    "geral"
  ]
}
```

---

#### 🧠 Dados Persistidos

O sistema armazena:

* ✔ Histórico de logins (usuário + timestamp)
* ✔ Lista de canais criados

---

## 🐳 Containerização

O projeto utiliza **Docker e Docker Compose** para orquestração dos serviços.

### Benefícios:

* Ambiente padronizado
* Facilidade de execução
* Isolamento dos serviços

---

## 🚀 Funcionalidades atuais

* Login de usuário
* Criação de canais
* Listagem de canais
* Comunicação cliente-servidor via broker

---

## 🔮 Próximos passos

* Envio de mensagens entre usuários

---

## 🧩 Conclusão

Este projeto demonstra, de forma prática, conceitos fundamentais de sistemas distribuídos:

* Comunicação desacoplada
* Uso de brokers
* Serialização eficiente
* Arquitetura escalável

Apesar de simplificado, ele representa uma base sólida para sistemas reais de mensageria.

---
