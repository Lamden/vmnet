import unittest, os
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
    config_file = '../vmnet_configs/docknet.json'

    os.environ['PROJECT_PATH'] = os.path.abspath(os.getcwd())

    def test_example(self):
        self.execute_python('masternode', hello)
        self.execute_python('delegate_4', world)
        self.execute_python('delegate_5', hello)
        self.execute_python('delegate_6', world)
        input('Hit enter to terminate')

if __name__ == '__main__':
    unittest.main()
