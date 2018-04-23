from util import *
import unittest
import os

class TestVmnetExample(unittest.TestCase):
    testname = 'vmnet_example'
    waittime = 20
    logfile = 'logs/{}.log'.format(testname)
    project = 'vmnet'
    compose_file = 'tests/vmnet/compose_file.yml'
    network_file = 'tests/vmnet/network_file.yml'
    is_setup = False
    is_torndown = False
    def run_script(self, params):
        os.system('python docker/launch.py --project {} {}'.format(
            self.project,
            params
        ))
        
    def setUp(self):
        if not self.is_setup:
            self.__class__.is_setup = True
            try: os.remove(self.logfile)
            except: pass
            os.environ['TEST_NAME'] = self.testname
            self.run_script('--compose_file {} --network_file {} &'.format(
                self.compose_file,
                self.network_file
            ))
            print('Running test "{}" and waiting for {}s...'.format(self.testname, self.waittime))
            time.sleep(self.waittime)
            with open(self.logfile) as f:
                self.__class__.content = f.readlines()

    def test_has_listeners(self):
        listeners = parse_listeners(self.content)
        for i in range(0,6):
            self.assertEqual(listeners.get('1000{}'.format(i)), 3)
            if i > 0: self.assertTrue(listeners.get('172.28.5.{}'.format(i)))

    def test_each_can_receive_messages(self):
        senders, receivers = parse_sender_receiver(self.content)
        for receiver in receivers:
            self.assertIn(receiver[1], senders)
        self.assertEqual(len(receivers), 3 * len(senders))

    def tearDown(self):
        if not self.is_torndown:
            self.__class__.is_torndown = True
            self.run_script('--clean')


if __name__ == '__main__':
    unittest.main()
