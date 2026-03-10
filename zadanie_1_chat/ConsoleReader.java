import java.util.Scanner;

public class ConsoleReader implements Runnable{
    private final Client client;
    private final Scanner keyboardScanner;

    public ConsoleReader(Client client){
        this.client = client;
        this.keyboardScanner = new Scanner(System.in);
    }

    @Override
    public void run() {
        while (true) {
            String message = keyboardScanner.nextLine();
            if (message.equalsIgnoreCase("exit")) {
                System.out.println("Exiting...");
                client.disconnect();
                break;
            } else if (message.startsWith("U ")){
                String udpConetent = message.substring(2);
                client.sendUDPMessage("MSG:" + client.getClientId() + ":" + udpConetent);
            }
            client.sendMessageTCP(message);
        }
        keyboardScanner.close();
    }
}
