import java.io.IOException;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;


public class Server {
    private final ConcurrentHashMap<Integer, ServerTCPThread> clientsThreadMap = new ConcurrentHashMap<>();

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
            ServerTCPThread clientThread = new ServerTCPThread(clientSocket, this, clientId);
            clientsThreadMap.put(clientId, clientThread);
            System.out.println("New client connected: " + clientId);
            new Thread(clientThread).start();
        } catch (IOException e) {
            System.out.println("Error adding client " + clientId + ": " + e.getMessage());
            try {
                if (!clientSocket.isClosed()) clientSocket.close();
            } catch (IOException ex) {
                System.out.println("Error closing broken socket: " + ex.getMessage());
            }
        }
    }

    private void addUDPConnection(){

    }

    public void removeClient(int clientId) {
        clientsThreadMap.remove(clientId);
    }
    
    public void broadcastTCPMessage(String message, Object senderId){
        for(ServerTCPThread clientThread : clientsThreadMap.values()){
            if(clientThread.getClientId() != (int) senderId){
                clientThread.sendTCPMessage(message);
            }
        }
    }

    public void broadcastUDPMessage(String message, Object senderId){
        // Implement UDP broadcasting logic here
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
