import logging
import os
import coloredlogs

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
        logging.FileHandler(filename),
        ColoredFileHandler('{}_color'.format(filename)),
        logging.StreamHandler()
    ]
    logging.basicConfig(
        format=format,
        handlers=filehandlers,
        level=logging.DEBUG
    )
    logger = logging.getLogger(name)
    # coloredlogs.install(level="DEBUG", logger=logger)
    return logger
