from vmnet.tests.base import *
import unittest

def sample():
    import os
    import time
    from cilantro.logger import get_logger
    log = get_logger('tests')
    log.debug('here is some test on: {}'.format(os.getenv('HOSTNAME')))
    time.sleep(10)

def create_pub():
    pass

def create_sub():
    pass

def send_pub():
    pass


class TestCilantroConsensus(BaseNetworkTestCase):
    testname = 'cilantro_pub_sub'
    project = 'cilantro'
    compose_file = get_path('vmnet/tests/configs/cilantro-pub-sub.yml')
    docker_dir = get_path('vmnet/docker/docker_files/cilantro')
    logdir = get_path('cilantro/logs')
    waittime = 15
    def test_pub_sub(self):
        self.execute_python('node_1', sample, async=True)
        self.execute_python('node_2', sample, async=True)
        self.execute_python('node_3', sample, async=True)
        self.execute_python('node_4', sample, async=True)

if __name__ == '__main__':
    unittest.main()
