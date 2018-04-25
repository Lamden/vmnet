"""
    Decentralized Dynamic Discovery
"""

import socket, struct
import asyncio
from urllib import urlopen

def discover_nodes():
    public_ip = urlopen('http://ip.42.pl/raw').read()
    print(public_ip)
    # check_ip_range(1084596224, 1084596479)

def check_ip_range(from_ip, to_ip):
    pass
    # loop = asyncio.get_event_loop()
    # future = asyncio.Future()
    # asyncio.ensure_future(slow_operation(future))
    # for d in range(from_ip, to_ip):
    #     ip = decimal_to_ip(d)
    #     asyncio.gather(*[coro("group 1.{}".format(i)) for i in range(1, 6)])
    #     output = subprocess.Popen(['ping', '-n', '1', '-w', '500', str(all_hosts[i])], stdout=subprocess.PIPE, startupinfo=info).communicate()[0]
    #     if "Destination host unreachable" in output.decode('utf-8'):
    #         print(str(all_hosts[i]), "is Offline")
    #     elif "Request timed out" in output.decode('utf-8'):
    #         print(str(all_hosts[i]), "is Offline")
    #     else:
    #         print(str(all_hosts[i]), "is Online")
    # loop.run_until_complete(future)
    # print(future.result())
    # loop.close()

def decimal_to_ip(d):
    return socket.inet_ntoa(struct.pack('!L', d))

def ip_to_decimal(ip):
    return struct.unpack("!L", socket.inet_aton(ip))[0]

async def check_ip(ip):
    pass

if __name__ == '__main__':
    discover_nodes()
