"""
BaseNetworkTestCase runs the setup and teardown only once. You can run it as
any normal Python unittests:
```bash
$ python -m unittest discover -v
```
"""

from vmnet.tests.util import *
import unittest
import sys
import os
import dill
import shutil

class BaseNetworkTestCase(unittest.TestCase):
    """
        The base testcase allows servers to run for a specified amount of
        wait-time and log the results into a log file. Test functions inside
        this test case should then parse the log file to verify the results.

        # Attributes

        waittime (int): The amount of time to allow the network to complete its tasks
        testname (string): Name of the test
        project (string): Name of the project you want to test
        compose_file (string): File path to the compose file
        docker_dir (string): Directory containing all dockerfiles used by your project

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

    def execute_python(self, node, fn, async=True, python_version='3.6'):
        fn_str = dill.dumps(fn, 0)
        exc_str = 'docker exec {} /usr/bin/python{} -c \"import dill; fn = dill.loads({}); fn();\" {}'.format(
            node,
            python_version,
            fn_str,
            '&' if async else ''
        )
        os.system(exc_str)
        self.collect_log()

    def setUp(self):
        """
            Brings the network up, sets the log file and wait for the server to
            complete its tasks before letting actual unittests to run.
        """
        if not self._is_setup:
            self.__class__._is_setup = True
            self.testdir = '{}/{}'.format(self.logdir, self.testname)
            try: shutil.rmtree(self.testdir)
            except: pass
            os.environ['TEST_NAME'] = self.testname
            self.run_script('--clean')
            self.run_script('--compose_file {} --docker_dir {} &'.format(
                self.compose_file,
                self.docker_dir
            ))
            print('Running test "{}" and waiting for {}s...'.format(self.testname, self.waittime))
            time.sleep(self.waittime)
            sys.stdout.flush()

    def collect_log(self):
        for root, dirs, files in os.walk(self.testdir):
            self.__class__.content = {}
            for file in files:
                with open(os.path.join(root, file)) as f:
                    self.__class__.content[os.path.splitext(file)[0]] = f.readlines()
