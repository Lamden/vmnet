import time, os

def file_listener(test, callback, failure, timeout, fname='fsock'):
    fname = os.path.join(test.project_path, fname)
    if os.path.exists(fname):
        os.remove(fname)
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

def send_to_file(data, fname='fsock'):
    with open(fname, 'a+') as f:
        f.write('{}\n'.format(data))
