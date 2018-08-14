import unittest, asyncio, os
from vmnet.launch import launch
from vmnet.webserver import start_ui
from vmnet.parser import get_fn_str
from multiprocessing import Process
from os.path import dirname, abspath, join, splitext, expandvars, realpath, exists

class BaseNetworkTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.webserver_proc, cls.websocket_proc = start_ui(cls.test_name, cls.project_path)

    def setUp(self):
        cls = BaseNetworkTestCase
        cls.test_name = cls.__name__
        cls._set_configs(launch(cls.config_file, cls.test_name))

    @classmethod
    def _set_configs(cls, config):
        for c in config:
            setattr(cls, c, config[c])

    @classmethod
    def execute_python(cls, node, fn, python_version=3.6, profiling=None):
        fname = 'tmp_exec_code_{}_{}.py'.format(node, fn.__name__)
        fpath = join(cls.project_path, fname)
        with open(fpath, 'w+') as f:
            f.write(get_fn_str(fn, profiling))
        exc_str = 'docker exec {} /usr/bin/python{} {} &'.format(
            node, python_version, fname)
        os.system(exc_str)

    @classmethod
    def execute_nodejs(cls, node, fname):
        pass

    def tearDown(self):
        cls = BaseNetworkTestCase
        launch(cls.config_file, cls.test_name, clean=True)

    @classmethod
    def tearDownClass(cls):
        cls.webserver_proc.terminate()
        cls.websocket_proc.terminate()
        launch(cls.config_file, cls.test_name, clean=True)