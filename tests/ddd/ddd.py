"""
    Decentralized Dynamic Discovery
"""

import socket, struct
import asyncio
import requests
import os

def discover_nodes():
    loop = asyncio.get_event_loop()
    groups = get_subnet_future(*get_local_range())
    results = loop.run_until_complete(asyncio.wait(groups))
    loop.close()
    print(results)

async def check_ip(ip):
    subp = asyncio.subprocess
    process = await asyncio.create_subprocess_exec(
        'ping', '-c', '1', '-i', '0.2', ip,
        stdout=subp.PIPE, stderr=subp.STDOUT
    )
    stdout, stderr = await process.communicate()
    response = stdout.decode()
    if response == 0:
        pingstatus = "online"
    else:
        pingstatus = "offline"
    return '{} is {}'.format(ip, pingstatus)

def get_local_range():
    try:
        r = requests.get('http://ip.42.pl/raw')
        public_ip = r.text.split('.')
        public_ip[3] = '0'
        from_ip = ip_to_decimal('.'.join(public_ip))
        to_ip = from_ip + 255
        return from_ip, to_ip
    except:
        raise Exception('Cannot get your public ip!')

def get_subnet_future(from_ip, to_ip):
    return [check_ip(decimal_to_ip(d)) for d in range(from_ip, to_ip)]

def decimal_to_ip(d):
    return socket.inet_ntoa(struct.pack('!L', d))

def ip_to_decimal(ip):
    return struct.unpack("!L", socket.inet_aton(ip))[0]

if __name__ == '__main__':
    discover_nodes()
