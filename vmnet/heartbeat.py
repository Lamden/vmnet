from vmnet.logger import get_logger
from vmnet.protocol import *
import socket, os, sys, uuid

log = get_logger('heartbeat')

def listen(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', port))
    s.listen(5)
    log.debug('Listening to the world...')
    conn, addr = s.accept()
    while True:
        try:
            data = conn.recv(1024)
            if not data: continue # No data
            data = decode_msg([data])
            if not data: continue # Don't have cilantro
            challenge_token = uuid.uuid4().hex
            log.debug('Received {}'.format(data))
            conn.sendall(compose_msg(['ack', challenge_token]))
            conn, addr = s.accept()
        except socket.error:
            break
    s.close()

if __name__ == '__main__':
    listen(os.getenv('DDD_PORT', 31337))
