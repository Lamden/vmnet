from vmnet.tests.base import *
import unittest
import time

def run_lookup_node():
    from vmnet.protocol.server import Server
    from vmnet.logger import get_logger
    import time, os, asyncio

    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)

    log = get_logger(os.getenv('HOSTNAME'))
    node = Server(block=False)
    time.sleep(5)
    vk = 'vk_172.29.5.3'
    node = loop.run_until_complete(node.dht.lookup_ip(vk))
    log.critical('{} resolves to {}'.format(vk, node))
    loop.run_forever()

def run_node():
    from vmnet.protocol.server import Server
    import os, asyncio
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    node = Server(block=False)
    loop.run_forever()

class TestLookup(BaseNetworkTestCase):
    testname = 'test_lookup'
    compose_file = 'kademlia-nodes.yml'
    setuptime = 10
    def test_setup_server_clients(self):
        self.execute_python('node_8', run_lookup_node, async=True)
        time.sleep(1)
        for node in ['node_{}'.format(n) for n in range(1,4)]:
            self.execute_python(node, run_node, async=True)
        time.sleep(360)

if __name__ == '__main__':
    unittest.main()
