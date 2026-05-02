import org.zeromq.ZMQ;
import chat.Chat;
import com.github.javafaker.Faker;

import java.util.*;

public class Main {

    // ===============================
    // STATE
    // ===============================

    private static ZMQ.Socket socket;
    private static final Set<String> subscribedChannels = new HashSet<>();
    private static final Random random = new Random();
    private static final Faker faker = new Faker();

    private static int logicalClock = 0;

    // ===============================
    // MAIN
    // ===============================

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

        startSubscriberThread(sub);

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

                    incrementClock(); // Lamport BEFORE send

                    publish(channel, generateMessage(), bot);

                    sleep(1000);
                }
            }
        }
    }

    // ===============================
    // SUBSCRIBER THREAD
    // ===============================

    private static void startSubscriberThread(ZMQ.Socket sub) {

        new Thread(() -> {
            while (true) {
                try {
                    byte[] topic = sub.recv();
                    byte[] msg = sub.recv();

                    Chat.ChatRequest req = Chat.ChatRequest.parseFrom(msg);

                    // Lamport update on receive
                    updateClock(req.getCount());

                    long receiveTime = System.currentTimeMillis();
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }).start();
    }

    // ===============================
    // REQ/REP METHODS
    // ===============================

    private static void login(String username) {
        send(buildBaseRequest("LOGIN")
                .setUsername(username)
                .setCount(logicalClock)
                .setTimestamp(System.currentTimeMillis())
                .build());
    }

    private static void createChannel(String channel) {
        send(buildBaseRequest("CREATE_CHANNEL")
                .setChannel(channel)
                .setCount(logicalClock)
                .setTimestamp(System.currentTimeMillis())
                .build());
    }

    private static List<String> listChannels() {

        Chat.ChatRequest req = buildBaseRequest("LIST_CHANNELS").build();

        socket.send(req.toByteArray());

        byte[] reply = socket.recv();

        try {
            Chat.ChatResponse res = Chat.ChatResponse.parseFrom(reply);

            updateClock(res.getCount()); // Lamport on receive

            return res.getChannelsList();

        } catch (Exception e) {
            e.printStackTrace();
        }

        return new ArrayList<>();
    }

    private static void publish(String channel, String msg, String username) {

        Chat.ChatRequest req = buildBaseRequest("PUBLISH")
                .setUsername(username)
                .setChannel(channel)
                .setMessage(msg)
                .setCount(logicalClock)
                .setTimestamp(System.currentTimeMillis())
                .build();

        send(req);
    }

    private static void send(Chat.ChatRequest req) {

        System.out.println("[CLIENT] Enviando: " + req.getType() + " | clock=" + logicalClock);

        socket.send(req.toByteArray());

        byte[] reply = socket.recv();

        try {
            Chat.ChatResponse res = Chat.ChatResponse.parseFrom(reply);

            updateClock(res.getCount()); // Lamport on receive

            System.out.println("[CLIENT] Resposta: " + res.getMessage() + " | clock=" + logicalClock);

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    // ===============================
    // SUBSCRIBE
    // ===============================

    private static void subscribe(ZMQ.Socket sub, String channel, String username) {

        if (subscribedChannels.contains(channel)) {
            return;
        }

        // SUB local
        sub.subscribe(channel.getBytes());

        // SUB remoto
        send(buildBaseRequest("SUBSCRIBE")
                .setUsername(username)
                .setChannel(channel)
                .setCount(logicalClock)
                .setTimestamp(System.currentTimeMillis())
                .build());

        subscribedChannels.add(channel);

        System.out.println("[CLIENT] Inscrito no canal: " + channel);
    }

    // ===============================
    // LAMPORT CLOCK
    // ===============================

    private static void incrementClock() {
        logicalClock++;
    }

    private static void updateClock(int received) {
        logicalClock = Math.max(logicalClock, received) + 1;
    }

    private static Chat.ChatRequest.Builder buildBaseRequest(String type) {
        return Chat.ChatRequest.newBuilder()
                .setType(type)
                .setCount(logicalClock)
                .setTimestamp(System.currentTimeMillis());
    }

    // ===============================
    // UTIL
    // ===============================

    private static String generateBot() {
        return "bot_" + faker.lorem().word();
    }

    private static String generateChannel() {
        return "canal_" + random.nextInt(100);
    }

    private static String generateMessage() {
        StringBuilder message = new StringBuilder();

        int size = random.nextInt(25, 50);

        for (int i = 0; i < size; i++) {
            message.append(" ").append(faker.lorem().word());
        }

        return message.toString();
    }

    private static void sleep(int ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}