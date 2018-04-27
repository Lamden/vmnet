from vmnet.tests.base import *
import unittest
import time

def run_discoverer():
    from vmnet.logger import get_logger
    from vmnet.ddd_zmq import discover
    log = get_logger('ddd')
    discover('test')

def run_listeners():
    from vmnet.logger import get_logger
    from vmnet.heartbeat_zmq import listen
    import os
    log = get_logger('heartbeat')
    listen(os.getenv('DDD_PORT', 31337))

class TestDDD(BaseNetworkTestCase):
    testname = 'test_ddd'
    compose_file = 'kademlia-nodes.yml'
    waittime = 15
    def test_setup_server_clients(self):
        for node in ['node_{}'.format(n) for n in range(1,5)]:
            self.execute_python(node, run_listeners, async=True)
        time.sleep(1) # allow the listeners to start
        self.execute_python('node_7', run_discoverer, async=True)

if __name__ == '__main__':
    unittest.main()
