import os
import logging
import sys
import shutil
from os.path import dirname, abspath

def get_logger(name='tests', level=logging.DEBUG):
    filedir = '{}/logs/{}'.format(abspath(dirname(__file__)), os.getenv('TEST_NAME', name))
    filename = "{}/{}.log".format(filedir, name)
    os.makedirs(filedir, exist_ok=True)
    filehandlers = [
        logging.FileHandler(filename),
        logging.StreamHandler(sys.stdout)
    ]
    logging.basicConfig(
        format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
        handlers=filehandlers,
        level=level
    )
    return logging.getLogger(name)
