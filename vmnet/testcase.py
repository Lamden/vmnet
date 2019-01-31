import unittest, asyncio, os, shutil, time
from vmnet.launch import launch, teardown, config_ports, Docker
from vmnet.webserver import start_ui
from vmnet.parser import get_fn_str
from os.path import dirname, abspath, join, splitext, expandvars, realpath, exists

class BaseNetworkTestCase(unittest.TestCase):

    enable_ui = True
    scripts = {}
    environment = {}
    @staticmethod
    def _set_configs(klass, config):
        for c in config:
            setattr(klass, c, config[c])

    @classmethod
    def end_test(cls):
        os.environ['TEST_COMPLETE'] = 'True'

    @classmethod
    def execute_python(cls, node, fn, python_version=3.6, profiling=None, async=True):

        fname = 'tmp_exec_code_{}_{}_{}.py'.format(node, cls.__name__, fn.__name__)
        fpath = join(cls.project_path, fname)
        with open(fpath, 'w+') as f:
            f.write(get_fn_str(fn, profiling))
        if os.getenv('CIRCLECI'):
            os.system('docker cp {} {}:/app/'.format(fpath, node))
        exc_str = 'docker exec {} /usr/bin/python{} {} {}'.format(
            node, python_version, fname, '&' if async else '')
        cls.scripts[node] = exc_str
        os.system(exc_str)

    @classmethod
    def kill_node(cls, node):
        print('Kill node {}...'.format(node))
        os.system('docker-compose kill {}'.format(node))

    @classmethod
    def start_node(cls, node):
        print('Starting node {}...'.format(node))
        os.system('docker-compose start {}'.format(node))

        time.sleep(3)
        print("Configuring ports...")
        config_ports(container_name=node)

        # sorry this is so ratchet lol... --davis
        BaseNetworkTestCase._set_configs(cls, Docker.config)
        BaseNetworkTestCase._set_configs(BaseNetworkTestCase, Docker.config)

    @classmethod
    def restart_node(cls, node, dead_time=0):
        cls.kill_node(node)
        if dead_time > 0:
            print('waiting {}s until starting node...'.format(dead_time))
            time.sleep(dead_time)
        cls.start_node(node)
        print('Rerunning script for {}...'.format(node))
        cls.rerun_node_script(node)

    @classmethod
    def rerun_node_script(cls, node):
        assert cls.scripts.get(node), 'No previous execution found for node "{}"!'.format(node)
        os.system(cls.scripts[node])

    @classmethod
    def execute_nodejs(cls, node, fname):
        pass

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'webserver_proc') and cls.enable_ui:
            cls.webserver_proc.terminate()
            cls.websocket_proc.terminate()
            teardown()
        os.system('rm -f ./tmp_*.py')

class BaseTestCase(BaseNetworkTestCase):

    @classmethod
    def setUpClass(cls):
        print('''
                               _
     _   _ ____  ____  _____ _| |_
    | | | |    \|  _ \| ___ (_   _)
     \ V /| | | | | | | ____| | |_
      \_/ |_|_|_|_| |_|_____)  \__)

      Brought to you by Lamden.io

        ''')

    enable_ui = True
    def setUp(self):
        BaseNetworkTestCase.test_name, BaseNetworkTestCase.test_id = self.id().split('.')[-2:]
        test_name = '{}.{}'.format(BaseNetworkTestCase.test_name, BaseNetworkTestCase.test_id)
        BaseNetworkTestCase._set_configs(BaseTestCase, launch(self.config_file, test_name, environment=self.environment))
        print('#' * 128 + '\n')
        print('    Running {}...\n'.format(test_name))
        print('#' * 128 + '\n')
        self._clear_fsock()
        if not hasattr(self, '_launched'):
            self._launched = True
            log_dir = join(self.project_path, 'logs', test_name)
            try: shutil.rmtree(log_dir)
            except: pass
            os.makedirs(log_dir, exist_ok=True)
            if self.enable_ui:
                self.webserver_proc, self.websocket_proc = start_ui(test_name, self.project_path)

    def _clear_fsock(self):
        fname = os.path.join(self.project_path, 'fsock')
        if os.path.exists(fname):
            os.remove(fname)
        open(fname, 'w+').close()

    def tearDown(self):
        if hasattr(self, 'webserver_proc') and self.enable_ui:
            self.webserver_proc.terminate()
            self.websocket_proc.terminate()
        teardown()
