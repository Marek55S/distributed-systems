import com.rabbitmq.client.*;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;

public class Agency {
    private static final String EXCHANGE_NAME = "space_exchange";

    public static void main(String[] argv) throws Exception {
        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));
        System.out.print("Enter a name of space agency: ");
        String agencyName = reader.readLine();

        ConnectionFactory factory = new ConnectionFactory();
        factory.setHost("localhost");
        Connection connection = factory.newConnection();
        Channel channel = connection.createChannel();

        channel.exchangeDeclare(EXCHANGE_NAME, BuiltinExchangeType.TOPIC);

        String queueName = channel.queueDeclare().getQueue();

        channel.queueBind(queueName, EXCHANGE_NAME, "ack." + agencyName);
        channel.queueBind(queueName, EXCHANGE_NAME, "admin.agencies");
        channel.queueBind(queueName, EXCHANGE_NAME, "admin.all");

        System.out.println("Agency " + agencyName + " ready. Waiting for messages...");

        DeliverCallback deliverCallback = (consumerTag, delivery) -> {
            String message = new String(delivery.getBody(), StandardCharsets.UTF_8);
            System.out.println("\n[RECEIVED] " + message);
            System.out.print("Order a service (people/cargo/satellite) or 'exit': ");
        };
        channel.basicConsume(queueName, true, deliverCallback, consumerTag -> {});

        int taskCounter = 1;
        while (true) {
            System.out.print("Order a service (people/cargo/satellite) or 'exit': ");
            String serviceType = reader.readLine();
            if ("exit".equalsIgnoreCase(serviceType)) break;

            if (!serviceType.equals("people") && !serviceType.equals("cargo") && !serviceType.equals("satellite")) {
                System.out.println("Unknown service!");
                continue;
            }

            String taskId = agencyName + "-" + taskCounter++;
            String routingKey = "task." + serviceType;
            String message = taskId + "|" + agencyName + "|" + serviceType;

            channel.basicPublish(EXCHANGE_NAME, routingKey, null, message.getBytes(StandardCharsets.UTF_8));
            System.out.println("[SENT] Task: " + taskId + " (type: " + serviceType + ")");
        }

        channel.close();
        connection.close();
    }
}