import uuid
import copy
import time
import warnings

class RollingRelayTree:
    def __init__(self, key, value, space=10, rep_factor=2, send_ahead=1):
        self.ht = {}
        self.trees = []
        self.key = key
        self.value = value
        self.index = -1
        self.in_network = False
        self.space = space
        self.rep_factor = rep_factor
        self.send_ahead = send_ahead
        self.timestamp = None

    def __repr__(self):
        return '<RollingRelayTree: k={}, v={}>'.format(self.key, self.value)

    def set_hash(self, int_key, value):
        h = int_key % self.space
        if not self.ht.get(h): self.ht[h] = {}
        self.ht[h][int_key] = value

    def get_hash(self, int_key):
        h = int_key % self.space
        return self.ht[h][int_key]

    def remove_hash(self, int_key):
        h = int_key % self.space
        del self.ht[h][int_key]
        if not self.ht[h]: del self.ht[h]

    def start_tree(self, ht=None, trees=None):
        self.in_network = True
        if trees and ht:
            self.index = len(trees)
            self.trees = trees
            self.ht = ht
        else:
            self.index = 0
        self.add_to_tree(self.key, self.value)

    def end_tree(self):
        self.in_network = False

    def add_to_tree(self, key, value):
        index = len(self.trees)
        self.set_hash(key, (index, value)) #DEBUG use vk as key and ip as value
        self.trees.append(key)

    def remove_from_tree(self, key):
        remove_idx, value = self.get_hash(key)
        self.remove_hash(key)
        self.trees.pop(remove_idx)

    def get_relay_list(self):
        return {self.trees[idx]: self.get_hash(self.trees[idx])[1] for idx in self.get_relay_indexes(self.index, self.send_ahead) if idx != self.index}

    def get_relay_indexes(self, index, send_ahead):
        relay_list = [((index * self.rep_factor) + (i+1)) % len(self.trees) for i in range(self.rep_factor)]
        if send_ahead > 0:
            tmp_list = []
            for idx in relay_list:
                tmp_list += self.get_relay_indexes(idx, send_ahead-1)
            relay_list += tmp_list
        return set(relay_list)

if __name__ == '__main__':
    ips = [(ip[0], ip[1]) for ip in [
        (1, '127.0.0.1'),
        (2, '127.0.0.2'),
        (3, '127.0.0.3'),
        (4, '127.0.0.4'),

        (11, '127.0.1.1'),
        (12, '127.0.1.2'),
        (15, '127.0.1.5'),
        (17, '127.0.1.7')
    ]]


    #####################
    # Test nested hashes
    #####################

    # rt = RollingRelayTree(1, '127.0.0.1')
    # for ip in ips:
    #     rt.set_hash(*ip)
    # for k in rt.ht:
    #     print(rt.ht[k])
    # print(rt.get_hash(12))

    #####################
    # Test relay tree
    #####################

    # This is addressable by vk in real life
    trees = {rt.key:rt for rt in [
        RollingRelayTree(1, '127.0.0.1'),
        RollingRelayTree(2, '127.0.0.2'),
        RollingRelayTree(3, '127.0.0.3'),
        RollingRelayTree(4, '127.0.0.4'),
        RollingRelayTree(11, '127.0.1.1'),
        RollingRelayTree(12, '127.0.1.2'),
        RollingRelayTree(15, '127.0.1.5'),
        RollingRelayTree(17, '127.0.1.7')
    ]}

    # Test add and remove trees
    # trees[1].start_tree()
    # trees[1].add_to_tree(trees[2].key, trees[2].value)
    # trees[1].add_to_tree(trees[3].key, trees[3].value)
    # trees[1].add_to_tree(trees[4].key, trees[4].value)
    # trees[1].remove_from_tree(trees[3].key)
    # print(trees[1].trees)
    # for i in trees[1].ht:
    #     print(trees[1].ht[i])

    # Test get relay list
    # trees[1].start_tree()
    # trees[1].add_to_tree(trees[2].key, trees[2].value)
    # trees[1].add_to_tree(trees[3].key, trees[3].value)
    # trees[1].add_to_tree(trees[4].key, trees[4].value)
    # trees[1].add_to_tree(trees[11].key, trees[11].value)
    # trees[1].add_to_tree(trees[12].key, trees[12].value)
    # trees[1].add_to_tree(trees[15].key, trees[15].value)
    # trees[1].add_to_tree(trees[17].key, trees[17].value)
    # print(trees[1].get_relay_list())

    # Test adding new trees

    def add_tree_to_network(tree_key, any_key, timestamp=None):
        if trees[any_key].in_network:
            if not timestamp: timestamp = time.time()
            if trees[any_key].timestamp == timestamp:
                # warnings.warn('Tree with key {} is already updated.'.format(any_key))
                return
            # starting the new tree using the bootstrapping node (any tree in the network is fine)
            trees[tree_key].start_tree(copy.deepcopy(trees[any_key].ht), trees[any_key].trees[:])
            # input('next...')
            # print(any_key, '<-', tree_key)
            # print(trees[any_key].get_relay_list())

            for k, v in trees[any_key].get_relay_list().items():
                # remote call to the network of trees
                trees[k].timestamp = timestamp
                trees[k].add_to_tree(trees[tree_key].key, trees[tree_key].value)
                add_tree_to_network(tree_key, k, timestamp)
            # direct call for the added tree
            trees[any_key].add_to_tree(trees[tree_key].key, trees[tree_key].value)
        else:
            warnings.warn('Tree with key {} is not in any network.'.format(any_key))

    trees[1].start_tree()
    # getting the routing table to the new tree from tree1
    add_tree_to_network(12, 1)
    add_tree_to_network(4, 12)
    add_tree_to_network(17, 12)
    add_tree_to_network(3, 1)
    add_tree_to_network(2, 17)


    print(trees[1].trees)
    print(trees[2].trees)
    print(trees[3].trees)
    print(trees[4].trees)
    print(trees[12].trees)
    print(trees[17].trees)
    #
    # print(trees[1].get_relay_list())
    # print(trees[2].get_relay_list())
    # print(trees[3].get_relay_list())
    # print(trees[4].get_relay_list())
    # print(trees[12].get_relay_list())
    # print(trees[17].get_relay_list())

    # Removing existing trees
    # trees[4].remove_from_tree(trees[12].key)
    # print(trees[1].trees)
    # print(trees[4].trees)
    # print(trees[12].trees)
