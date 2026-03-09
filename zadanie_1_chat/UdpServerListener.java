import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.util.Arrays;


public class UdpServerListener implements Runnable{
    private final Server server;
    private final DatagramSocket udpSocket;



    // when the connection is secured, client should send its clientId to the server
    public UdpServerListener(Server server, int portNumber) throws IOException {
        this.server = server;
        this.udpSocket = new DatagramSocket(portNumber);
    }

    @Override
    public void run() {
        byte[] receiveBuffer = new byte[1024];

        try{
            while(true){
                Arrays.fill(receiveBuffer, (byte) 0);
                DatagramPacket receivePacket = new DatagramPacket(receiveBuffer, receiveBuffer.length);

                udpSocket.receive(receivePacket);

                String message = new String(receivePacket.getData(), 0, receivePacket.getLength()).trim();

                if (message.startsWith("INIT:")) {
                    int clientId = Integer.parseInt(message.split(":")[1]);

                    server.registerClientUdp(clientId, receivePacket.getAddress(), receivePacket.getPort());
                    System.out.println("Registered UDP for client " + clientId + " at " + receivePacket.getAddress() + ":" + receivePacket.getPort());
                } else if (message.startsWith("MSG:")){
                    String[] parts = message.split(":", 3);
                    int serverId = Integer.parseInt(parts[1]);
                    String messageData = parts[2];

                    server.broadcastUDPMessage(messageData, serverId, udpSocket);
                }
            }
        } catch (Exception e) {
            System.out.println("Error in UDP listener: " + e.getMessage());
        } finally {
            if (!udpSocket.isClosed()) {
                udpSocket.close();
            }
        }
    }
}
