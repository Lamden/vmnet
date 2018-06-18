import asyncio, zmq, zmq.asyncio
import signal, sys

def signal_term_handler(signal, frame):
    print('sigterm')
    socket.close()
    loop.close()
    sys.exit(0)

async def recv_that(socket):
    while True:
        print("tryna recv that")
        msg = await socket.recv()
        print("got msg: {}".format(msg))


loop = asyncio.get_event_loop()
signal.signal(signal.SIGTERM, signal_term_handler)

try:
    context = zmq.asyncio.Context()
    socket = context.socket(zmq.PAIR)  # For communication with main process
    socket.connect('ipc://test_pair_socket')

    loop.run_until_complete(recv_that(socket))
except:
    socket.close()
    print(
        'running', loop.is_running()
        )
    print(
        'closed', loop.is_closed()
    )
    loop.close()
