"""
BaseNetworkTestCase runs the setup and teardown only once. You can run it as
any normal Python unittests:
```bash
$ python -m unittest discover -v
```
"""
import vmnet, unittest, sys, os, re, shutil, webbrowser, threading, time, json, yaml, signal, warnings, uuid, inspect, dill
from multiprocessing import Process
from os.path import dirname, abspath, join, splitext, expandvars, realpath, exists
from vmnet.test.util import *
from vmnet.test.logger import *
from coloredlogs.converter import convert
from websocket_server import WebsocketServer
from sanic import Sanic
from sanic.response import file
from functools import wraps

DEFAULT_SETUP_TIME = 20
DEFAULT_TESTNAME = 'vmnet_test'

VPROF_PORT = 4322
WEBUI_PORT = 4320
WS_PORT = 4321

log = get_logger(__name__)

def keyboard_kill_handler(func):
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            log.info('Process is stopped by a keyboard interrupt.')
    return func_wrapper

def ignore_warnings(test_func):
    def do_test(self, *args, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            test_func(self, *args, **kwargs)
    return do_test

def vmnet_test(*args, **kwargs):
    def _vmnet_test(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            self = args[0]
            assert isinstance(self, BaseNetworkTestCase), \
                "@vmnet_test can only be used to decorate BaseNetworkTestCase subclass methods (got self={}, but expected " \
                "a BaseNetworkTestCase subclass instance)".format(self)

            klass = self.__class__
            parent_klass = self.__class__.__bases__[0]  # In Cilantro, this should be MPTestCase

            # Horrible hack to get MPTestCase to work
            if parent_klass is not BaseNetworkTestCase:
                klass = parent_klass

            log.info("Starting docker...")
            klass.start_docker(run_webui=run_webui)

            klass.vmnet_test_active = True
            res = func(*args, **kwargs)
            klass.vmnet_test_active = False
            klass._reset_containers()

            return res

        return wrapper

    if len(args) == 1 and callable(args[0]):
        run_webui = False
        return _vmnet_test(args[0])
    else:
        run_webui = kwargs.get('run_webui', False)
        return _vmnet_test

def profile(*args, **kwargs):
    def decorator(self, fn=None, profiling='cmph'):
        from vprof import runner, stats_server
        import unittest
        testname = unittest.TestCase.id(self)
        node = os.getenv('HOSTNAME','')
        fnname = fn.__name__
        log.debug('Running VProf on {},{},{}'.format(testname, node, fnname))
        run_stats = runner.run_profilers((fn, args, kwargs), profiling)
        profname = '{}.json'.format(join(os.getcwd(),'profiles', testname, node, fnname))
        if not os.path.exists(dirname(profname)):
            os.makedirs(dirname(profname))
        with open(profname, 'w+') as f:
            f.write(json.dumps(run_stats))
        return run_stats
    return decorator

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
                setattr(clsobj, func_name, ignore_warnings(func))

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
    _webui_started = False
    vmnet_test_active = False

    setuptime = DEFAULT_SETUP_TIME
    testname = DEFAULT_TESTNAME
    profiles = []

    @classmethod
    def _run_launch(cls, params):
        """
        Runs launch.py to start-up or tear-down for network of nodes in the
        specifed Docker network.
        """
        assert cls.compose_file is not None, "compose_file file must be set by subclass"
        assert cls.testname is not None, "testname file must be set by subclass"

        test_path = dirname(realpath(sys.argv[0]))
        vmnet_path = dirname(vmnet.__file__) if hasattr(vmnet, '__file__') else vmnet.__path__._path[0]
        local_path = abspath(os.getenv('LOCAL_PATH', '.'))
        compose_path = '{}/compose_files/{}'.format(test_path, cls.compose_file)
        docker_dir_path = '{}/docker_dir'.format(test_path)
        launch_path = '{}/launch.py'.format(vmnet_path)
        if not hasattr(cls, 'docker_dir'): cls.docker_dir = docker_dir_path
        cls.test_path = test_path
        cls.launch_path = launch_path

        exc_str = 'python {} --compose_file {} --docker_dir {} --local_path {} {}'.format(
            launch_path,
            cls.compose_file if exists(cls.compose_file) else compose_path,
            cls.docker_dir if exists(cls.docker_dir) else docker_dir_path,
            cls.local_path if hasattr(cls, 'local_path') else local_path,
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
        def new_client(client, svr):
            opened_files = {}
            while True:
                for root, dirs, files in os.walk(os.getenv('LOCAL_PATH')):
                    for f in files:
                        if f.endswith('_color') and os.getenv('TEST_NAME') in root:
                            if not opened_files.get(f):
                                opened_files[f] = open(join(root, f))
                            log_lines = [convert(l) for l in opened_files[f].readlines()]
                            if log_lines != []:
                                node = splitext(f)[0].split('_')
                                node_num = node[-1] if node[-1].isdigit() else None
                                node_type = node[:-1] if node[-1].isdigit() else node
                                svr.send_message_to_all(json.dumps({
                                    'node_type': '_'.join(node_type),
                                    'node_num': node_num,
                                    'log_lines': log_lines
                                }))
                time.sleep(0.01)
        server.set_fn_new_client(new_client)
        server.run_forever()

    @classmethod
    def _set_node_map(cls):
        groups, nodemap, nodes, ports = {}, {}, [], {}

        docker_compose_path = '{}/docker-compose.yml'.format(dirname(cls.launch_path))

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
                if compose_config['services'][service].get('ports'):
                    service_ports = compose_config['services'][service]['ports']
                    for s in service_ports:
                        cmd = """docker inspect --format='{{(index (index .NetworkSettings.Ports """ + '"{}/tcp"'.format(s) + """) 0).HostPort}}' """ + service
                        if not ports.get(service): ports[service] = {}
                        ports[service][s] = 'localhost:{}'.format(os.popen(cmd).read().strip())

        assert nodes, "Nodes list should not be empty!"
        cls.groups, cls.nodemap, cls.nodes, cls.ports = groups, nodemap, nodes, ports
        cls.profiles = []

    @classmethod
    def get_fn_str(cls, fn, indent=0):
        if not callable(fn): return ''
        cv = inspect.getclosurevars(fn)
        non_locals = dict(cv.nonlocals)
        globals = dict(cv.globals)
        full_fn_str = cls._clear_indents(inspect.getsource(fn))
        fn_str = indent * '    ' + full_fn_str[0] + '\n'
        for m in globals:
            fn_str += (indent+1) * '    ' + '{} = dill.loads({})'.format(m, dill.dumps(globals[m])) + '\n'
        for m in non_locals:
            if not callable(non_locals[m]):
                fn_str += (indent+1) * '    ' + '{} = dill.loads({})'.format(m, dill.dumps(non_locals[m])) + '\n'
        for m in non_locals:
            if callable(non_locals[m]):
                added_fn_str = cls.get_fn_str(non_locals[m], indent+1) + '\n'
                added_fn_str = re.sub(r"def ([\w]+)\(", 'def {}('.format(m), added_fn_str)
                fn_str += added_fn_str
        for l in full_fn_str[1:]:
            fn_str += indent * '    ' + l + '\n'
        return fn_str

    @classmethod
    def _clear_indents(cls, s):
        new_fn_str = ''
        pattern = re.compile('^    ')
        lines = s.split('\n')
        new_lines = []
        for line in lines:
            if not pattern.match(line) and line != '':
                return lines
            new_lines.append(pattern.sub('', line))
        return new_lines

    @classmethod
    def execute_python(cls, node, fn, async=False, python_version=3.6, profiling=None):
        fn_str = cls.get_fn_str(fn, indent=0)
        dill_str = dill.dumps(fn)
        fname = 'tmp_exec_code_{}.py'.format(uuid.uuid4().hex)
        with open(fname, 'w+') as f:
            new_fn_str = """
import dill, os
os.environ["PROFILING"] = "{profiling}"
{fn_str}
{fnname}()
            """.format(fn_str=fn_str, fnname=fn.__name__, profiling=profiling)

            f.write(new_fn_str)

        os.system('docker cp {fname} {node}:/app/{fname}'.format(fname=fname, node=node))
        exc_str = 'docker exec {} /usr/bin/python{} {} {}'.format(
            node,
            python_version,
            fname,
            '&' if async else ''
        )
        os.system(exc_str)

    @classmethod
    def start_docker(cls, run_webui=True):
        assert cls.compose_file, "compose_file class var must be set by subclass"
        assert cls.testname, "testname class var must be set by subclass"
        assert os.getenv('LOCAL_PATH'), "You must set the env variable LOCAL_PATH which contains the project you are testing."

        if cls._docker_started:
            return

        cls._docker_started = True

        os.environ['TEST_NAME'] = cls.testname
        os.environ['TEST_ID'] = str(int(time.time()))

        for root, dirs, files in os.walk(os.getenv('LOCAL_PATH')):
            if os.getenv('TEST_NAME') in root and 'log' in root:
                shutil.rmtree(root)

        cls._run_launch('--clean')
        cls._run_launch('--build_only')
        cls._run_launch('&')

        if run_webui:
            log.debug("Launching web UI")

            cls.webui = Process(target=cls._run_webui)
            cls.webui.start()
            cls._webui_started = True

            cls.server = WebsocketServer(WS_PORT, host='0.0.0.0')
            cls.websocket = Process(target=cls._run_websocket, args=(cls.server,))
            cls.websocket.start()

            webbrowser.open('http://localhost:{}'.format(WEBUI_PORT), new=2, autoraise=True)
            sys.stdout.flush()

        log.info('Running test "{}" and waiting for {}s...'.format(cls.testname, cls.setuptime))
        time.sleep(cls.setuptime)
        # Configure node map properties including the 'groups', 'nodemap', and 'nodes' attributes
        cls._set_node_map()

    @classmethod
    def stop_docker(cls):
        assert cls._docker_started, "stop_docker called but cls._docker_started is not True!"

        log.debug("Cleaning docker containers")
        cls._reset_containers()
        cls._run_launch('--clean')
        cls._docker_started = False

        if cls._webui_started:
            log.debug("Stopping web UI")
            cls.server.server_close()
            cls.webui.terminate()
            cls.websocket.terminate()
            cls._webui_started = False

    @classmethod
    def _reset_containers(cls):
        log.debug("Resetting docker containers (sending 'pkill -f python')")
        if hasattr(cls, 'nodes'):
            for node in cls.nodes:
                log.debug("resetting node {}".format(node))
                os.system('docker exec -d {} pkill -f python'.format(node))

        if len(cls.profiles) > 0:
            for root, dirs, files in os.walk(os.getenv('LOCAL_PATH')):
                for name in files:
                    fpath = join(root, name)
                    for i, p in enumerate(cls.profiles):
                        if fpath.endswith(p+'.json'):
                            file = splitext(fpath)[0]
                            os.system('vprof -i {}.json -p {} &'.format(file, VPROF_PORT+i))
                            os.system('gprof2dot -f pstats {file}.stats | dot -Tpng -o {file}.png'.format(file=file))

        os.system('pkill docker-compose')

    @classmethod
    def setUpClass(cls):
        os.system('find {} -type f -name \'tmp_exec_code_*.py\' -delete'.format(os.getenv('LOCAL_PATH')))

    @classmethod
    def tearDownClass(cls):
        if cls._docker_started:
            cls.stop_docker()
            os.system('find {} -type f -name \'tmp_exec_code_*.py\' -delete'.format(os.getenv('LOCAL_PATH')))
