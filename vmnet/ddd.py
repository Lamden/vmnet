"""
    Scans ip addresses for the decentralized dynamic discover procedure
"""

from vmnet.logger import get_logger
from vmnet.ip import *
from vmnet.protocol import *
import socket
import os
import json
import uuid
import asyncio

log = get_logger('ddd')

def discover(mode):
    ips = []
    if mode == 'test':
        for d in range(*get_local_range(os.getenv('HOST_IP', '127.0.0.1'))):
            ips.append(decimal_to_ip(d))
    else:
        public_ip = get_public_ip()
        # public_ip = '105.160.59.0' # Migori, Kenya
        if mode == 'local':
            for d in range(*get_local_range(public_ip)):
                ips.append(decimal_to_ip(d))
        elif mode == 'neighborhood':
            for d in range(*get_local_range(os.getenv('HOST_IP', '127.0.0.1'))):
                ips.append(decimal_to_ip(d))
            for ip in get_region_range(public_ip):
                for d in range(*get_local_range(ip)):
                    ips.append(decimal_to_ip(d))
    log.debug('Scanning {}...'.format(mode))
    results = scan_all(ips)
    log.debug('Done.')
    log.debug(results)
    return results

def scan_all(ips):
    port = os.getenv('DDD_PORT', 31337)
    loop = asyncio.get_event_loop()
    group = asyncio.gather(*[scan_one(ip, port) for ip in ips])
    results = loop.run_until_complete(group)
    return list(filter(lambda r: r != None, results))

async def scan_one(host, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.01)
        s.connect((host, port))
        s.sendall(compose_msg())
        data = s.recv(1024)
        log.debug(data)
        s.close()
        return data
    except:
        pass

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Do da decentralized dynamic discovery dance!')
    parser.add_argument('--discovery_mode', help='local, neighborhood, popular, predictive', required=True)
    args = parser.parse_args()
    discover(args.discovery_mode)
