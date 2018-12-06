import unittest
from vmnet.cloud.testcase import AWSTestCase

def hello():
    from cilantro.logger.base import get_logger
    import os
    log = get_logger('hello')
    log.critical('hello')
    log.critical(os.getenv('HOST_NAME'))

def world():
    from cilantro.logger.base import get_logger
    log = get_logger('world')
    log.important('world')

class TestCloud(AWSTestCase):

    config_file = '../vmnet_configs/cilantro_mn.json'
    keep_up = True
    timeout = 30

    def test_cloud(self):
        self.execute_python('master', hello)
        self.execute_python('delegate', world)

if __name__ == '__main__':
    unittest.main()
