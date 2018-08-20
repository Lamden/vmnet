import unittest, asyncio, os, shutil
from vmnet.launch import launch
from vmnet.webserver import start_ui
from vmnet.parser import get_fn_str
from os.path import dirname, abspath, join, splitext, expandvars, realpath, exists

class BaseNetworkTestCase(unittest.TestCase):

    @staticmethod
    def _set_configs(klass, config):
        for c in config:
            setattr(klass, c, config[c])

    @classmethod
    def execute_python(cls, node, fn, python_version=3.6, profiling=None, async=True):
        fname = 'tmp_exec_code_{}_{}_{}.py'.format(node, cls.__name__, fn.__name__)
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
        self._set_configs(BaseTestCase, launch(self.config_file, self.id()))
        if not hasattr(self, '_launched') and not hasattr(self, 'disable_ui'):
            self._launched = True
            log_dir = join(self.project_path, 'logs', self.id())
            try: shutil.rmtree(log_dir)
            except: pass
            os.makedirs(log_dir, exist_ok=True)
            self.webserver_proc, self.websocket_proc = start_ui(self.id(), self.project_path)

    def tearDown(self):
        if hasattr(self, 'webserver_proc'):
            self.webserver_proc.terminate()
            self.websocket_proc.terminate()
        launch(self.config_file, self.test_name, clean=True)
