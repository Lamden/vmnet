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

    def sig_handler(signal, frame):
        log.critical('Program is now shutting down...')
        loop.call_soon_threadsafe(loop.stop)
        loop.call_soon_threadsafe(loop.close)
        sys.exit(0)

    signal.signal(signal.SIGTERM, sig_handler)

    log.debug('Running server...')
    loop = asyncio.get_event_loop()
    loop.run_forever()

class TestVmnetExample(BaseNetworkTestCase):
    testname = 'node'
    compose_file = 'vmnet-node.yml'
    setuptime = 3
    logdir = 'scripts/logs'
    def test_run_service(self):
        self.execute_python('vmnet_node', run_node, async=True)
        input('Press enter to exit...')

if __name__ == '__main__':
    unittest.main()
