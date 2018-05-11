from vmnet.tests.base import *
import unittest

def run_node():
    import time
    time.sleep(10)
    

class TestCilantroConsensus(BaseNetworkTestCase):
    testname = 'pub_sub'
    compose_file = 'cilantro-nodes.yml'
    waittime = 15
    def test_pub_sub(self):
        for i in range(5):
            self.execute_python('node_{}'.format(i), run_node, async=True)

if __name__ == '__main__':
    unittest.main()
