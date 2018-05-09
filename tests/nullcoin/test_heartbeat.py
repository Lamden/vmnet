from vmnet.tests.base import *
import unittest, time

def run_server():
    from nullcoin.node import Node
    n = Node()
    n.listen()
    n.loop.run_forever()

def run_client():
    from nullcoin.node import Node
    n = Node()
    n.listen()
    n.connect('172.29.5.1')
    n.loop.run_forever()

class TestHeartbeat(BaseNetworkTestCase):
    testname = 'heartbeat'
    compose_file = 'nullcoin-nodes.yml'
    setuptime = 10
    def test_basic_pub_sub(self):
        self.execute_python('node_1', run_server, async=True)
        time.sleep(1)
        self.execute_python('node_2', run_client, async=True)

if __name__ == '__main__':
    unittest.main()
