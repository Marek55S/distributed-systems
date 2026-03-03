import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.nio.ByteBuffer;
import java.util.Arrays;

public class JavaUdpServer3 {

    public static void main(String args[])
    {
        System.out.println("JAVA UDP SERVER");
        DatagramSocket socket = null;
        int portNumber = 9008;

        try{
            socket = new DatagramSocket(portNumber);
            byte[] receiveBuffer = new byte[4];

            while(true) {
                DatagramPacket receivePacket = new DatagramPacket(receiveBuffer, receiveBuffer.length);
                socket.receive(receivePacket);
                int nb = Integer.reverseBytes(ByteBuffer.wrap(receiveBuffer).getInt());
                nb++;
                nb = Integer.reverseBytes(nb);
                byte[] buff = ByteBuffer.allocate(4).putInt(nb).array();

                DatagramPacket sendPacket = new DatagramPacket(buff, buff.length, receivePacket.getAddress(), receivePacket.getPort());
                socket.send(sendPacket);
            }
        }
        catch(Exception e){
            e.printStackTrace();
        }
        finally {
            if (socket != null) {
                socket.close();
            }
        }
    }
}
