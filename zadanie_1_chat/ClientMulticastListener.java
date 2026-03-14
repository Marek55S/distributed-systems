import java.io.IOException;
import java.net.*;

public class ClientMulticastListener implements Runnable{
    private final MulticastSocket multicastSocket;
    private final Client client;

    public ClientMulticastListener(Client client,MulticastSocket multicastSocket)  {
        this.client = client;
        this.multicastSocket = multicastSocket;
    }

    @Override
    public void run() {
        byte[] buffer = new byte[1024];
        try{
            while(true){
                DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
                multicastSocket.receive(packet);
                String message = new String(packet.getData(), 0, packet.getLength()).trim();
                if(message.startsWith("MSG:")){
                    String[] parts = message.split(":", 3);
                    int senderId = Integer.parseInt(parts[1]);
                    String messageData = parts[2];
                    if(senderId != this.client.getClientId()){
                        System.out.println("Received multicast message from client " + senderId + ": " + messageData);
                    }
                } else {
                    System.out.println("Received multicast message: " + message);
                }
            }
        } catch(IOException e){
            if (multicastSocket.isClosed()){
                System.out.println("Multicast listener stopped.");
            } else {
                System.out.println("Error in multicast listener: " + e.getMessage());
            }
        } finally {
            try {
                InetAddress group = InetAddress.getByName(multicastSocket.getInetAddress().getHostAddress());
                NetworkInterface networkInterface = NetworkInterface.getByInetAddress(InetAddress.getLocalHost());
                multicastSocket.leaveGroup(new InetSocketAddress(group, multicastSocket.getLocalPort()), networkInterface);
            } catch (IOException e) {
                System.out.println("Error leaving multicast group: " + e.getMessage());
            }
            multicastSocket.close();
        }
    }
}
