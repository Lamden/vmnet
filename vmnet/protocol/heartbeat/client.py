import socket
import sys, time
import asyncio

loop = asyncio.get_event_loop()

port = 6666
# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket.setdefaulttimeout(0.1)

server_address = ('localhost', port)
sock.connect(server_address)

print('connected to {}!'.format(server_address))
loop.run_forever()
