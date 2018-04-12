from group_util import *
from group_base import GroupBase
import zmq
import time
import uuid
import json
import random
logger = get_logger()

class GroupClient(GroupBase):
    def connect(self, key):
        groups = self.nodes[key]['groups']
        self.groups_map = groups
        self.ctx = ctx = zmq.Context()
        self.socks = []
        self.urls = []
        for g in groups:
            sock = ctx.socket(zmq.SUB)
            self.socks.append(sock)
            url = "tcp://{}:{}".format(self.server_ip, self.groups[g]['port'])
            sock.connect(url)
            sock.setsockopt_string(zmq.SUBSCRIBE, '')
            logger.debug('listening on {}'.format(url))
            self.urls.append(url)
    def on_recv(self, msg):
        obj = json.loads(msg)
        new_port = self.renew_port(obj['tx'], obj['group'])
        logger.debug(msg)

if __name__ == '__main__':
    ips_list = [
        '10.0.15.21',
        '10.0.15.22',
        '10.0.15.23',
        '10.0.15.24'
    ]
    ips = load_ips(ips_list)
    try: key = get_ip_address('eth1')
    except: key = random.choice(list(ips.keys()))
    server_ip = '10.0.15.20'# if test_ping('10.0.15.20') else 'localhost'
    gc = GroupClient(ips, server_ip=server_ip)
    gc.regroup(2, 1)
    print(gc.nodes)
    gc.connect(key)
    logger.debug('Started listening as {} ...'.format(key))

    while True:
        for sock in gc.socks:
            while True:
                try:
                    msg = sock.recv_string(zmq.DONTWAIT)
                    gc.on_recv(msg)
                except zmq.Again:
                    break
