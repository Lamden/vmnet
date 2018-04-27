"""
    Scans ip addresses for the decentralized dynamic discover procedure
"""

from vmnet.tests.util import *
import socket, struct
import requests
import os
import time
import re
import csv
import numpy as np

WORLD_IP_FILE = 'data/IP2LOCATION-LITE-DB5.csv'
NEIGHBOR_IP_FILE = 'data/neighborhood.txt'

def compile_ips():
    results = {}
    with open('scan.log') as f:
        p_stats = re.compile('--- ' + ip_address_regex() + ' ping statistics ---')
        p_benchmarks = re.compile('round-trip min/avg/max/stddev = '+decimal_regex()+'/'+decimal_regex()+'/'+decimal_regex()+'/'+decimal_regex()+' ms')
        ip = None
        lc = 0
        for l in f:
            stats = re.findall(p_stats, l)
            if stats:
                ip = stats[0]
                lc = 0
            lc += 1
            if lc == 3:
                benchmarks = re.findall(p_benchmarks, l)
                if benchmarks:
                    results[ip] = {
                        'min': benchmarks[0][0],
                        'avg': benchmarks[0][1],
                        'max': benchmarks[0][2],
                        'stddev': benchmarks[0][3]
                    }
    print(len(results.keys()), 'people are reachable.')
    return results

def scan(mode='local'):
    public_ip = get_public_ip()
    # public_ip = '105.160.59.0' # Migori, Kenya
    print('Scanning {}...'.format(mode))
    open('scan.log', 'w+')
    ips = []
    if mode == 'local':
        for d in range(*get_local_range(public_ip)):
            ips.append(decimal_to_ip(d))
    elif mode == 'neighborhood':
        for ip in get_region_range(public_ip):
            for d in range(*get_local_range(ip)):
                ips.append(decimal_to_ip(d))
    check_ips(ips)
    results = compile_ips()
    os.remove('scan.log')
    print('Done.')
    return results


def check_ips(ips):
    os.system(' '.join(['ping -t 1 -c 1 -i 0.1 -W 0.001 {} >> scan.log &'.format(ip) for ip in ips]))

def get_public_ip():
    try:
        r = requests.get('http://ip.42.pl/raw')
        public_ip = r.text
        return public_ip
    except:
        raise Exception('Cannot get your public ip!')

def truncate_ip(ip):
    return ip_to_decimal('.'.join(ip.split('.')[:3]+['0']))

def get_local_range(ip):
    from_ip = truncate_ip(ip)
    to_ip = from_ip + 256
    return from_ip, to_ip

def get_region_range(ip, max_away=5, recalculate=False):
    data = []
    if not os.path.exists(NEIGHBOR_IP_FILE) or recalculate:
        print('Calculating neighboring ip ranges...')
        ip_idx = 0
        idx_set = False
        ip_decimal = ip_to_decimal(ip)
        with open(WORLD_IP_FILE) as f:
            lines = csv.DictReader(f, delimiter=',', quotechar='"')
            for row in lines:
                if ip_decimal < int(row['from_ip']) and not idx_set:
                    idx_set = True
                elif not idx_set:
                    ip_idx += 1
                # data.append(row)
                data.append(decimal_to_ip(int(row['from_ip'])))
        with open(NEIGHBOR_IP_FILE, 'w+') as f:
            for ip in data[ip_idx-max_away:ip_idx+max_away]:
                f.write("{}\n".format(ip))
        print('Saved to {}!'.format(NEIGHBOR_IP_FILE))
    else:
        with open(NEIGHBOR_IP_FILE) as f:
            for line in f:
                data.append(line.strip())
    print('Loaded neighboring {} ip ranges!'.format(len(data)))
    return data

def get_popular_range():
    pass

def decimal_to_ip(d):
    return socket.inet_ntoa(struct.pack('!L', d))

def ip_to_decimal(ip):
    return struct.unpack("!L", socket.inet_aton(ip))[0]

if __name__ == '__main__':
    scan('neighborhood')
    # public_ip = get_public_ip()
    # get_region_range(public_ip, max_away=5, recalculate=True)
