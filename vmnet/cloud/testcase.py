import unittest, asyncio, os, shutil
from vmnet.cloud.aws import AWS
from vmnet.parser import get_fn_str, load_test_envvar
from os.path import dirname, abspath, join, splitext, expandvars, realpath, exists
from pprint import pprint

class CloudNetworkTestCase(unittest.TestCase):

    @staticmethod
    def _set_configs(klass, config):
        for c in config:
            setattr(klass, c, config[c])

    @classmethod
    def end_test(cls):
        os.environ['TEST_COMPLETE'] = '1'

    @classmethod
    def execute_python(cls, node, fn, python_version=3.6):
        fname = 'tmp_exec_code_{}_{}_{}.py'.format(node, cls.__name__, fn.__name__)
        fn_str = get_fn_str(fn)
        # cls.api.send_file()
        # cls.api.execute_command()

    @classmethod
    def execute_nodejs(cls, node, fname):
        pass

class AWSTestCase(CloudNetworkTestCase):

    @classmethod
    def setUpClass(cls):
        cls.api = AWS(cls.config_file)
        self.api.up()
        self.group_ips = {}
        self.groups = {}
        self.nodemap = {}
        instance_idx = 1
        for service in self.api.config['services']:
            image = self.api.config['aws']['images'][service['image']]
            instances = self.find_instances(image, image['run_ami'])
            self.groups_ips[service['name']] = []
            self.groups[service['name']] = []
            for instance in instances:
                ip = instance['PublicIpAddress']
                if service["count"] == 1:
                    name = service["name"]
                else:
                    name = '{}_{}'.format(service['name'], instance_idx)
                self.groups_ips[service['name']].append(ip)
                self.groups[service['name']].append(name)
                self.nodemap[name] = ip
                instance_idx += 1
        pprint(self.group_ips)
        pprint(self.groups)
        pprint(self.nodemap)

    def setUp(self):
        self.envvar = {}
        self.test_name, self.test_id = self.id().split('.')[-2:]
        print('#' * 128 + '\n')
        print('    Running {}.{}...\n'.format(test_name, test_id))
        print('#' * 128 + '\n')

    # @classmethod
    # def tearDownClass(cls):
    #     print('Bringing down services...')
    #     cls.api.down()
