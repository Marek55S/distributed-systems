import sys
import Ice

Ice.loadSlice(['-I.', 'SimpleObject.ice'])
import Demo

def main():
    with Ice.initialize(sys.argv) as communicator:
        while True:
            print("\n Ice Client Menu: ")
            print("1. Shared Servant")
            print("2. Dedicated Servant")
            print("q. Quit")
            
            cat_choice = input("choose object type (1 or 2): ")
            
            if cat_choice.lower() == 'q':
                break
                
            category = ""
            if cat_choice == '1':
                category = "shared"
            elif cat_choice == '2':
                category = "dedicated"
            else:
                print("Invalid choice. Please try again.")
                continue
                
            obj_name = input(f"Enter name for the {category} object: ")

            identity_str = f"{category}/{obj_name}"
            proxy_string = f"{identity_str}:default -p 10000"
            
            base_proxy = communicator.stringToProxy(proxy_string)
            
            if not base_proxy:
                print("Error creating proxy.")
                continue

            obj = Demo.SimpleObjectPrx.uncheckedCast(base_proxy)
            
            print("\nWhat would you like to do with the object", identity_str, "?")
            action = input("(1) getState (Read), (2) setState (Write): ")
            
            try:
                if action == '1':
                    print(f"State from server {identity_str}:", obj.getState())
                elif action == '2':
                    new_state = input("Enter new state: ")
                    obj.setState(new_state)
                    print(f"State for {identity_str} has been successfully set.")
                else:
                    print("Unknown action.")
            except Ice.Exception as ex:
                print("An Ice error occurred:", ex)

if __name__ == '__main__':
    main()