import logging
import asyncio

from vmnet.logs.logger import get_logger
from kademlia.network import Server

def bootstrap_network():
    with open():
        pass

def run():
    log = get_logger('kademlia')
    server = Server()
    server.listen(8468)
    loop = asyncio.get_event_loop()
    loop.set_debug(True)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    loop.close()

if __name__ == '__main__':
    run()
    result = loop.run_until_complete(server.get(sys.argv[3]))
