from vmnet.tests.base import *
from vmnet.vmnet.logger import get_logger
log = get_logger('dis')
import unittest
import time, os

def run_req():
    import threading, time, os
    import zmq
    from zmq.utils.monitor import recv_monitor_message
    from vmnet.logger import get_logger
    log = get_logger('req')
    log.debug('req stared')

    EVENT_MAP = {}
    for name in dir(zmq):
        if name.startswith('EVENT_'):
            value = getattr(zmq, name)
            log.debug("%21s : %4i" % (name, value))
            EVENT_MAP[value] = name

    def event_monitor(monitor):
        while monitor.poll():
            evt = recv_monitor_message(monitor)
            evt.update({'description': EVENT_MAP[evt['event']]})
            log.debug("Event: {}".format(evt))
            if evt['event'] == zmq.EVENT_MONITOR_STOPPED:
                break
        monitor.close()
        log.debug("event monitor thread done!")

    ctx = zmq.Context.instance()
    req = ctx.socket(zmq.REQ)
    req.bind("tcp://{}:6666".format(os.getenv('HOST_IP')))
    monitor = req.get_monitor_socket()
    t = threading.Thread(target=event_monitor, args=(monitor,))
    t.start()

    while True:
        time.sleep(1)


def run_rep():
    import threading, time, os
    import zmq
    from zmq.utils.monitor import recv_monitor_message
    from vmnet.logger import get_logger
    log = get_logger('rep')
    log.debug('rep stared')

    EVENT_MAP = {}
    for name in dir(zmq):
        if name.startswith('EVENT_'):
            value = getattr(zmq, name)
            log.debug("%21s : %4i" % (name, value))
            EVENT_MAP[value] = name

    def event_monitor(monitor):
        while monitor.poll():
            evt = recv_monitor_message(monitor)
            evt.update({'description': EVENT_MAP[evt['event']]})
            log.debug("Event: {}".format(evt))
            if evt['event'] == zmq.EVENT_MONITOR_STOPPED:
                break
        monitor.close()
        log.debug("event monitor thread done!")

    ctx = zmq.Context.instance()
    rep = ctx.socket(zmq.REP)
    monitor = rep.get_monitor_socket()
    t = threading.Thread(target=event_monitor, args=(monitor,))
    t.start()

    rep.connect("tcp://172.29.5.1:6666")


    log.debug('req connected')

    while True:
        time.sleep(1)

class TestMonitor(BaseNetworkTestCase):
    testname = 'test_monitor'
    compose_file = 'kademlia-nodes.yml'
    waittime = 15
    def test_disconnect(self):
        log.debug('disconnect test started')
        self.execute_python('node_1', run_req, async=True)
        self.execute_python('node_2', run_rep, async=True)
        time.sleep(5)
        os.system('docker kill node_2')
        log.debug('disconnect triggered')

if __name__ == '__main__':
    unittest.main()
