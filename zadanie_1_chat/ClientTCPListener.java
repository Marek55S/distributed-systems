import java.io.BufferedReader;
import java.io.IOException;

public class ClientTCPListener implements Runnable{
    private final BufferedReader in;

    public ClientTCPListener(Client client) {
        this.in = client.getIn();
    }

    @Override
    public void run() {
        try {
            String message;
            while ((message = this.in.readLine()) != null) {
                System.out.println("Received from server: " + message);
            }
        } catch (IOException e) {
            if (e.getMessage().equalsIgnoreCase("Socket closed")) {
                System.out.println("TCP listener stopped.");
            } else {
                System.out.println("Error in TCP listener: " + e.getMessage());
            }
        }
    }

}
