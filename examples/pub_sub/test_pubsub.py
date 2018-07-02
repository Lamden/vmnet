from vmnet.test.base import *
from vmnet.test.util import *
import unittest, time

def run_server():
    from vmnet.test.logger import get_logger
    from .scripts.group_util import load_ips
    import os, time, uuid, random
    log = get_logger(os.getenv('HOSTNAME'))
    from .scripts.group_server import GroupServer

    ips = load_ips(os.getenv('VMNET_CLIENT').split(','))
    server_ip = os.getenv('VMNET_SERVER')
    gs = GroupServer(ips, server_ip=server_ip)
    gs.regroup()
    gs.bind()
    time.sleep(3)

    while True:
        gs.publish_transaction(
            '{}'.format(uuid.uuid4().hex),
            random.choice(list(gs.nodes.keys()))
        )
        time.sleep(1)

def run_client():
    from vmnet.test.logger import get_logger
    from .scripts.group_util import load_ips
    import os, zmq
    log = get_logger(os.getenv('HOSTNAME'))
    from .scripts.group_client import GroupClient

    ips = load_ips(os.getenv('VMNET_CLIENT').split(','))
    key = os.getenv('HOST_IP')
    server_ip = os.getenv('VMNET_SERVER')
    gc = GroupClient(ips, server_ip=server_ip)
    gc.regroup()
    gc.connect(key)
    log.debug('Started listening as <{}> ...'.format(key))

    while True:
        for sock in gc.socks:
            while True:
                try:
                    msg = sock.recv_string(zmq.DONTWAIT)
                    gc.on_recv(msg)
                except zmq.Again:
                    break

class TestVmnetExample(BaseNetworkTestCase):
    testname = 'srv_cli'
    compose_file = 'vmnet-svr-cli.yml'
    setuptime = 10
    logdir = 'scripts/logs'
    def test_run_service(self):
        self.execute_python('vmnet_server', run_server, async=True)
        for node_name in self.groups['vmnet_client']:
            self.execute_python(node_name, run_client, async=True)
        time.sleep(10)

if __name__ == '__main__':
    unittest.main()
