import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;

public class ClientUDPListener implements Runnable{
    private final DatagramSocket udpSocket;

    public ClientUDPListener(DatagramSocket udpSocket){
        this.udpSocket = udpSocket;
    }

    @Override
    public void run() {
        byte[] buffer = new byte[1024];
        try{
            while(true){
                DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
                udpSocket.receive(packet);
                String message = new String(packet.getData(),0,packet.getLength());
                System.out.println("Received UDP message: " + message);
            }
        } catch (IOException e){
            if (udpSocket.isClosed()){
                System.out.println("UDP listener stopped.");
            } else {
                System.out.println("Error in UDP listener: " + e.getMessage());
            }
        }
    }

}
