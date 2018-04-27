import socket, struct
import requests
import csv
import os

WORLD_IP_FILE = 'data/IP2LOCATION-LITE-DB5.csv'
NEIGHBOR_IP_FILE = 'data/neighborhood.txt'
POPULAR_IP_FILE = 'data/popular.txt'

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

def decimal_to_ip(d):
    return socket.inet_ntoa(struct.pack('!L', d))

def ip_to_decimal(ip):
    return struct.unpack("!L", socket.inet_aton(ip))[0]

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
