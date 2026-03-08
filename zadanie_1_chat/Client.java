import java.io.BufferedReader;
import java.io.IOException;
import java.io.PrintWriter;
import java.net.Socket;



public class Client {
    private final String serverAddress;
    private final int serverPort;
    private final Socket socket;
    private final BufferedReader in;
    private final PrintWriter out;

    public Client(String serverAddress, int serverPort) throws IOException {
        this.socket = new Socket(serverAddress, serverPort);
        this.serverAddress = serverAddress;
        this.serverPort = serverPort;
        this.in = new BufferedReader(new java.io.InputStreamReader(socket.getInputStream()));
        this.out = new PrintWriter(socket.getOutputStream(), true);
        System.out.println("Connected to server at " + serverAddress + ":" + serverPort);
    }

    public void sendMessageTCP(String message){
        out.println(message);
        if (out.checkError()) {
            System.out.println("Failed to send message to server.");
        }
    }

    public void disconnect() {
        try{
            if (socket != null && !socket.isClosed()) {
                socket.close();
            }
            System.out.println("Connection closed");
        } catch (IOException e) {
            System.out.println("Error closing client socket: " + e.getMessage());
        }
    }

    public BufferedReader getIn() {
        return in;
    }

    public static void main(String[] args){
        String serverAddress = "localhost";
        int serverPort = 12345;

        try {
            Client client = new Client(serverAddress, serverPort);
            new Thread(new ClientTCPListener(client)).start();
            new Thread(new ConsoleReader(client)).start();
        } catch (IOException e) {
            System.out.println("Error connecting to server: " + e.getMessage());
        }
    }
}
