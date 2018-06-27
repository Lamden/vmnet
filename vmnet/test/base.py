"""
BaseNetworkTestCase runs the setup and teardown only once. You can run it as
any normal Python unittests:
```bash
$ python -m unittest discover -v
```
"""
import vmnet, unittest, sys, os, dill, shutil, webbrowser, threading, time, json, yaml, signal
from multiprocessing import Process
from os.path import dirname, abspath, join, splitext, expandvars
from vmnet.test.util import *
from vmnet.test.logger import *
from coloredlogs.converter import convert
from websocket_server import WebsocketServer
from sanic import Sanic
from sanic.response import file
from functools import wraps


DEFAULT_SETUP_TIME = 20

WEBUI_PORT = 4320
WS_PORT = 4321
BASE_LOG_DIR = '../../logs'

log = get_logger(__name__)


def keyboard_kill_handler(func):
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            pass
            # log.critical('Sending kill sigs to test...')
            # for node in BaseNetworkMeta.get_nodes():
            #     log.critical("killing node {}".format(node))
            #     os.system('docker exec {} pkill -f python'.format(
            #         node
            #     ))
    return func_wrapper


def vmnet_test(func):
    """
    Decorator to allow tests to use VMNET. Designed to be used in combination with Cilantro's MPTest framework.
    """
    @wraps(func)
    def _test_func(*args, **kwargs):
        self = args[0]
        assert isinstance(self, BaseNetworkTestCase), \
            "@vmnet_test can only be used to decorate BaseNetworkTestCase subclass methods (got self={}, but expected " \
            "a BaseNetworkTestCase subclass instance)".format(self)

        klass = self.__class__

        log.info("Starting docker...")
        klass.start_docker()
        log.info("Stopping docker...")

        klass.vmnet_test_active = True
        res = func(*args, **kwargs)
        klass.vmnet_test_active = False

        return res

    return _test_func


class BaseNetworkMeta(type):
    TEST_PREFIX = 'test_'

    def __new__(cls, clsname, bases, clsdict):
        clsobj = super().__new__(cls, clsname, bases, clsdict)

        for func_name in vars(clsobj):
            if not callable(getattr(clsobj, func_name)):
                continue

            if func_name.startswith(cls.TEST_PREFIX):
                func = getattr(clsobj, func_name)
                setattr(clsobj, func_name, keyboard_kill_handler(func))

        return clsobj


