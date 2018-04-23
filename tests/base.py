"""
BaseNetworkTestCase runs the setup and teardown only once. You can run it as
any normal Python unittests:
```bash
$ python -m unittest discover -v
```
"""


from vmnet.tests.util import *
import unittest
import os

class BaseNetworkTestCase(unittest.TestCase):
    """
        The base testcase allows servers to run for a specified amount of
        wait-time and log the results into a log file. Test functions inside
        this test case should then parse the log file to verify the results.

        # Arguments

        waittime (int): The amount of time to allow the network to complete its tasks
        testname (string): Name of the test
        project (string): Name of the project you want to test
        compose_file (filepath): File path to the compose file
        docker_dir (directory): Directory containing all dockerfiles used by your project

        # Example
```python
        from vmnet.tests.base import BaseTestCase
        from vmnet.tests.util import get_path

        class TestVmnetExample(BaseTestCase):
            testname = 'vmnet_example'
            project = 'vmnet'
            compose_file = get_path('vmnet/tests/configs/vmnet-compose.yml')
            docker_dir = get_path('vmnet/docker/docker_files/vmnet')

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
```
    """
    waittime = 20
    _is_setup = False
    _is_torndown = False
    def run_script(self, params):
        """
            Runs launch.py to start-up or tear-down for network of nodes in the
            specifed Docker network.
        """
        launch_path = get_path('vmnet/docker/launch.py')
        os.system('python {} --project {} {}'.format(
            launch_path,
            self.project,
            params
        ))

    def setUp(self):
        """
            Brings the network up, sets the log file and wait for the server to
            complete its tasks before letting actual unittests to run.
        """
        if not self._is_setup:
            self.__class__._is_setup = True
            self.logfile = get_path('vmnet/logs/{}.log'.format(self.testname))
            try: os.remove(self.logfile)
            except: pass
            os.environ['TEST_NAME'] = self.testname
            self.run_script('--compose_file {} --docker_dir {} &'.format(
                self.compose_file,
                self.docker_dir
            ))
            print('Running test "{}" and waiting for {}s...'.format(self.testname, self.waittime))
            time.sleep(self.waittime)
            with open(self.logfile) as f:
                self.__class__.content = f.readlines()

    def tearDown(self):
        """
            Stop and remove Docker containers when the log file has been updated.
        """
        if not self._is_torndown:
            self.__class__._is_torndown = True
            self.run_script('--clean')
