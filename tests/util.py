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
