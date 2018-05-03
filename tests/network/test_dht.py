from vmnet.tests.base import *
import unittest
import time

def run_setter_node():
    from vmnet.protocol.server import Server
    from vmnet.logger import get_logger
    import time, os, asyncio

    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)

    log = get_logger(os.getenv('HOSTNAME'))
    node = Server(block=False)
    future = asyncio.ensure_future(node.set_value('marco', 'pollo'))

    loop.run_forever()


def run_getter_node():
    from vmnet.protocol.server import Server
    from vmnet.logger import get_logger
    import time, os, asyncio

    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)

    log = get_logger(os.getenv('HOSTNAME'))
    node = Server(block=False)
    res = asyncio.ensure_future(node.get_value('marco'))
    log.debug('res={}'.format(res))

    loop.run_forever()

class TestDHT(BaseNetworkTestCase):
    testname = 'test_dht'
    compose_file = 'kademlia-nodes.yml'
    setuptime = 10
    def test_setup_server_clients(self):
        self.execute_python('node_8', run_setter_node, async=True)
        time.sleep(3)
        for node in ['node_{}'.format(n) for n in range(1,8)]:
            self.execute_python(node, run_getter_node, async=True)

if __name__ == '__main__':
    unittest.main()
