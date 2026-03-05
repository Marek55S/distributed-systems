import java.io.IOException;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.concurrent.ConcurrentHashMap;


public class Server {
    private final ConcurrentHashMap clientsMap = new ConcurrentHashMap<>();

    private int clientId = 0;

    public int getNewclientId(){
        return clientId++;
    }

    public ServerMain() throws IOException{
        int portNumber = 12345;
        try (ServerSocket serverSocket = new ServerSocket(portNumber)){
            System.out.println("Server is running on port 12345...");

            while(true){
                Socket clientSocket = serverSocket.accept();
                addNewClient(clientSocket);
            }

        } catch (IOException e){
            System.out.println("Error in server: " + e.getMessage());
        }
    }

    private void addNewClient(Socket clientSocket) {
        int clientId = getNewclientId();
        System.out.println("New client connected: " + clientId);
        ServerThread clientThread = new ServerThread(clientSocket, this, clientId);
        clientsMap.put(clientId, clientThread);
    }

    private void removeClient(int clientId) {
        clientsMap.remove(clientId);
    }
    
    private void broadcastMessage(String message, int senderId){
        for (Object clientThread : clientsMap.values()){

        }
    }


    public static void main(String[] args){
        try{
            new Server();
        }
        catch (IOException e){
            System.out.println("Error starting server: " + e.getMessage());
        }
    }

}
