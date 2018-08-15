import unittest, asyncio, os, shutil
from vmnet.launch import launch
from vmnet.webserver import start_ui
from vmnet.parser import get_fn_str
from multiprocessing import Process
from os.path import dirname, abspath, join, splitext, expandvars, realpath, exists

class BaseNetworkTestCase(unittest.TestCase):

    @staticmethod
    def _set_configs(klass, config):
        for c in config:
            setattr(klass, c, config[c])

    @classmethod
    def execute_python(cls, node, fn, python_version=3.6, profiling=None, async=True):
        fname = 'tmp_exec_code_{}_{}.py'.format(node, fn.__name__)
        fpath = join(cls.project_path, fname)
        with open(fpath, 'w+') as f:
            f.write(get_fn_str(fn, profiling))
        exc_str = 'docker exec {} /usr/bin/python{} {} {}'.format(
            node, python_version, fname, '&' if async else '')
        os.system(exc_str)

    @classmethod
    def execute_nodejs(cls, node, fname):
        pass

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'webserver_proc'):
            cls.webserver_proc.terminate()
            cls.websocket_proc.terminate()
            launch(cls.config_file, cls.test_name, clean=True)

class BaseTestCase(BaseNetworkTestCase):

    def setUp(self):
        self.test_name = self.__name__
        self._set_configs(launch(self.config_file, self.test_name))

    def set_configs(self, config):
        for c in config:
            setattr(self, c, config[c])

    def tearDown(self):
        launch(self.config_file, self.test_name, clean=True)
