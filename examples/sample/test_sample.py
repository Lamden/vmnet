from vmnet.test.base import *
from vmnet.test.util import *
import unittest, time

def run_node():
    import os, asyncio, signal, sys
    from vmnet.test.logger import get_logger
    log = get_logger(os.getenv('HOSTNAME'))
    log.debug("this is a debugging message")
    log.info("this is an informational message")
    log.warning("this is a warning message")
    log.error("this is an error message")
    log.critical("this is a critical message")

    def sig_handler(signum, frame):
        signame = signal.Signals(signum).name
        print('Received... {}'.format(signame))
        if signame == 'SIGTERM':
            print('Program is now shutting down...')
            loop.call_soon_threadsafe(loop.stop)
            loop.call_soon_threadsafe(loop.close)
            print('Torn down successfully')
            sys.exit(0)

    for i in [x for x in dir(signal) if x.startswith("SIG")]:
        try: signal.signal(
            getattr(signal, i),
            sig_handler
        )
        except: pass

    log.debug('Running server...')
    loop = asyncio.get_event_loop()
    loop.run_forever()

class TestVmnetExample(BaseNetworkTestCase):
    testname = 'node'
    compose_file = 'vmnet-node.yml'
    setuptime = 5
    logdir = 'scripts/logs'
    def test_run_service(self):
        for node in self.groups.get('vmnet_node'):
            self.execute_python(node, run_node, async=True)
        input('Press enter to exit...')

if __name__ == '__main__':
    unittest.main()
