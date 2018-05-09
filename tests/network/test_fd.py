from vmnet.tests.base import *
import unittest
import time

def run_server_node():
    import select, socket, asyncio, time

    loop = asyncio.get_event_loop()
    port = 6666
    socket.setdefaulttimeout(0.1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setblocking(0)
    sock.bind(('0.0.0.0', port))
    sock.listen(64)

    connected = []

    print('server is running...')

    async def server():
        while True:
            try:
                conn, addr = sock.accept()
                connected.append((conn, addr))
                print("Client (%s, %s) connected" % addr)
            except:
                pass
            await asyncio.sleep(0.1)

    async def heartbeat():
        while True:
            print(connected)
            for connection in connected:
                conn, addr = connection
                try:
                    ready_to_read, ready_to_write, in_error = select.select([conn,], [conn,], [], 5)
                    if ready_to_read:
                        print("Client (%s, %s) disconnected" % addr)
                        connected.remove(connection)
                        sock.shutdown(2)    # 0 = done receiving, 1 = done sending, 2 = both
                        sock.close()
                except select.error as e:
                    pass
            await asyncio.sleep(0.1)

    asyncio.ensure_future(server())
    asyncio.ensure_future(heartbeat())
    loop.run_forever()

def run_client_node():
    import socket
    import sys, time
    import asyncio

    loop = asyncio.get_event_loop()

    port = 6666
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket.setdefaulttimeout(0.1)

    server_address = ('172.29.5.8', port)
    sock.connect(server_address)

    print('connected to {}!'.format(server_address))
    loop.run_forever()

class TestFD(BaseNetworkTestCase):
    testname = 'test_fd'
    compose_file = 'kademlia-nodes.yml'
    setuptime = 10
    def test_setup_server_clients(self):
        self.execute_python('node_8', run_server_node, async=True)
        time.sleep(3)
        for node in ['node_{}'.format(n) for n in range(1,4)]:
            self.execute_python(node, run_client_node, async=True)
        time.sleep(10)
        os.system('docker kill node_2')
        time.sleep(360)

if __name__ == '__main__':
    unittest.main()
