from .group_util import *
from .group_base import GroupBase
from vmnet.test.logger import get_logger
import zmq
import time
import uuid
import json
import os
log = get_logger(__file__)

class GroupServer(GroupBase):
    def __init__(self, ips, server_ip, mode='rolling_group', *args, **kwargs):
        super(GroupServer, self).__init__(ips, server_ip, *args, **kwargs)
        self.curr_group = 0
        self.mode = mode # 'rolling_group' or 'random_group' or 'random_subgroup' or 'all_target_groups'

    def bind(self):
        self.socks = []
        self.urls = []
        self.ctx = ctx = zmq.Context()
        for idx in self.groups:
            sock = ctx.socket(zmq.PUB)
            port = self.groups[idx]['port']
            self.socks.append(sock)
            sock.bind("tcp://*:{}".format(port))
            self.urls.append("tcp://*:{}".format(port))

    def publish_transaction(self, tx, key):
        assert self.validate_key(key)
        groups = self.nodes[key]['groups']
        # ctx = self.ctx
        if self.mode == 'all_target_groups':
            for idx in groups:
                sock = self.socks[idx]
                url = self.urls[idx]
                msg = json.dumps({'tx':tx, 'group': idx, 'key': key})
                sock.send_string(msg)
                self.send(msg, key, idx)
            return
        else:
            if self.mode == 'rolling_group':
                idx = self.curr_group
                self.curr_group = (self.curr_group + 1) % len(self.groups)
            elif self.mode == 'random_subgroup':
                idx = random.choice(groups)
            elif self.mode == 'random_group':
                idx = random.choice(self.groups)
            new_port = self.renew_port(tx, idx)
            msg = json.dumps({'tx':tx, 'group': idx, 'key': key})

            self.send(msg, key, idx)

    def send(self, msg, key, group_idx):
        sock = self.socks[group_idx]
        url = self.urls[group_idx]
        sock.send_string(msg)
        log.debug('Sending to... {} from {}'.format(key, url))
        log.debug('\t{}'.format(msg))

if __name__ == '__main__':
    ips = load_ips(os.getenv('VMNET_CLIENT').split(','))
    server_ip = os.getenv('VMNET_SERVER')
    gs = GroupServer(ips, server_ip=server_ip)
    gs.regroup()
    gs.bind()
    time.sleep(5)

    while True:
        gs.publish_transaction(
            '{}'.format(uuid.uuid4().hex),
            random.choice(list(gs.nodes.keys()))
        )
        time.sleep(1)
