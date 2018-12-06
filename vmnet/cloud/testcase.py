import unittest, asyncio, os, shutil, sys, queue, time
from vmnet.cloud.aws import AWS
from vmnet.parser import get_fn_str, load_test_envvar
from os.path import dirname, abspath, join, splitext, expandvars, realpath, exists
from pprint import pprint
from threading import Thread

class CloudNetworkTestCase(unittest.TestCase):

    print('''
                                          _                 _
                           _             | |               | |
 _   _ ____  ____  _____ _| |_ _____ ____| | ___  _   _  __| |
| | | |    \|  _ \| ___ (_   _|_____) ___) |/ _ \| | | |/ _  |
 \ V /| | | | | | | ____| | |_     ( (___| | |_| | |_| ( (_| |
  \_/ |_|_|_|_| |_|_____)  \__)     \____)\_)___/|____/ \____|

                Brought to you by Lamden.io

    ''')
    keep_up = False
    exec_q = queue.Queue()
    timeout = 30

    @staticmethod
    def _set_configs(klass, config):
        for c in config:
            setattr(klass, c, config[c])

    def setUp(self):
        self.envvar = {}
        CloudNetworkTestCase.test_name, CloudNetworkTestCase.test_id = self.id().split('.')[-2:]
        print('#' * 128 + '\n')
        print('    Running {}.{}...\n'.format(CloudNetworkTestCase.test_name, CloudNetworkTestCase.test_id))
        print('#' * 128 + '\n')

    @classmethod
    def execute_python(cls, node, fn, python_version=3.6):
        def _run():
            try:
                cls.api.send_file(instance_ip, username, fname, fn_str)
                cls.api.execute_command(instance_ip, 'python3 {}'.format(fname), username, immediate_raise=True)
                cls.exec_q.put('done')
            except Exception as e:
                cls.exec_q.put(sys.exc_info())

        fname = 'tmp_exec_code_{}_{}_{}.py'.format(node, cls.__name__, fn.__name__)
        group = node.rsplit('_', 1)
        idx = int(group[1]) if len(group) == 2 else 0
        instance_ip = cls.group_ips[group[0]][idx]
        username = cls.images[node]['username']
        environment = {
            'TEST_NAME': CloudNetworkTestCase.test_name,
            'TEST_ID': CloudNetworkTestCase.test_id,
            'HOST_NAME': node,
            'HOST_IP': instance_ip
        }
        environment.update(cls.environment)
        env_str = 'import os\n'
        env_str += '\n'.join(['os.environ["{}"]="{}"'.format(name, environment[name]) for name in environment])
        fn_str = env_str + get_fn_str(fn)
        t = Thread(target=_run, name=node)
        t.start()

    def tearDown(self):
        print('_' * 128 + '\n')
        print('    Running test for a max of {}s'.format(self.timeout))
        print('_' * 128 + '\n')
        current_time = 0
        while current_time < self.timeout:
            if self._raise_error() == 'done':
                
                return
            current_time += 1
            time.sleep(1)
        raise Exception('{}.{} has timed out after {}s'.format(CloudNetworkTestCase.test_name, CloudNetworkTestCase.test_id, self.timeout))

    @classmethod
    def _raise_error(cls):
        try:
            exc = cls.exec_q.get(block=False)
            return exc
        except queue.Empty:
            pass
        else:
            if not cls.keep_up:
                print('Bringing down services...')
                cls.api.down()
            raise exc[0].with_traceback(exc[1], exc[2])

    @classmethod
    def execute_nodejs(cls, node, fname):
        pass

class AWSTestCase(CloudNetworkTestCase):

    @classmethod
    def setUpClass(cls):
        cls.api = AWS(cls.config_file)
        cls.api.up(cls.keep_up)
        cls.group_ips = {}
        cls.groups = {}
        cls.nodemap = {}
        cls.images = {}
        cls.environment = {}
        instance_idx = 1
        for service in cls.api.config['services']:
            image = cls.api.config['aws']['images'][service['image']]
            instances = cls.api.find_aws_instances(image, image['run_ami'])
            cls.group_ips[service['name']] = []
            cls.groups[service['name']] = []
            for instance in instances:
                ip = instance['PublicIpAddress']
                if service["count"] == 1:
                    name = service["name"]
                else:
                    name = '{}_{}'.format(service['name'], instance_idx)
                cls.group_ips[service['name']].append(ip)
                cls.groups[service['name']].append(name)
                cls.nodemap[name] = ip
                cls.images[name] = image
                instance_idx += 1

        for group in cls.group_ips:
            cls.environment[group.upper()] = ','.join(cls.group_ips[group])

    @classmethod
    def tearDownClass(cls):
        if not cls.keep_up:
            print('Bringing down services...')
            cls.api.down()
