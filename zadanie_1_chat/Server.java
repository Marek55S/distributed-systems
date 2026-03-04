import java.io.IOException;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.concurrent.ConcurrentHashMap;


public class Server {
    private final ConcurrentHashMap clientsMap = new ConcurrentHashMap<>();

    private int clientNumber = 0;

    public int getNewClientNumber(){
        return clientNumber++;
    }

    public ServerMain() throws IOException{
        int portNumber = 12345;
        try (ServerSocket serverSocket = new ServerSocket(portNumber)){
            System.out.println("Server is running on port 12345...");

            while(true){
                Socket clientSocket = serverSocket.accept();
            }

        } catch
    }




    public static void main(String[] args){
        try{
            new ServerMain();
        }
        catch (IOException e){
            System.out.println("Error starting server: " + e.getMessage());
        }
    }

}
