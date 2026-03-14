import java.util.Scanner;

public class ConsoleReader implements Runnable{
    private final Client client;
    private final Scanner keyboardScanner;

    public static final String asciiArtMessage = """
            
            
                                  ;\\
                                 _' \\_
                               ,' '  '`.
                              ;,)       \\
                             /          :
                             (_         :
                              `--.       \\
                                 /        `.
                                ;           `.
                               /              `.
                              :                 `.
                              :                   \\
                               \\\\                \\
                                ::                 :
                                || |               |
                                || |`._            ;
                  Y            _;; ; __`._,       (________
              (t^##_          ((__/(_____(______,'______(___) SSt
            """;

    public static final String multicastMessage = """
                       __n__n__
                .------`-\\00/-'
               /  ##  ## (oo)
              / \\## __   ./
                 |//YY \\|/
            snd  |||   |||
            """;

    public ConsoleReader(Client client){
        this.client = client;
        this.keyboardScanner = new Scanner(System.in);
    }

    @Override
    public void run() {
        while (true) {
            String message = keyboardScanner.nextLine();
            if (message.equalsIgnoreCase("exit")) {
                System.out.println("Exiting...");
                client.disconnect();
                break;
            } else if (message.equals("U")) {
                client.sendUDPMessage("MSG:" + client.getClientId() + ":" + asciiArtMessage);
            }else if(message.equals("M")){
                client.sendMulticastMessage("MSG:" + client.getClientId() + ":" + multicastMessage);
            }
            else {
                client.sendMessageTCP(message);
            }
        }
        keyboardScanner.close();
    }
}
