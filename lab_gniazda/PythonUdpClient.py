import socket

serverIP = "127.0.0.1"
serverPort = 9008
msg = "żółta gęś"

msg3_bytes = (300).to_bytes(4, byteorder='little')

print('PYTHON UDP CLIENT')
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.sendto(bytes(msg, 'utf-8'), (serverIP, serverPort))




