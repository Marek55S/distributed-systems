package server;

import Demo.SimpleObject;
import com.zeroc.Ice.Current;
import java.util.HashMap;
import java.util.Map;

public class SharedServantI implements SimpleObject {
    private final Map<String, String> states = new HashMap<>();

    @Override
    public void setState(String state, Current current) {
        String objectName = current.id.name;
        System.out.println("SharedServant: Calling setState on object: " + objectName + ", new value: " + state);
        states.put(objectName, state);
    }

    @Override
    public String getState(Current current) {
        String objectName = current.id.name;
        String currentState = states.getOrDefault(objectName, "NO_STATE");
        System.out.println("SharedServant: Calling setState on object: " + objectName + ": " + currentState);
        return currentState;
    }
}