class BaseNetworkTestCase(unittest.TestCase, metaclass=BaseNetworkMeta):
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
    _docker_started = False
    vmnet_test_active = False

    setuptime = DEFAULT_SETUP_TIME
    testname = 'vmnet_test'

    compose_file = 'cilantro_nodes.yml'

    @classmethod
    def _run_launch(cls, params):
        """
        Runs launch.py to start-up or tear-down for network of nodes in the
        specifed Docker network.
        """
        assert cls.compose_file is not None, "compose_file file must be set by subclass"
        assert cls.testname is not None, "testname file must be set by subclass"

        vmnet_path = dirname(vmnet.__file__) if hasattr(vmnet, '__file__') else vmnet.__path__._path[0]
        local_path = cls.local_path if hasattr(cls, 'local_path') else dirname(dirname(dirname(os.getcwd())))
        compose_path = 'compose_files/{}'.format(cls.compose_file)
        launch_path = '{}/launch.py'.format(vmnet_path)

        exc_str = 'python {} --compose_file {} --docker_dir {} --local_path {} {}'.format(
            launch_path,
            cls.compose_file if not os.path.exists(compose_path) else compose_path,
            cls.docker_dir if hasattr(cls, 'docker_dir') else 'docker_dir`',
            local_path,
            params
        )
        os.system(exc_str)

    @classmethod
    def _run_webui(cls):
        STATIC_ROOT = join(dirname(dirname(__file__)), 'console/nota')

        app = Sanic(__name__)
        app.static('/', STATIC_ROOT)
        app.static('/favicon.ico', os.path.join('{}/asserts/img/icons/favicon.ico'.format(STATIC_ROOT)))

        @app.route('/')
        async def index(request):
            return await file('{}/index.html'.format(STATIC_ROOT))

        app.run(host="0.0.0.0", port=WEBUI_PORT, debug=False, access_log=False)

    @classmethod
    def _run_websocket(cls, server):
        log.critical("Console running: {}".format(os.getenv('CONSOLE_RUNNING')))
        def new_client(client, svr):
            opened_files = {}
            while True:
                for root, dirs, files in os.walk(os.getenv('CONSOLE_RUNNING')):
                    for f in files:
                        if f.endswith('_color'):
                            if not opened_files.get(f):
                                opened_files[f] = open(join(root, f))
                            log_lines = ''.join(opened_files[f].readlines())
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

    @classmethod
    def _set_node_map(cls):
        groups, nodemap, nodes = {}, {}, []

        docker_compose_path = 'docker-compose.yml'

        assert os.path.exists(docker_compose_path), "Expected to find docker-compose.yml file in current directory {}"\
                                                    .format(os.getcwd())

        with open(docker_compose_path, 'r') as f:
            compose_config = yaml.load(f)
            nodes = list(compose_config['services'].keys())
            for service in compose_config['services']:
                s = service.split('_')
                if s[-1].isdigit():
                    servicename = '_'.join(s[:-1])
                    if not groups.get(servicename):
                        groups[servicename] = []
                    groups[servicename].append(service)
                    for envvar in compose_config['services'][service]['environment']:
                        if envvar.startswith('HOST_IP'):
                            nodemap[service] = envvar.split('=')[-1]

        assert nodes, "Nodes list should not be empty!"
        cls.groups, cls.nodemap, cls.nodes = groups, nodemap, nodes

    @classmethod
    def execute_python(cls, node, fn, async=False, python_version='3.6'):
        fn_str = dill.dumps(fn, 0)
        exc_str = 'docker exec {} /usr/bin/python{} -c \"import dill; fn = dill.loads({}); fn();\" {}'.format(
            node,
            python_version,
            fn_str,
            '&' if async else ''
        )
        os.system(exc_str)

    @classmethod
    def start_docker(cls):
        assert cls.compose_file, "compose_file class var must be set by subclass"
        assert cls.testname, "testname class var must be set by subclass"

        if cls._docker_started:
            # log.debug("Docker already started")  # todo remove dat shieettt
            return

        cls._docker_started = True

        os.environ['TEST_NAME'] = cls.testname

        logdir = cls.logdir if hasattr(cls, 'logdir') else abspath('{}/{}'.format(BASE_LOG_DIR, cls.testname))
        os.makedirs(logdir, exist_ok=True)
        shutil.rmtree(logdir)

        cls._run_launch('--clean')
        cls._run_launch('--build_only')
        cls._run_launch('&')

        # Configure node map properties including the 'groups', 'nodemap', and 'nodes' attributes
        cls._set_node_map()

        cls.webui = Process(target=cls._run_webui)
        cls.webui.start()

        log.info('Running test "{}" and waiting for {}s...'.format(cls.testname, cls.setuptime))
        time.sleep(cls.setuptime)

        if not os.getenv('CONSOLE_RUNNING'):
            os.environ['CONSOLE_RUNNING'] = logdir

            try:
                cls.server = WebsocketServer(WS_PORT, host='0.0.0.0')
                cls.websocket = Process(target=cls._run_websocket, args=(cls.server,))
                cls.websocket.start()
            except:
                log.warning('Test Console already running!')

            webbrowser.open('http://localhost:{}'.format(WEBUI_PORT), new=2, autoraise=True)

        sys.stdout.flush()

    @classmethod
    def reset_containers(cls):
        log.critical("Resetting docker containers (sending 'pkill -f python')...")

        for node in cls.nodes:
            log.critical("resetting node {}".format(node))
            os.system('docker exec -d {} pkill -f python &'.format(
                node
            ))

    @classmethod
    def stop_docker(cls):
        assert cls._docker_started, "stop_docker called but cls._docker_started is not True!"

        log.critical("Terminating docker containers")

        cls._run_launch('--clean')
        cls.server.server_close()

        cls.webui.terminate()
        cls.websocket.terminate()

        cls._docker_started = False

    @classmethod
    def tearDownClass(cls):
        if not cls._docker_started:
            return

        cls.reset_containers()
        cls.stop_docker()
