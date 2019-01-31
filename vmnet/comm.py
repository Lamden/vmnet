import time, os

def file_listener(test, callback, failure, timeout):
    start = time.time()
    os.environ['TEST_COMPLETE'] = 'False'
    with open(fname, 'r') as f:
        while True:
            msg = f.readlines()
            if msg:
                if callback([l.strip() for l in msg]) == True:
                    break
            if time.time() > start + timeout:
                f.close()
                os.remove(fname)
                failure()
                break
            if os.getenv('TEST_COMPLETE') == 'True':
                break
            time.sleep(0.01)

def send_to_file(data):
    with open('fsock', 'a+') as f:
        f.write('{}\n'.format(data))
