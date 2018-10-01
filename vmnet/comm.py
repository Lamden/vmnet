import time, os

def file_listener(test, callback, failure, timeout):
    fname = '{}/fsock'.format(test.project_path)
    open(fname, 'w+').close()
    start = time.time()
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
            time.sleep(0.01)

def send_to_file(data):
    with open('fsock', 'a+') as f:
        f.write('{}\n'.format(data))
