import java.io.IOException;
import java.net.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;


public class Server {
    private final ConcurrentHashMap<Integer, ServerTCPThread> clientsMap = new ConcurrentHashMap<>();
    private final AtomicInteger clientIdGenerator = new AtomicInteger(1);
    private final ExecutorService executor = Executors.newCachedThreadPool();

    private volatile boolean isRunning=false;
    private ServerSocket serverSocket;


    public Server(){
    }

    private void start(int portNumber) {
        try{
            this.isRunning = true;
            this.serverSocket = new ServerSocket(portNumber);
            System.out.println("Server is running on port " + portNumber);

            UdpServerListener udpListener = new UdpServerListener(this, portNumber);
            executor.submit(udpListener);
            System.out.println("UDP listener started on port " + portNumber);


            while(this.isRunning){
                try {
                    Socket clientSocket = serverSocket.accept();
                    addNewClient(clientSocket);
                } catch (IOException e) {
                    if (!isRunning) {
                        System.out.println("Server socket stopped accepting new clients.");                    } else {
                        break;
                    }
                    System.out.println("Error accepting client connection: " + e.getMessage());
                }
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
        tcpThread.sendGreeting();
        executor.submit(tcpThread);
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

    public void stopServer() {
        if(!isRunning) return;
        isRunning = false;
        System.out.println("Stopping server...");

        try{
            if(serverSocket != null && !serverSocket.isClosed()){
                serverSocket.close();
            }

            executor.shutdown();
            if(!executor.awaitTermination(3, TimeUnit.SECONDS)){
                System.out.println("Forcing shutdown of remaining tasks...");
                executor.shutdownNow();
            }
            System.out.println("Server stopped.");
        } catch (Exception e){
            System.out.println("Error closing server socket: " + e.getMessage());
            executor.shutdownNow();
        }
    }

    public static void main(String[] args){
        int portNumber = 12345;
        Server server = new Server();
        Runtime.getRuntime().addShutdownHook(new Thread(server::stopServer));
        server.start(portNumber);
    }
}
