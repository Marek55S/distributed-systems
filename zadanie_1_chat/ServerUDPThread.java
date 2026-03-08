
public class ServerUDPThread implements Runnable{
    private final Server server;
    private final int clientId;

    // when the connection is secured, client should send its clientId to the server
    public ServerUDPThread(Server server) {
        this.server = server;

    }

    private secureUDPConnection(){

    }

    public void sendUDPMessage(String message){
        // Implement UDP message sending logic here
    }

    @Override
    public void run() {

    }
}
