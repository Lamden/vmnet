"""
BaseNetworkTestCase runs the setup and teardown only once. You can run it as
any normal Python unittests:
```bash
$ python -m unittest discover -v
```
"""
import vmnet, unittest, sys, os, dill, shutil, webbrowser, threading, time, json, yaml
from multiprocessing import Process
from os.path import dirname, abspath, join, splitext, expandvars
from vmnet.test.util import *
from coloredlogs.converter import convert
from websocket_server import WebsocketServer

WEBUI_PORT = 4320
WS_PORT = 4321

class BaseNetworkTestCase(unittest.TestCase):
    """
        The base testcase allows servers to run for a specified amount of
        wait-time and log the results into a log file. Test functions inside
        this test case should then parse the log file to verify the results.

        # Attributes

        setuptime (int): The amount of time to allow the network to complete its tasks
        testname (string): Name of the test
        project (string): Name of the project you want to test
        compose_file (string): File path to the compose file
        docker_dir (string): Directory containing all dockerfiles used by your project

        # Example
```python
        from vmnet.tests.base import BaseTestCase
        from vmnet.tests.util import get_path

        class TestVmnetExample(BaseTestCase):
            testname = 'example'
            compose_file = vmnet-svr-cli.yml'

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
    setuptime = 20
    _is_setup = False
    _is_torndown = False
    logdir = '../../logs'
    vmnet_path = dirname(vmnet.__file__) if hasattr(vmnet, '__file__') else vmnet.__path__._path[0]
    local_path = dirname(dirname(dirname(os.getcwd())))
    
    def run_launch(self, params):
        """
            Runs launch.py to start-up or tear-down for network of nodes in the
            specifed Docker network.
        """
        launch_path = '{}/launch.py'.format(self.vmnet_path)
        exc_str = 'python {} --compose_file {} --docker_dir {} --local_path {} {}'.format(
            launch_path,
            'compose_files/{}'.format(self.compose_file),
            'docker_dir',
            self.local_path,
            params
        )
        os.system(exc_str)

    def run_webui(self):
        from sanic import Sanic
        from sanic.response import file

        STATIC_ROOT = join(dirname(dirname(__file__)), 'console/nota')

        app = Sanic(__name__)
        app.static('/', STATIC_ROOT)
        app.static('/favicon.ico', os.path.join('{}/asserts/img/icons/favicon.ico'.format(STATIC_ROOT)))

        @app.route('/')
        async def index(request):
            return await file('{}/index.html'.format(STATIC_ROOT))

        app.run(host="0.0.0.0", port=WEBUI_PORT, debug=False, access_log=False)

    def run_websocket(self, server):
        def new_client(client, svr):
            opened_files = {}
            while True:
                for root, dirs, files in os.walk(os.getenv('CONSOLE_RUNNING')):
                    for f in files:
                        if f.endswith('_color'):
                            if not opened_files.get(f):
                                opened_files[f] = open(join(root, f))
                            log_lines = opened_files[f].readline().strip()
                            if log_lines != '':
                                node = splitext(f)[0].split('_')
                                node_num = node[-1] if node[-1].isdigit() else None
                                node_type = node[:-1] if node[-1].isdigit() else node
                                svr.send_message_to_all(json.dumps({
                                    'node_type': '_'.join(node_type),
                                    'node_num': node_num,
                                    'log_lines': convert(log_lines)
                                }))
                time.sleep(0.01)
        server.set_fn_new_client(new_client)
        server.run_forever()

    def execute_python(self, node, fn, async=False, python_version='3.6'):
        fn_str = dill.dumps(fn, 0)
        exc_str = 'docker exec {} /usr/bin/python{} -c \"import dill; fn = dill.loads({}); fn();\" {}'.format(
            node,
            python_version,
            fn_str,
            '&' if async else ''
        )
        os.system(exc_str)

    def set_node_map(self):
        self.groups = {}
        self.nodemap = {}
        with open('docker-compose.yml', 'r') as f:
            compose_config = yaml.load(f)
            for service in compose_config['services']:
                s = service.split('_')
                if s[-1].isdigit():
                    servicename = '_'.join(s[:-1])
                    if not self.groups.get(servicename):
                        self.groups[servicename] = []
                    self.groups[servicename].append(service)
                    for envvar in compose_config['services'][service]['environment']:
                        if envvar.startswith('HOST_IP'):
                            self.nodemap[service] = envvar.split('=')[-1]

    def setUp(self):
        """
            Brings the network up, sets the log file and wait for the server to
            complete its tasks before letting actual unittests to run.
        """
        if not self._is_setup:
            self.__class__._is_setup = True
            os.environ['TEST_NAME'] = self.testname
            self.logdir = abspath('{}/{}'.format(self.logdir, self.testname))
            os.makedirs(self.logdir, exist_ok=True)
            shutil.rmtree(self.logdir)
            self.run_launch('--clean')
            self.run_launch('--build_only')
            self.run_launch('&')
            self.__class__.webui = Process(target=self.run_webui)
            self.__class__.webui.start()
            print('Running test "{}" and waiting for {}s...'.format(self.testname, self.setuptime))
            time.sleep(self.setuptime)
            self.set_node_map()
            if not os.getenv('CONSOLE_RUNNING'):
                os.environ['CONSOLE_RUNNING'] = self.logdir
                try:
                    self.server = WebsocketServer(WS_PORT, host='0.0.0.0')
                    self.__class__.websocket = Process(target=self.run_websocket, args=(self.server,))
                    self.__class__.websocket.start()
                except:
                    print('Test Console already running!')
                webbrowser.open('http://localhost:{}'.format(WEBUI_PORT), new=2, autoraise=True)
            sys.stdout.flush()

    def tearDown(self):
        if not self._is_torndown:
            self.__class__._is_torndown = True
            self.run_launch('--clean')
            self.__class__.webui.terminate()
            self.__class__.websocket.terminate()
