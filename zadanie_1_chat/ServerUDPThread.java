
public class ServerUDPThread implements Runnable{
    private final Server server;
    private final int clientId;

    // when the connection is secured, client should send its clientId to the server
    public ServerUDPThread(Server server) {
        this.server = server;

    }

    @Override
    public void run() {

    }
}
