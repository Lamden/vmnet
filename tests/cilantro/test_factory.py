from vmnet.tests.base import *
import unittest, time, random

def run_node():
    from cilantro.nodes.factory import NodeFactory
    import os
    ip = os.getenv('HOST_IP')
    s = NodeFactory.run_delegate('vk_{}'.format(ip), 'tcp://{}:31337'.format(ip))

class TestReactorNodes(BaseNetworkTestCase):
    testname = 'reactor_nodes'
    compose_file = 'cilantro-nodes.yml'
    setuptime = 10
    def test_basic_pub_sub(self):
        for i in range(1,9):
            self.execute_python('node_{}'.format(i), run_node, async=True)
        time.sleep(360)

if __name__ == '__main__':
    unittest.main()
