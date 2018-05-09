from vmnet.logger import get_logger
from vmnet.protocol.msg import *
from vmnet.discovery.ddd import *
from kademlia.network import Server as DHT
from queue import Queue
import os, sys, uuid, time, threading, uuid, asyncio, random, zmq.asyncio, warnings, zmq
from zmq.utils.monitor import recv_monitor_message


log = get_logger('server')
loop = asyncio.get_event_loop()
asyncio.set_event_loop(loop)

class Server:
    def __init__(self, mode='test', betray_ratio=3, rediscover_interval=10, cmd_cli=False, block=True):
        self.discovery_mode = mode
        self.rediscover_interval = rediscover_interval
        self.betray_ratio = betray_ratio
        self.dht_port = os.getenv('DHT_PORT', 5678)
        self.server_port = os.getenv('SERVER_PORT', 31337)
        self.network = []
        self.dht = DHT(node_id=os.getenv('HOST_IP'))
        self.dht.listen(self.dht_port)

        if cmd_cli:
            self.q = Queue()
            self.cli_thread = threading.Thread(name='cmd_cli', target=Server.command_line_interface, args=(self.q,))
            self.cli_thread.start()
            asyncio.ensure_future(self.recv_cli())

        self.listen_for_crawlers()
        self.discover_and_join()

        if block:
            log.debug('Server started and blocking...')
            loop.run_forever()

    @staticmethod
    def command_line_interface(q):
        """
            Serves as the local command line interface to set or get values in
            the network.
        """
        while True:
            command = input("Enter command (e.g.: <get/set> <key> <value>):\n")
            args = list(filter(None, command.strip().split(' ')))
            if len(args) != 0: q.put(args)

    async def recv_cli(self):
        print("\n STARTING READING FROM CLI QUEUE \n")
        while True:
            try:
                cmd = self.q.get_nowait()
                print("\n\n EXECUTING CMD: {}\n\n".format(cmd))
                if cmd[0] == 'get':
                    await self.get_value(cmd[1])
                elif cmd[0] == 'set':
                    await self.set_value(cmd[1], cmd[2])
                else:
                    warnings.warn("Unknown cmd arg: {}".format(cmd[0]))
            except Exception as e:
                pass
            await asyncio.sleep(0.5)

    async def set_value(self, key, val):
        log.debug('setting {} to {}...'.format(key, val))
        output = await asyncio.ensure_future(self.dht.set(key, val))
        log.debug('done!')

    async def get_value(self, key):
        log.debug('getting {}...'.format(key))
        res = await asyncio.ensure_future(self.dht.get(key))
        log.debug('res={}'.format(res))
        return res

    def discover_and_join(self):
        new_network = discover(self.discovery_mode)
        log.debug('Newly joined network: {}'.format(new_network))
        if self.betray_ratio * len(self.network) < len(new_network):
            betray_all(self.network)
            self.network = new_network
        self.join_network()

    def join_network(self):
        try:
            self.network.append(os.getenv('HOST_IP', '127.0.0.1'))
            loop.run_until_complete(self.dht.bootstrap([(ip, self.dht_port) for ip in self.network]))
        except: pass

    def listen_for_crawlers(self):
        port = self.server_port
        self.ctx = ctx = zmq.asyncio.Context()
        self.sock = sock = ctx.socket(zmq.REP)
        sock.bind("tcp://*:{}".format(port))
        log.debug('Listening to the world on port {}...'.format(port))
        asyncio.ensure_future(self.listen(sock))

    async def listen(self, socket):
        while True:
            msg = await socket.recv_multipart()
            msg_type, data = decode_msg(msg)
            if data != []:
                log.debug("Received - {}: {}".format(msg_type, data))
            self.select_action(msg_type, data)

    async def heartbeat(self):
        while True:
            self.sock.send(compose_msg('beat'))
            asyncio.sleep(0.05)

    def echo(self):
        self.sock.send(compose_msg('echo', os.getenv('HOST_IP', '127.0.0.1')))

    def select_action(self, msg_type, data=[]):
        if msg_type == 'discover':
            self.discover_network(*data)
        elif msg_type == 'verify':
            self.challenge_response(*data)
        elif msg_type == 'role':
            self.role(*data)
        elif msg_type == 'beat':
            self.echo()
        elif msg_type == 'echo':
            self.refresh_connection(*data)
        pass

    def discover_network(self, *args):
        # TODO Rate limit this call
        self.sock.send(compose_msg('ack'))

    def challenge_response(self, *args):
        """
            Prove that this ip owns the verifying key
        """
        pass

    def switch_port(self):
        """
            Switch the kademlia port so people can't just follow ips
        """
        self.sock.send(compose_msg('ack_switch'))

    def role(self, *args):
        pass

if __name__ == '__main__':
    server = Server(cmd_cli=True)
