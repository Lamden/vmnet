from group_util import *
from group_base import GroupBase
import socket
import asyncio
import uuid
import json
import random
import os
logger = get_logger()

class GroupServer(GroupBase):
    def __init__(self, ips, server_ip, mode='rolling_group', *args, **kwargs):
        super(GroupServer, self).__init__(ips, server_ip, *args, **kwargs)
        self.curr_group = 0
        self.mode = mode # 'rolling_group' or 'random_group' or 'random_subgroup' or 'all_target_groups'

    def bind(self):
        self.socks = []
        self.urls = []
        for idx in self.groups:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(False)
            port = self.groups[idx]['port']
            self.socks.append(sock)
            sock.bind(('', port))
            url = (self.server_ip, port)
            logger.debug('listening on {}...'.format(url))
            self.urls.append(url)

    async def send_fakes(self):
        while True:
            await asyncio.sleep(1)
            self.publish_transaction('{}'.format(uuid.uuid4().hex),
                                     random.choice(list(self.nodes.keys())))

    def listen(self):
        asyncio.ensure_future(self.recv())
        asyncio.ensure_future(self.send_fakes())
        self.loop.run_forever()

    def publish_transaction(self, tx, key):
        assert self.validate_key(key)
        groups = self.nodes[key]['groups']
        if self.mode == 'all_target_groups':
            for idx in groups:
                sock = self.socks[idx]
                url = self.urls[idx]
                msg = json.dumps({'tx':tx, 'group': idx, 'key': key})
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
        sock.sendto(msg.encode(), url)
        logger.debug('Sending to... {} from {}'.format(key, url))
        logger.debug('\t{}'.format(msg))

if __name__ == '__main__':
    ips = load_ips(os.getenv('VMNET_WITNESS', '127.0.0.1').split(','))
    server_ip = os.getenv('VMNET_MASTER', '127.0.0.1')
    gs = GroupServer(ips, server_ip=server_ip)
    gs.regroup()
    gs.bind()
    gs.listen()
    gs.loop.run_until_complete(send_fake_transactions(gs))


