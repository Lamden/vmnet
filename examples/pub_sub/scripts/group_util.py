import random
import socket
import fcntl
import struct
import uuid
import logging
import sys
import os

def random_ip():
    return socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xffffffff)))

def random_port(ports):
    port = None
    while port in set(ports.values()) or not port:
        port = random.randint(10000, 20000)
        pass
    return port

def generate_ips(count=20):
    return {uuid.uuid4().hex: {
        'ip': random_ip(),
        'groups': []
    } for i in range(count)}

def load_ips(ips):
    return {ip: {
        'ip': ip,
        'groups': []
    } for ip in ips}

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', bytes(ifname[:15], 'utf-8'))
    )[20:24])

def test_ping(hostname):
    return True if os.system("ping -c 1 -W 0.1 " + hostname) is 0 else False

def get_logger(name=''):
    filedir = "logs/{}".format(os.getenv('TEST_NAME', 'test'))
    filename = "{}/{}.log".format(filedir, name)
    os.makedirs(filedir, exist_ok=True)
    filehandlers = [
        logging.FileHandler(filename),
        logging.StreamHandler()
    ]
    logging.basicConfig(
        format="%(asctime)s [%(levelname)-5.5s] %(message)s",
        handlers=filehandlers,
        level=logging.DEBUG
    )
    return logging.getLogger(name)
