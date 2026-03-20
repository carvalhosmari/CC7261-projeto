FROM maven:3.9.6-eclipse-temurin-17

WORKDIR /app

# Copia proto compartilhado
COPY proto ./proto

# Copia projeto do cliente
COPY client-java ./client-java

# Entra no diretório do cliente
WORKDIR /app/client-java

# Build
RUN mvn clean package

# Executa
CMD ["java", "-jar", "target/client.jar"]