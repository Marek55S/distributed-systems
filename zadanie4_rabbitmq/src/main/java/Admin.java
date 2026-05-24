import com.rabbitmq.client.*;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;

public class Admin {
    private static final String EXCHANGE_NAME = "space_exchange";

    public static void main(String[] argv) throws Exception {
        ConnectionFactory factory = new ConnectionFactory();
        factory.setHost("localhost");
        Connection connection = factory.newConnection();
        Channel channel = connection.createChannel();

        channel.exchangeDeclare(EXCHANGE_NAME, BuiltinExchangeType.TOPIC);

        String queueName = channel.queueDeclare().getQueue();
        channel.queueBind(queueName, EXCHANGE_NAME, "task.#");
        channel.queueBind(queueName, EXCHANGE_NAME, "ack.#");

        System.out.println("System administrator connected.");

        DeliverCallback deliverCallback = (consumerTag, delivery) -> {
            String message = new String(delivery.getBody(), StandardCharsets.UTF_8);
            String routingKey = delivery.getEnvelope().getRoutingKey();
            System.out.println("[LOG] Intercepted (" + routingKey + "): " + message);
            printMenu();
        };
        channel.basicConsume(queueName, true, deliverCallback, consumerTag -> {});

        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));
        while (true) {
            printMenu();
            String option = reader.readLine();

            String routingKey = "";
            if (option.equals("1")) routingKey = "admin.agencies";
            else if (option.equals("2")) routingKey = "admin.carriers";
            else if (option.equals("3")) routingKey = "admin.all";
            else continue;

            System.out.print("Enter message content: ");
            String message = "[ADMIN] " + reader.readLine();

            channel.basicPublish(EXCHANGE_NAME, routingKey, null, message.getBytes(StandardCharsets.UTF_8));
            System.out.println("Sent message with routing key: " + routingKey);
        }
    }

    private static void printMenu() {
        System.out.print("\nSend message to: [1] Agencies, [2] Carriers, [3] All: ");
    }
}