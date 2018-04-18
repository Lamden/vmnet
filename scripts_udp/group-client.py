from group_util import *
from group_base import GroupBase
import socket
import asyncio
import json
import os
logger = get_logger()

class GroupClient(GroupBase):
    def connect(self, key):
        groups = self.nodes[key]['groups']
        self.groups_map = groups
        self.socks = []
        self.urls = []
        for g in groups:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(False)
            sock.settimeout(1.0)
            self.socks.append(sock)
            url = (self.server_ip, self.groups[g]['port'])
            sock.bind((self.server_ip, self.groups[g]['port']))
            logger.debug('subscribing to {}...'.format(url))
            self.urls.append(url)

    def listen(self):
        asyncio.ensure_future(self.recv())
        self.loop.run_forever()

    def on_recv(self, msg):
        obj = json.loads(msg)
        new_port = self.renew_port(obj['tx'], obj['group'])
        logger.debug('{}: received {}'.format(os.getenv('HOST_IP'), msg))

if __name__ == '__main__':
    ips = load_ips(os.getenv('VMNET_WITNESS', '127.0.0.1').split(','))
    server_ip = os.getenv('VMNET_MASTER', '127.0.0.1')
    key = os.getenv('HOST_IP', '127.0.0.1')
    gc = GroupClient(ips, server_ip=server_ip)
    gc.regroup()
    gc.connect(key)
    gc.listen()