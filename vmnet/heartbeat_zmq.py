from vmnet.logger import get_logger
from vmnet.protocol import *
import zmq, os, sys, uuid

log = get_logger('heartbeat')

def listen(port):
    ctx = zmq.Context()
    sock = ctx.socket(zmq.REP)
    sock.bind("tcp://*:{}".format(port))
    log.debug('Listening to the world on port {}...'.format(port))
    poller = zmq.Poller()
    poller.register(sock, zmq.POLLIN | zmq.POLLOUT)
    while True:
        evts = dict(poller.poll())
        if sock in evts:
            while True:
                try:
                    msg = sock.recv_multipart(zmq.NOBLOCK)
                    log.debug("Received request: {}".format(decode_msg(msg)))
                    sock.send(compose_msg('ack'))
                except zmq.Again:
                    break


if __name__ == '__main__':
    listen(os.getenv('DDD_PORT', 31337))
