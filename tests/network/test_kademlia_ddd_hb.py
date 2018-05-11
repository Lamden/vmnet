from vmnet.tests.base import *
import unittest
import time

def run_lookup_node():
    from kademlia.server import Server
    from kademlia.logger import get_logger
    import time, os, asyncio
    log = get_logger(__name__)
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    node = Server(node_id='vk_{}'.format(os.getenv('HOST_IP')), mode='test', block=False, cmd_cli=False)
    time.sleep(5)
    vk = 'vk_172.29.5.3'
    node = loop.run_until_complete(node.dht.lookup_ip(vk))
    loop.run_forever()

def run_node():
    from kademlia.server import Server
    import time, os, asyncio
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    node = Server(node_id='vk_{}'.format(os.getenv('HOST_IP')), mode='test', block=False, cmd_cli=False)
    loop.run_forever()

class TestDDDHB(BaseNetworkTestCase):
    testname = 'test_ddd_hb'
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
