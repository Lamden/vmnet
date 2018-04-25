"""
    Scans ip addresses for the decentralized dynamic discover procedure
"""

from vmnet.tests.util import *
import socket, struct
import requests
import os
import time
import re

def parse_listeners(content):
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

def discover_peers():
    with open('scan.log', 'w+') as f:
        for d in range(*get_local_range()):
            check_ip(decimal_to_ip(d))
        time.sleep(5)
        p_stats = re.compile('--- ' + ip_address_regex() + ' ping statistics ---')
        for l in f:

            print(l)



def check_ip(ip):
    os.system('ping -t 2 -c 5 -i 0.2 {} >> scan.log &'.format(ip))

def get_local_range():
    try:
        r = requests.get('http://ip.42.pl/raw')
        public_ip = r.text.split('.')
        from_ip = ip_to_decimal('.'.join(public_ip[:3]+['0']))
        to_ip = from_ip + 256
        return from_ip, to_ip
    except:
        raise Exception('Cannot get your public ip!')

def get_region_range():
    pass

def get_popular_range():
    pass

def decimal_to_ip(d):
    return socket.inet_ntoa(struct.pack('!L', d))

def ip_to_decimal(ip):
    return struct.unpack("!L", socket.inet_aton(ip))[0]

if __name__ == '__main__':
    discover_peers()
