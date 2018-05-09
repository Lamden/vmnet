from vmnet.tests.base import *
from cilantro.nodes.factory import NodeFactory
import unittest, time

def run_master():
    from cilantro.nodes.factory import NodeFactory
    n = NodeFactory.create_masternode()
    n.start()

def run_witness():
    from cilantro.nodes.factory import NodeFactory
    n = NodeFactory.create_witnessnode()
    n.start()

def run_delegate():
    from cilantro.nodes.factory import NodeFactory
    n = NodeFactory.create_delegatenode()
    n.start()

class TestMWDNodes(BaseNetworkTestCase):
    testname = 'mwd_nodes'
    compose_file = 'cilantro-nodes.yml'
    waittime = 10
    def test_mwd(self):
        # self.execute_python('node_1', run_pub, async=True)
        # for i in range(2,9):
        #     self.execute_python('node_{}'.format(i), run_sub, async=True)
        time.sleep(15)

if __name__ == '__main__':
    unittest.main()
