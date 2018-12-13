import unittest, asyncio, os, shutil, sys, time, logging
from vmnet.cloud.aws import AWS
from vmnet.parser import get_fn_str, load_test_envvar
from os.path import dirname, abspath, join, splitext, expandvars, realpath, exists
from pprint import pprint
from threading import Thread
from vmnet.cloud.cloud import Cloud

class CloudNetworkTestCase(unittest.TestCase):

    keep_up = False
    timeout = 30
    all_nodes_ready = False

    @staticmethod
    def _set_configs(klass, config):
        for c in config:
            setattr(klass, c, config[c])

    def setUp(self):
        self.envvar = {}
        CloudNetworkTestCase.all_nodes = set()
        CloudNetworkTestCase.all_loaded_nodes = set()
        CloudNetworkTestCase.test_name, CloudNetworkTestCase.test_id = self.id().split('.')[-2:]
        print('#' * 128 + '\n')
        print('    Running {}.{}...\n'.format(CloudNetworkTestCase.test_name, CloudNetworkTestCase.test_id))
        print('#' * 128 + '\n')

    @classmethod
    def execute_python(cls, node, fn, python_version=3.6, no_kill=False):
        def _run():
            try:
                CloudNetworkTestCase.all_nodes.add(node)
                cls.api.send_file(instance_ip, username, fname, fn_str)
                while len(CloudNetworkTestCase.all_loaded_nodes) < len(CloudNetworkTestCase.all_nodes):
                    CloudNetworkTestCase.all_loaded_nodes.add(node)
                    time.sleep(1)
                CloudNetworkTestCase.all_nodes_ready = True
                if not no_kill:
                    cls.api.execute_command(instance_ip, 'pkill python{}'.format(python_version), username, immediate_raise=True)
                cls.api.execute_command(instance_ip, 'python{} {}'.format(python_version, fname), username, environment=environment, immediate_raise=True)
                Cloud.q.put(node)
            except Exception as e:
                Cloud.q.put(sys.exc_info())

        fname = 'tmp_exec_code_{}_{}_{}.py'.format(node, cls.__name__, fn.__name__)
        group = node.rsplit('_', 1)
        idx = cls.groups[group[0]].index(node)
        instance_ip = cls.group_ips[group[0]][idx]
        username = cls.images[node]['username']
        environment = load_test_envvar(
            test_name=CloudNetworkTestCase.test_name,
            test_id=CloudNetworkTestCase.test_id,
            host_name=node,
            host_ip=instance_ip,
            to_dict=True
        )
        environment.update(cls.environment)
        env_str = 'import os\n'
        env_str += '\n'.join(['os.environ["{}"]="{}"'.format(name, environment[name]) for name in environment])
        fn_str = env_str + get_fn_str(fn)
        t = Thread(target=_run, name=node)
        t.start()

    def tearDown(self):
        while not CloudNetworkTestCase.all_nodes_ready:
            time.sleep(1)
        print('_' * 128 + '\n')
        print('    Running test for a max of {}s'.format(self.timeout))
        print('_' * 128 + '\n')
        current_time = 0
        while current_time < self.timeout:
            exc = Cloud._raise_error(self.api)
            if exc != None:
                if type(exc) == str:
                    CloudNetworkTestCase.all_nodes.remove(exc)
                else:
                    raise exc[0].with_traceback(exc[1], exc[2])
            if len(CloudNetworkTestCase.all_nodes) == 0: return
            current_time += 1
            time.sleep(1)
        raise Exception('{}.{} has timed out after {}s'.format(CloudNetworkTestCase.test_name, CloudNetworkTestCase.test_id, self.timeout))

    @classmethod
    def execute_nodejs(cls, node, fname):
        pass

class AWSTestCase(CloudNetworkTestCase):

    @classmethod
    def setUpClass(cls):
        print('''
                                              _                 _
                               _             | |               | |
     _   _ ____  ____  _____ _| |_ _____ ____| | ___  _   _  __| |
    | | | |    \|  _ \| ___ (_   _|_____) ___) |/ _ \| | | |/ _  |
     \ V /| | | | | | | ____| | |_     ( (___| | |_| | |_| ( (_| |
      \_/ |_|_|_|_| |_|_____)  \__)     \____)\_)___/|____/ \____|

                    Brought to you by Lamden.io

        ''')
        cls.api = AWS(cls.config_file)
        cls.api.up(cls.keep_up)
        cls.group_ips = {}
        cls.groups = {}
        cls.nodemap = {}
        cls.images = {}
        cls.environment = {'VMNET_CLOUD': 'True'}
        for service in cls.api.config['services']:
            image = cls.api.config['aws']['images'][service['image']]
            instances = cls.api.find_aws_instances(image, image['run_ami'], additional_filters=[{
                'Name': 'tag:Name',
                'Values': ['{}:{}:{}-run'.format(image['repo_name'], image['branch'], service['name'])]
            }])
            cls.group_ips[service['name']] = []
            cls.groups[service['name']] = []
            for instance in instances:
                ip = instance['PublicIpAddress']
                if service["count"] == 1:
                    name = service["name"]
                else:
                    name = '{}_{}'.format(service['name'], instance['AmiLaunchIndex'])
                cls.group_ips[service['name']].append(ip)
                cls.groups[service['name']].append(name)
                cls.nodemap[name] = ip
                cls.images[name] = image

        for group in cls.group_ips:
            cls.environment[group.upper()] = ','.join(cls.group_ips[group])

    @classmethod
    def tearDownClass(cls):
        if not cls.keep_up:
            print('Bringing down services...')
            cls.api.down()
