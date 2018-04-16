from group_util import *
import asyncio
import errno
import zmq
import socket
logger = get_logger()

class GroupBase:
    def __init__(self, nodes={}, server_ip=None):
        assert server_ip
        self.server_ip = server_ip
        self.nodes = nodes
        self.groups = {}
        self.ports = {}
        self.loop = asyncio.get_event_loop()

    async def recv(self):
        while True:
            await asyncio.sleep(0)
            for sock in self.socks:
                try:
                    msg, url = sock.recvfrom(1024)
                    print(msg, url)
                except socket.error as e:
                    err = e.args[0]
                    if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                        continue

    def renew_port(self, tx, group_idx):
        # new_port = (sum([ord(c) for c in tx]) + self.groups[group_idx]['count']) % 10000 + 10000
        new_port = (sum([ord(c) for c in tx])) % 10000 + 10000
        if hasattr(self, 'groups_map'):
            idx = self.groups_map.index(group_idx)
        else:
            idx = group_idx
        sock = self.socks[idx]
        url = self.urls[idx]
        self.groups[group_idx]['count'] += 1
        return new_port

    def distribute_groups(self, window_size, skip_space):
        keys = list(self.nodes.keys())
        keys = keys[(len(keys) - window_size) + 1:len(keys)] + keys
        zip_list = [keys[i:] for i in range(0, window_size, skip_space) if keys[i:] != []]
        groups_list = list(zip(*zip_list))[:]
        return groups_list

    def regroup(self, window_size=6, skip_space=2):
        groups_list = self.distribute_groups(window_size, skip_space)
        ports = {}
        for idx, group in enumerate(groups_list):
            # port = random_port(ports)
            port = 10000 + int(idx)
            ports[idx] = port
            for key in group:
                self.nodes[key]['groups'].append(idx)
                if not self.groups.get(idx):
                    self.groups[idx] = {'port': port, 'nodes': [], 'count': 0}
                self.groups[idx]['nodes'].append({
                    'key': key,
                    'ip': self.nodes[key]['ip']
                })
        return groups_list

    def validate_key(self, key):
        return True
