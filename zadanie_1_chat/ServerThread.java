import java.net.Socket;

public class ServerThread implements Runnable{
    private final Socket clientSocket;
    private final Server server;
    private final int clientId;

    public ServerThread(Socket clientSocket, Server server, int clientId){
        this.clientSocket = clientSocket;
        this.server = server;
        this.clientId = clientId;
    }

    @Override
    public void run() {

    }
}
