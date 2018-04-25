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
    results = list(filter(None, loop.run_until_complete(groups)))
    loop.close()
    print(results)

async def check_ip(ip):
    process = await asyncio.create_subprocess_exec(
        'ping', '-t', '1', '-c', '1', ip,
        stdout=asyncio.subprocess.PIPE
    )
    output, stderr = await process.communicate()
    pingstatus = 'online' if '1 packets received' in output.decode() else 'offline'
    print('{} is {}'.format(ip, pingstatus))
    if pingstatus == 'online':
        return ip

def get_local_range():
    try:
        r = requests.get('http://ip.42.pl/raw')
        public_ip = r.text.split('.')
        from_ip = ip_to_decimal('.'.join(public_ip[:3]+['0']))
        to_ip = from_ip + 255
        return from_ip, to_ip
    except:
        raise Exception('Cannot get your public ip!')

def get_subnet_future(from_ip, to_ip):
    return asyncio.gather(*[check_ip(decimal_to_ip(d)) for d in range(from_ip, to_ip)])

def decimal_to_ip(d):
    return socket.inet_ntoa(struct.pack('!L', d))

def ip_to_decimal(ip):
    return struct.unpack("!L", socket.inet_aton(ip))[0]

if __name__ == '__main__':
    discover_nodes()
