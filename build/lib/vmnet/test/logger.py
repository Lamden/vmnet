import logging
import os
import coloredlogs

# coloredlogs.install(level="DEBUG")

def get_logger(name=''):
    filedir = "logs/{}".format(os.getenv('TEST_NAME', 'test'))
    filename = "{}/{}.log".format(filedir, os.getenv('HOSTNAME', name))
    # format = "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"
    format = '%(asctime)s.%(msecs)03d %(name)s[%(process)d][%(processName)s] %(levelname)-2s %(message)s'

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
    return logging.getLogger(name)
