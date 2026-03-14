import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.net.InetAddress;
import java.net.Socket;

public class ServerTCPThread implements Runnable{
    private final Socket clientSocket;
    private final Server server;
    private final int clientId;

    private final BufferedReader in;
    private final PrintWriter out;

    private InetAddress udpAddress;
    private int udpPort;

    public ServerTCPThread(Socket clientSocket, Server server, int clientId) throws IOException {
        this.clientSocket = clientSocket;
        this.server = server;
        this.clientId = clientId;
        this.in = new BufferedReader(new InputStreamReader(clientSocket.getInputStream()));
        this.out = new PrintWriter(clientSocket.getOutputStream(), true);
    }

    public void sendGreeting() {
        out.println("ID: " + clientId);
    }

    @Override
    public void run()  {
        try {
            String message;
            while ((message = in.readLine()) != null) {
                System.out.println("Received from client " + clientId + ": " + message);
                server.broadcastTCPMessage("Client " + clientId + ": " + message, clientId);
            }
        } catch (IOException e) {
            System.out.println("Error in client " + clientId + ": " + e.getMessage());
        }
        finally {
            System.out.println("Client " + clientId + " disconnected.");
            server.removeClient(clientId);

            try {
                if (clientSocket != null && !clientSocket.isClosed()) {
                    clientSocket.close();
                }
            } catch (IOException e) {
                System.out.println("Error closing client socket for client " + clientId + ": " + e.getMessage());
            }
        }
    }

    public void sendTCPMessage(String message) {
        out.println(message);
        if (out.checkError()) {
            System.out.println("Failed to send message to client " + clientId);
        }
    }


    public void setUdpConnectionDetails(InetAddress address, int port) {
        this.udpAddress = address;
        this.udpPort = port;
    }

    public InetAddress getUdpAddress() {
        return udpAddress;
    }

    public int getUdpPort() {
        return udpPort;
    }

    public int getClientId() {
        return clientId;
    }

}
