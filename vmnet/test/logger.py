import logging
import os

def get_logger(name=''):
    filedir = "logs/{}".format(os.getenv('TEST_NAME', 'test'))
    filename = "{}/{}.log".format(filedir, name)
    os.makedirs(filedir, exist_ok=True)
    filehandlers = [
        logging.FileHandler(filename),
        logging.StreamHandler()
    ]
    logging.basicConfig(
        format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
        handlers=filehandlers,
        level=logging.DEBUG
    )
    return logging.getLogger(name)
