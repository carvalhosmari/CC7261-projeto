import org.zeromq.ZMQ;
import chat.Chat;
import com.github.javafaker.Faker;

public class Main {

    private static ZMQ.Socket socket;

    public static void main(String[] args) {

        ZMQ.Context context = ZMQ.context(1);
        socket = context.socket(ZMQ.REQ);
        socket.connect("tcp://broker:5555");

        login(generateBot());

        listChannels();

        createChannel(generateChannel());

        listChannels();
    }

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

    private static void listChannels() {
        Chat.ChatRequest req = Chat.ChatRequest.newBuilder()
                .setType("LIST_CHANNELS")
                .setTimestamp(System.currentTimeMillis())
                .build();

        send(req);
    }

    private static String generateChannel() {
        Faker faker = new Faker();
        String channel = faker.lorem().word();

        return channel;
    }

    private static String generateBot() {
        Faker faker = new Faker();
        String bot = "bot_" + faker.lorem().word();

        return bot;
    }

    private static void send(Chat.ChatRequest req) {
        System.out.println("[CLIENT] Enviando: " + req.getType());

        socket.send(req.toByteArray());

        byte[] reply = socket.recv();

        try {
            Chat.ChatResponse res = Chat.ChatResponse.parseFrom(reply);

            System.out.println("[CLIENT] Resposta: " + res.getMessage());

            if (res.getChannelsCount() > 0) {
                System.out.println("[CLIENT] Canais: " + res.getChannelsList());
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}