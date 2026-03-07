import java.io.IOException;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;


public class Server {
    private final ConcurrentHashMap<Integer, ServerThread> clientsThreadMap = new ConcurrentHashMap<>();

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
            ServerThread clientThread = new ServerThread(clientSocket, this, clientId);
            clientsThreadMap.put(clientId, clientThread);
            System.out.println("New client connected: " + clientId);
            new Thread(clientThread).start();
        } catch (IOException e) {
            System.out.println("Error adding client " + clientId + ": " + e.getMessage());
        }
    }

    public void removeClient(int clientId) {
        clientsThreadMap.remove(clientId);
    }
    
    public void broadcastMessage(String message, Object senderId){
        for(ServerThread clientThread : clientsThreadMap.values()){
            if(clientThread.getClientId() != (int) senderId){
                clientThread.sendMessage(message);
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
