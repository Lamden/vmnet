import unittest
from vmnet.cloud.testcase import AWSTestCase

def hello():
    from logger import get_logger
    log = get_logger('hello')
    log.critical('hello')

def world():
    from logger import get_logger
    log = get_logger('world')
    log.important('world')

class TestCloud(AWSTestCase):

    config_file = '../vmnet_configs/cilantro_mn.json'

    def test_cloud(self):
        self.execute_python('masternode', hello)
        self.execute_python('delegate_3', world)
        self.execute_python('delegate_4', hello)
        self.execute_python('delegate_5', world)
        input('Hit enter to terminate')

if __name__ == '__main__':
    unittest.main()
