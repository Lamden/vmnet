import re
import os
import time

def get_path(path):
    """
        Uses the PYTHONPATH as the base path and returns the path relative to that
    """
    return os.path.join(os.environ['PYTHONPATH'], path)

def ip_address_regex():
    """
        Returns the regex pattern for ip addresses
    """
    return r'([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})'

def port_regex():
    """
        Returns the regex pattern for port numbers
    """
    return r'([0-9]{4,5})'

def get_logger():
    """
        Returns the logger based on the TEST_NAME environmental variable
    """
    filename = "logs/{}.log".format(os.getenv('TEST_NAME', 'debug'))
    filehandlers = [logging.FileHandler(filename)]
    if not os.getenv('TEST_NAME'):
        filehandlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
        handlers=filehandlers,
        level=logging.DEBUG
    )
    return logging.getLogger()
