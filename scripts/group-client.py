from group_util import *
from group_base import GroupBase
import zmq
import time
import uuid
import json
import random
import os
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
        logger.debug('{}: received {}'.format(os.getenv('HOST_IP'), msg))

if __name__ == '__main__':
    ips = load_ips(os.getenv('VMNET_WITNESS').split(','))
    key = os.getenv('HOST_IP')
    server_ip = os.getenv('VMNET_MASTER')
    gc = GroupClient(ips, server_ip=server_ip)
    gc.regroup()
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
