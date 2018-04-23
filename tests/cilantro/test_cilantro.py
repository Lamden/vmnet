from vmnet.tests.base import *
from vmnet.tests.util import *
import unittest

class TestCilantro(BaseTestCase):
    testname = 'cilantro_example'
    project = 'cilantro'
    compose_file = get_path('vmnet/tests/configs/cilantro-compose.yml')
    docker_dir = get_path('vmnet/docker/docker_files/cilantro')
    def test_has_listeners(self):
        pass

if __name__ == '__main__':
    unittest.main()
