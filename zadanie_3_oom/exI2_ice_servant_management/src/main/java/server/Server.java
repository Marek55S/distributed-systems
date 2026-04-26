package server;

import com.zeroc.Ice.Communicator;
import com.zeroc.Ice.Util;
import com.zeroc.Ice.ObjectAdapter;

public class Server {
    public static void main(String[] args) {
        try (Communicator communicator = Util.initialize(args)) {
            ObjectAdapter adapter = communicator.createObjectAdapterWithEndpoints("MyAdapter", "default -p 10000");

            adapter.addDefaultServant(new SharedServantI(), "shared");

            adapter.addServantLocator(new MyServantLocator(), "dedicated");

            adapter.activate();
            System.out.println("Server listening on port 10000");
            communicator.waitForShutdown();
        }
    }
}