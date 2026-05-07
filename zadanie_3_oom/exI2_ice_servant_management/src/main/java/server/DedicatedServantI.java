package server;

import Demo.SimpleObject;
import com.zeroc.Ice.Current;

public class DedicatedServantI implements SimpleObject {
    private String state = "INITIAL_STATE";

    @Override
    public void setState(String state, Current current) {
        System.out.println("DedicatedServant " + this.hashCode() + ": setState on object: " + current.id.name);
        this.state = state;
    }

    @Override
    public String getState(Current current) {
        System.out.println("DedicatedServant " + this.hashCode() + ": getState on object: " + current.id.name);
        return state;
    }
}