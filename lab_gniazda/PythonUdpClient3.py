import socket

serverIP = "127.0.0.1"
serverPort = 9008

msg3_bytes = (300).to_bytes(4, byteorder='little')

print('PYTHON UDP CLIENT')

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.sendto(msg3_bytes, (serverIP, serverPort))

received_message = client.recv(4)
received_int = int.from_bytes(received_message, byteorder='little')
print("Received integer from server: " + str(received_int))



