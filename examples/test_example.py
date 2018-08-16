import unittest
from vmnet.testcase import BaseTestCase

def hello():
    from logger import get_logger
    log = get_logger('hello')
    log.critical('hello')

def world():
    from logger import get_logger
    log = get_logger('world')
    log.important('world')

class TestExample(BaseTestCase):
    config_file = 'vmnet_configs/docknet.json'
    def test_example(self):
        self.execute_python('masternode', hello)
        self.execute_python('delegate_3', world)
        self.execute_python('delegate_4', hello)
        self.execute_python('delegate_5', world)
        input('Hit enter to terminate')

if __name__ == '__main__':
    unittest.main()
