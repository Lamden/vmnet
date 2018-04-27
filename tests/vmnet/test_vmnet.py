from vmnet.tests.base import *
from vmnet.tests.util import *
import unittest

def parse_listeners():
    with open('logs/srv_cli.log') as f:
        content = f.readlines()
    listeners = {}
    p_ports = re.compile(r'listening on tcp\:\/\/'+ip_address_regex()+r'\:'+port_regex())
    p_client = re.compile(r'Started listening as '+ip_address_regex())
    for line in content:
        matches = re.findall(p_ports, line)
        for m in matches:
            if not listeners.get(m[1]):
                listeners[m[1]] = 0
            listeners[m[1]] += 1
        matches = re.findall(p_client, line)
        for m in matches:
            listeners[m] = True
    return listeners

def parse_sender_receiver():
    with open('logs/srv_cli.log') as f:
        content = f.readlines()
    senders = []
    receivers = []
    p_sender = re.compile(r'Sending to\.\.\.\ '+ip_address_regex())
    p_receiver = re.compile(ip_address_regex()+r'\: received .* "key": "'+ip_address_regex()+r'"')
    for line in content:
        matches = re.findall(p_sender, line)
        for m in matches:
            senders.append(m)
        matches = re.findall(p_receiver, line)
        for m in matches:
            receivers.append(m)
    return senders, receivers

class TestVmnetExample(BaseNetworkTestCase):
    testname = 'srv_cli'
    compose_file = 'vmnet-svr-cli.yml'
    def test_has_listeners(self):
        listeners = parse_listeners()
        for i in range(0,6):
            self.assertEqual(listeners.get('1000{}'.format(i)), 3)
            if i > 0: self.assertTrue(listeners.get('172.28.5.{}'.format(i)))

    def test_each_can_receive_messages(self):
        senders, receivers = parse_sender_receiver()
        for receiver in receivers:
            self.assertIn(receiver[1], senders)
        self.assertEqual(len(receivers), 3 * len(senders))

if __name__ == '__main__':
    unittest.main()
