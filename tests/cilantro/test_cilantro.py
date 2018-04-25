from vmnet.tests.base import *
import unittest

def send_four_tx():
    from cilantro.testnet_config.tx_builder import send_tx, DAVIS, STU
    send_tx(DAVIS,STU,1)
    send_tx(DAVIS,STU,2)
    send_tx(DAVIS,STU,3)
    send_tx(DAVIS,STU,4)

class TestCilantroConsensus(BaseNetworkTestCase):
    testname = 'cilantro_consensus'
    project = 'cilantro'
    compose_file = get_path('vmnet/tests/configs/cilantro-compose.yml')
    docker_dir = get_path('vmnet/docker/docker_files/cilantro')
    logdir = get_path('cilantro/logs')
    waittime = 15
    def test_in_consensus(self):
        self.execute_python('mgmt', send_four_tx)
        for node in ['delegate_5', 'delegate_6', 'delegate_7']:
            in_consensus = False
            for l in self.content[node]:
                if 'Delegate in consensus!' in l:
                    in_consensus = True
                    break
            self.assertTrue(in_consensus, '{} failed: Delegates are not in consensus'.format(node))

if __name__ == '__main__':
    unittest.main()
