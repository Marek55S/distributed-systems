import java.io.IOException;
import java.net.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;


public class Server {
    private final ConcurrentHashMap<Integer, ServerTCPThread> clientsMap = new ConcurrentHashMap<>();

    private final AtomicInteger clientIdGenerator = new AtomicInteger(1);


    public Server(){
    }

    private void startServer(int portNumber) throws IOException {
        try (ServerSocket serverSocket = new ServerSocket(portNumber)){
            System.out.println("Server is running on port " + portNumber);
            while(true){
                Socket clientSocket = serverSocket.accept();
                addNewClient(clientSocket);
            }

        } catch (IOException e){
            System.out.println("Error in server: " + e.getMessage());
        }
    }

    private void addNewClient(Socket clientSocket) {
        int clientId = clientIdGenerator.getAndIncrement();
        try {
            addTCPConnection(clientId, clientSocket);
            System.out.println("Client " + clientId + " connected.");
        } catch (IOException e) {
            System.out.println("Error adding client " + clientId + ": " + e.getMessage());
            try {
                if (!clientSocket.isClosed()) clientSocket.close();
            } catch (IOException ex) {
                System.out.println("Error closing broken socket: " + ex.getMessage());
            }
        }
    }

    private void addTCPConnection(int clientId, Socket clientSocket) throws IOException{
        ServerTCPThread tcpThread = new ServerTCPThread(clientSocket, this, clientId);
        clientsMap.put(clientId, tcpThread);
        new Thread(tcpThread).start();
    }

    public void registerClientUdp(int clientId, InetAddress address, int portNumber) throws IOException{
        ServerTCPThread client = clientsMap.get(clientId);
        if(client!=null){
            client.setUdpConnectionDetails(address, portNumber);
        }
    }

    public void removeClient(int clientId) {
        clientsMap.remove(clientId);
    }
    
    public void broadcastTCPMessage(String message, int senderId){
        for(ServerTCPThread clientThread : clientsMap.values()){
            if(clientThread.getClientId() != (int) senderId){
                clientThread.sendTCPMessage(message);
            }
        }
    }

    public void broadcastUDPMessage(String message, int senderId, DatagramSocket serverUdpSocket) {
        byte[] data = ("Client " + senderId + " (UDP): " + message).getBytes();

        for (ServerTCPThread client : clientsMap.values()) {
            if (client.getClientId() != senderId && client.getUdpAddress() != null) {
                try {
                    DatagramPacket packet = new DatagramPacket(
                            data, data.length, client.getUdpAddress(), client.getUdpPort()
                    );
                    serverUdpSocket.send(packet);
                } catch (IOException e) {
                    System.out.println("Failed to send UDP to " + client.getClientId());
                }
            }
        }
    }

    public static void main(String[] args){
        try{
            Server server = new Server();
            server.startServer(12345);
        }
        catch (IOException e){
            System.out.println("Error starting server: " + e.getMessage());
        }
    }

}
