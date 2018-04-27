"""
    Scans ip addresses for the decentralized dynamic discover procedure
"""

from vmnet.logger import get_logger
from vmnet.ip import *
from vmnet.protocol import *
import os
import json
import uuid
import zmq
import resource

SOCKET_LIMIT = 2500
log = get_logger('ddd')
resource.setrlimit(resource.RLIMIT_NOFILE, (SOCKET_LIMIT, SOCKET_LIMIT))

def discover(mode):
    ips = {}
    if mode == 'test':
        host = os.getenv('HOST_IP', '127.0.0.1')
        ips[host] = [decimal_to_ip(d) for d in range(*get_local_range(host))]
    else:
        public_ip = get_public_ip()
        # public_ip = '105.160.59.0' # Migori, Kenya
        if mode == 'local':
            ips['localhost'] = [decimal_to_ip(d) for d in range(*get_local_range(public_ip))]
        elif mode == 'neighborhood':
            host_ip = os.getenv('HOST_IP', '127.0.0.1')
            ips[host_ip] = [decimal_to_ip(d) for d in range(*get_local_range(host_ip))]
            for ip in get_region_range(public_ip):
                ips[ip] = [decimal_to_ip(d) for d in range(*get_local_range(ip))]
    log.debug('Scanning {}...'.format(mode))
    results = {}
    for host in ips:
        results[host] = scan_all(ips[host])
    log.debug('Done.')
    log.debug(results)
    return results

def scan_all(ips, poll_time=50):
    port = os.getenv('DDD_PORT', 31337)
    sockets = []
    results = []
    ctx = zmq.Context()
    poller = zmq.Poller()
    for ip in ips:
        url = "tcp://{}:{}".format(ip, port)
        sock = ctx.socket(zmq.REQ)
        sock.linger = 0
        sock.connect(url)
        sockets.append({
            'socket': sock,
            'ip':ip
        })
        sock.send(compose_msg(), zmq.NOBLOCK)
        poller.register(sock, zmq.POLLIN)

    evts = dict(poller.poll(poll_time))
    for s in sockets:
        sock = s['socket']
        ip = s['ip']
        if sock in evts:
            try:
                msg = sock.recv_multipart(zmq.NOBLOCK)
                log.debug("Received msg: {}".format(decode_msg(msg)))
                log.debug("Great, {} is online".format(ip))
                results.append(ip)
            except zmq.Again:
                break
    return results

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Do da decentralized dynamic discovery dance!')
    parser.add_argument('--discovery_mode', help='local, neighborhood, popular, predictive', required=True)
    args = parser.parse_args()
    discover(args.discovery_mode)
