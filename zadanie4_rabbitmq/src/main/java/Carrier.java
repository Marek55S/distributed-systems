import com.rabbitmq.client.*;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;

public class Carrier {
    private static final String EXCHANGE_NAME = "space_exchange";

    public static void main(String[] argv) throws Exception {
        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));
        System.out.print("Enter carrier name: ");
        String carrierName = reader.readLine();

        System.out.println("Choose 2 services (people, cargo, satellite).");
        System.out.print("Service 1: ");
        String service1 = reader.readLine();
        System.out.print("Service 2: ");
        String service2 = reader.readLine();

        ConnectionFactory factory = new ConnectionFactory();
        factory.setHost("localhost");
        Connection connection = factory.newConnection();
        Channel channel = connection.createChannel();

        channel.exchangeDeclare(EXCHANGE_NAME, BuiltinExchangeType.TOPIC);

        channel.basicQos(1);

        channel.queueDeclare("queue_" + service1, false, false, false, null);
        channel.queueDeclare("queue_" + service2, false, false, false, null);

        channel.queueBind("queue_" + service1, EXCHANGE_NAME, "task." + service1);
        channel.queueBind("queue_" + service2, EXCHANGE_NAME, "task." + service2);

        String adminQueue = channel.queueDeclare().getQueue();
        channel.queueBind(adminQueue, EXCHANGE_NAME, "admin.carriers");
        channel.queueBind(adminQueue, EXCHANGE_NAME, "admin.all");

        System.out.println("Carrier " + carrierName + " ready to handle: " + service1 + ", " + service2);

        DeliverCallback taskCallback = (consumerTag, delivery) -> {
            String message = new String(delivery.getBody(), StandardCharsets.UTF_8);
            String[] parts = message.split("\\|");
            String taskId = parts[0];
            String agencyName = parts[1];

            System.out.println("\n[TASK] Received for execution: " + taskId);

            System.out.println("[TASK] Completed " + taskId + ". Sending confirmation...");

            String ackMessage = "Task " + taskId + " has been completed by " + carrierName;
            String ackRoutingKey = "ack." + agencyName;

            channel.basicPublish(EXCHANGE_NAME, ackRoutingKey, null, ackMessage.getBytes(StandardCharsets.UTF_8));

            channel.basicAck(delivery.getEnvelope().getDeliveryTag(), false);
        };

        DeliverCallback adminCallback = (consumerTag, delivery) -> {
            String message = new String(delivery.getBody(), StandardCharsets.UTF_8);
            System.out.println("\n[ADMIN INFO] " + message);
        };

        channel.basicConsume("queue_" + service1, false, taskCallback, consumerTag -> {});
        channel.basicConsume("queue_" + service2, false, taskCallback, consumerTag -> {});
        channel.basicConsume(adminQueue, true, adminCallback, consumerTag -> {});
    }
}