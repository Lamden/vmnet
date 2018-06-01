import logging
import os
import coloredlogs
from coloredlogs.converter import convert

def get_logger(name=''):
    filedir = "logs/{}".format(os.getenv('TEST_NAME', 'test'))
    filename = "{}/{}.log".format(filedir, os.getenv('HOSTNAME', name))
    format = "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"

    class ColoredFileHandler(logging.FileHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.setFormatter(
                coloredlogs.ColoredFormatter(format)
            )

    os.makedirs(filedir, exist_ok=True)
    filehandlers = [
        ColoredFileHandler('{}.color'.format(filename)),
        logging.StreamHandler()
    ]
    logging.basicConfig(
        format=format,
        handlers=filehandlers,
        level=logging.DEBUG
    )
    return logging.getLogger(name)

coloredlogs.install(level="DEBUG")

logger = get_logger('coloredlog')
logger.debug("this is a debugging message")
logger.info("this is an informational message")
logger.warning("this is a warning message")
logger.error("this is an error message")
logger.critical("this is a critical message")

with open('logs/test/coloredlog.log') as f:
    print('Parsing logs')
    for line in f:
        print(convert(line.strip()))
