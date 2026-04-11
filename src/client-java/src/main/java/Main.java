import org.zeromq.ZMQ;
import chat.Chat;
import com.github.javafaker.Faker;
import java.util.*;

public class Main {

    private static ZMQ.Socket socket;
    private static Set<String> subscribedChannels = new HashSet<>();
    private static Random random = new Random();

    public static void main(String[] args) {

        ZMQ.Context context = ZMQ.context(1);

        // REQ → Broker
        socket = context.socket(ZMQ.REQ);
        socket.connect("tcp://broker:5555");

        // SUB → PubSub Proxy
        ZMQ.Socket sub = context.socket(ZMQ.SUB);
        sub.connect("tcp://pubsub-proxy:5558");

        String bot = generateBot();

        login(bot);

        // THREAD DE ESCUTA (Pub/Sub)
        new Thread(() -> {
            while (true) {
                try {
                    byte[] topic = sub.recv();
                    byte[] msg = sub.recv();

                    Chat.ChatRequest req = Chat.ChatRequest.parseFrom(msg);

                    long receiveTime = System.currentTimeMillis();

                    System.out.println("\n[CANAL: " + req.getChannel() + "]");
                    System.out.println("Mensagem: " + req.getMessage());
                    System.out.println("Enviado em: " + req.getTimestamp());
                    System.out.println("Recebido em: " + receiveTime);

                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }).start();

        // LOOP PRINCIPAL
        while (true) {

            List<String> channels = listChannels();

            // REGRA 1 — criar canais até ter 5
            if (channels.size() < 5) {
                String newChannel = generateChannel();
                createChannel(newChannel);
                channels = listChannels();
            }

            // REGRA 2 — se inscrever em até 3 canais
            if (subscribedChannels.size() < 3 && !channels.isEmpty()) {
                String randomChannel = channels.get(random.nextInt(channels.size()));
                subscribe(sub, randomChannel, bot);
            }

            // REGRA 3 — enviar mensagens
            if (!channels.isEmpty()) {

                String channel = channels.get(random.nextInt(channels.size()));

                for (int i = 0; i < 10; i++) {
                    publish(channel, generateMessage(), bot);

                    try {
                        Thread.sleep(1000);
                    } catch (InterruptedException e) {
                        e.printStackTrace();
                    }
                }
            }
        }
    }

    // ===============================
    // REQ/REP METHODS
    // ===============================

    private static void login(String username) {
        Chat.ChatRequest req = Chat.ChatRequest.newBuilder()
                .setType("LOGIN")
                .setUsername(username)
                .setTimestamp(System.currentTimeMillis())
                .build();

        send(req);
    }

    private static void createChannel(String channel) {
        Chat.ChatRequest req = Chat.ChatRequest.newBuilder()
                .setType("CREATE_CHANNEL")
                .setChannel(channel)
                .setTimestamp(System.currentTimeMillis())
                .build();

        send(req);
    }

    private static List<String> listChannels() {
        Chat.ChatRequest req = Chat.ChatRequest.newBuilder()
                .setType("LIST_CHANNELS")
                .setTimestamp(System.currentTimeMillis())
                .build();

        socket.send(req.toByteArray());

        byte[] reply = socket.recv();

        try {
            Chat.ChatResponse res = Chat.ChatResponse.parseFrom(reply);
            return res.getChannelsList();
        } catch (Exception e) {
            e.printStackTrace();
        }

        return new ArrayList<>();
    }

    private static void publish(String channel, String msg, String username) {
        Chat.ChatRequest req = Chat.ChatRequest.newBuilder()
                .setType("PUBLISH")
                .setUsername(username)
                .setChannel(channel)
                .setMessage(msg)
                .setTimestamp(System.currentTimeMillis())
                .build();

        send(req);
    }

    private static void send(Chat.ChatRequest req) {
        System.out.println("[CLIENT] Enviando: " + req.getType());

        socket.send(req.toByteArray());

        byte[] reply = socket.recv();

        try {
            Chat.ChatResponse res = Chat.ChatResponse.parseFrom(reply);
            System.out.println("[CLIENT] Resposta: " + res.getMessage());

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    // ===============================
    //  SUBSCRIBE
    // ===============================

    private static void subscribe(ZMQ.Socket sub, String channel, String username) {

        if (!subscribedChannels.contains(channel)) {

            //SUB local (ZeroMQ)
            sub.subscribe(channel.getBytes());

            // SUB remoto (servidor)
            Chat.ChatRequest req = Chat.ChatRequest.newBuilder()
                    .setType("SUBSCRIBE")
                    .setUsername(username)
                    .setChannel(channel)
                    .setTimestamp(System.currentTimeMillis())
                    .build();

            send(req);

            subscribedChannels.add(channel);

            System.out.println("[CLIENT] Inscrito no canal: " + channel);
        }
    }

    // ===============================
    // UTIL
    // ===============================

    private static String generateBot() {
        Faker faker = new Faker();
        String bot = "bot_" + faker.lorem().word();

        return bot;
    }

    private static String generateChannel() {
        return "canal_" + random.nextInt(100);
    }

    private static String generateMessage() {
        Faker faker = new Faker();
        String message = "";
        
        for(int i = 0; i <= random.nextInt(25, 50); i++) {
            message += " " + faker.lorem().word();
        }
         
        return message;
    }
}