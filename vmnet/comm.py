import time, os

def file_listener(test, callback, failure, timeout):
    fname = '{}/fsock'.format(test.project_path)
    f = open(fname, 'w+')
    f.close()
    os.chmod(fname, 777)
    f = open(fname, 'r+')
    f.truncate()
    start = time.time()
    while True:
        msg = f.readlines()
        if msg:
            if callback(test, [l.strip() for l in msg]) == True:
                break
        if time.time() > start + timeout:
            f.close()
            os.remove(fname)
            failure(test)
            break
        time.sleep(0.01)
    f.close()
    os.remove(fname)

def send_to_file(data):
    with open('fsock', 'a+') as f:
        f.write('{}\n'.format(data))
