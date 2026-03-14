import java.io.BufferedReader;
import java.io.IOException;
import java.io.PrintWriter;
import java.net.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;


public class Client {
    public static final String multicastAddress = "230.0.0.1";
    public static final int multicastPort = 4446;

    private final String serverAddress;
    private final int serverPort;
    private final Socket tcpSocket;
    private final BufferedReader in;
    private final PrintWriter out;
    private final ExecutorService executor = Executors.newCachedThreadPool();
    private final DatagramSocket udpSocket;
    private int clientId;
    private MulticastSocket multicastSocket;


    public Client(String serverAddress, int serverPort) throws IOException {
        this.tcpSocket = new Socket(serverAddress, serverPort);
        this.serverAddress = serverAddress;
        this.serverPort = serverPort;
        this.in = new BufferedReader(new java.io.InputStreamReader(tcpSocket.getInputStream()));
        this.out = new PrintWriter(tcpSocket.getOutputStream(), true);

        String welcomeMsg = in.readLine();
        if(welcomeMsg != null && welcomeMsg.startsWith("ID:")){
            this.clientId = Integer.parseInt(welcomeMsg.substring(3).trim());
            System.out.println("Connected with server. Client ID: " + clientId);
        }
        this.udpSocket = new DatagramSocket();
        sendUDPMessage("INIT:" + clientId);
    }

    public void start() throws IOException {
        this.multicastSocket = new MulticastSocket(multicastPort);
        SocketAddress group = new InetSocketAddress(InetAddress.getByName(multicastAddress), multicastPort);
        NetworkInterface networkInterface = NetworkInterface.getByInetAddress(InetAddress.getLocalHost());
        multicastSocket.joinGroup(group, networkInterface);

        executor.submit(new ClientTCPListener(this));
        executor.submit(new ClientUDPListener(udpSocket));
        executor.submit(new ConsoleReader(this));
        executor.submit(new ClientMulticastListener(this,multicastSocket));
    }

    public void sendMessageTCP(String message){
        out.println(message);
        if (out.checkError()) {
            System.out.println("Failed to send message to server.");
        }
    }

    public void sendUDPMessage(String message) {
        try{
            byte[] buffer = message.getBytes();
            InetAddress address = InetAddress.getByName(serverAddress);

            DatagramPacket packet = new DatagramPacket(buffer, buffer.length,address,serverPort);
            udpSocket.send(packet);
        } catch (IOException e){
            System.out.println("Error sending UDP message: " + e.getMessage());
        }
    }

    public void sendMulticastMessage(String message){
        try{
            byte[] buffer = message.getBytes();
            InetAddress group = InetAddress.getByName(multicastAddress);
            DatagramPacket packet = new DatagramPacket(buffer, buffer.length, group, multicastPort);
            udpSocket.send(packet);
        } catch (IOException e){
            System.out.println("Error sending multicast message: " + e.getMessage());
        }
    }

    public void disconnect() {
        try{
            if (tcpSocket != null && !tcpSocket.isClosed()) {
                tcpSocket.close();
            }
            if (udpSocket != null && !udpSocket.isClosed()) {
                udpSocket.close();
            }
            executor.shutdown();

            if(!executor.awaitTermination(2, TimeUnit.SECONDS)){
                System.out.println("Forcing shutdown of client threads...");
                executor.shutdownNow();
            }

            System.out.println("Connection closed");

        } catch (IOException e) {
            System.out.println("Error closing client socket: " + e.getMessage());
        } catch (InterruptedException e) {
            executor.shutdownNow();
            Thread.currentThread().interrupt();
        }
    }

    public BufferedReader getIn() {
        return in;
    }


    public int getClientId() {
        return clientId;
    }


    public static void main(String[] args){
        String serverAddress = "localhost";
        int serverPort = 12345;

        try {
            Client client = new Client(serverAddress, serverPort);
            client.start();
        } catch (IOException e) {
            System.out.println("Error connecting to server: " + e.getMessage());
        }
    }
}
