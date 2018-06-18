import asyncio, zmq, zmq.asyncio
import signal, sys

def signal_term_handler(signal, frame):
    print('sigterm')
    socket.close()
    loop.close()
    sys.exit(0)

async def recv_that(socket):
    while True:
        print("tryna send that")
        await asyncio.sleep(1)
        socket.send(b'ack')

loop = asyncio.get_event_loop()
signal.signal(signal.SIGTERM, signal_term_handler)

try:
    context = zmq.asyncio.Context()
    socket = context.socket(zmq.PAIR)  # For communication with main process
    socket.bind('ipc://test_pair_socket')

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
