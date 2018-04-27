"""
    Scans ip addresses for the decentralized dynamic discover procedure
"""

from vmnet.logger import get_logger
from vmnet.tests.util import *
from ip import *
from protocol import *
import os
import json
import uuid
import requests
import asyncio
import logging

log = get_logger('ddd', logging.INFO)

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
            for ip in get_region_range(public_ip):
                for d in range(*get_local_range(ip)):
                    ips.append(decimal_to_ip(d))
    log.info('Scanning {}...'.format(mode))
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(scan_all(loop, ips))
    log.info('Done.')
    log.info(results)
    return results

async def scan_all(loop, ips):
    def req(url):
        try:
            r = requests.get(url, timeout=0.01)
            return r.text
        except:
            pass
    results = []
    port = os.getenv('DDD_PORT', 31337)
    futures = [
        loop.run_in_executor(
            None,
            req,
            'http://{}:{}/'.format(ip, port)
        )
        for ip in ips
    ]
    for response in await asyncio.gather(*futures):
        results.append(response)
    return list(filter(lambda r: r != None, results))

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Do da decentralized dynamic discovery dance!')
    parser.add_argument('--discovery_mode', help='local, neighborhood, popular, predictive', required=True)
    args = parser.parse_args()
    discover(args.discovery_mode)
