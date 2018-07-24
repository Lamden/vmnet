import re
import os
import time
import uuid
import pickle
import pstats

def profile(filepath):
    pstats.Stats(filepath).strip_dirs().sort_stats('cumtime').print_stats(50)

def add_args(fn, *args, **kwargs):
    def wrapper():
        return fn(*args, **kwargs)
    return wrapper

def get_path(path):
    """
        Uses the `PYTHONPATH` as the base path and returns the path relative to that

        # Arguments
        path (str): path relative to `PYTHONPATH`

        # Returns
        (str): absolute path
    """
    return os.path.join(os.environ['PYTHONPATH'], path)

def ip_address_regex():
    """
        Returns the regex pattern for ip addresses

        # Returns
        (pattern): ip addresses pattern
    """
    return r'([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})'

def port_regex():
    """
        Returns the regex pattern for port numbers

        # Returns
        (pattern): ports pattern
    """
    return r'([0-9]{4,5})'

def decimal_regex():
    """
        Returns the regex pattern for decimal numbers

        # Returns
        (pattern): decimal number pattern
    """
    return r'(\d*\.?\d*)'
