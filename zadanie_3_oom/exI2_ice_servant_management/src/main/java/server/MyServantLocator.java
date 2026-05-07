package server;

import com.zeroc.Ice.Current;
import com.zeroc.Ice.Object;
import com.zeroc.Ice.ServantLocator;
import com.zeroc.Ice.UserException;

public class MyServantLocator implements ServantLocator {

    @Override
    public LocateResult locate(Current current) throws UserException {
        System.out.println("\nLOCATOR: Instantiating new servant for: " + current.id.category + "/" + current.id.name);

        Object servant = new DedicatedServantI();

       current.adapter.add(servant, current.id);

        return new LocateResult(servant, null);
    }

    @Override
    public void deactivate(String category) {
        System.out.println("LOKALIZATOR: Deactivating category: " + category);
    }

    @Override
    public void finished(Current current, Object servant, java.lang.Object cookie) throws UserException {
    }
}