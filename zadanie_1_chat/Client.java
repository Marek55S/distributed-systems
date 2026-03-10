import java.io.BufferedReader;
import java.io.IOException;
import java.io.PrintWriter;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.Socket;



public class Client {
    private final String serverAddress;
    private final int serverPort;
    private final Socket tcpSocket;
    private final BufferedReader in;
    private final PrintWriter out;

    private DatagramSocket udpSocket;
    private int clientId;

    public Client(String serverAddress, int serverPort) throws IOException {
        this.tcpSocket = new Socket(serverAddress, serverPort);
        this.serverAddress = serverAddress;
        this.serverPort = serverPort;
        this.in = new BufferedReader(new java.io.InputStreamReader(tcpSocket.getInputStream()));
        this.out = new PrintWriter(tcpSocket.getOutputStream(), true);

        String welcomeMsg = in.readLine();
        if(welcomeMsg != null && welcomeMsg.startsWith("ID:")){
            this.clientId = Integer.parseInt(welcomeMsg.substring(3));
            System.out.println("Connected with server. Client ID: " + clientId);
        }
        this.udpSocket = new DatagramSocket();
        sendUDPMessage("INIT:" + clientId);
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

    public void disconnect() {
        try{
            if (tcpSocket != null && !tcpSocket.isClosed()) {
                tcpSocket.close();
            }
            if (udpSocket != null && !udpSocket.isClosed()) {
                udpSocket.close();
            }
            System.out.println("Connection closed");
        } catch (IOException e) {
            System.out.println("Error closing client socket: " + e.getMessage());
        }
    }

    public BufferedReader getIn() {
        return in;
    }

    public DatagramSocket getUdpSocket() {
        return udpSocket;
    }

    public int getClientId() {
        return clientId;
    }


    public static void main(String[] args){
        String serverAddress = "localhost";
        int serverPort = 12345;

        try {
            Client client = new Client(serverAddress, serverPort);
            new Thread(new ClientTCPListener(client)).start();
            new Thread(new ClientUDPListener(client.getUdpSocket())).start();
            new Thread(new ConsoleReader(client)).start();
        } catch (IOException e) {
            System.out.println("Error connecting to server: " + e.getMessage());
        }
    }
}
