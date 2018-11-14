<p align="center">
  <img src="https://preview.ibb.co/i3Q6Ao/vmnet.png" />
</p>

# Vmnet
This is a network testing framework based on Docker. It can spin up multiple nodes and allow you to inject code during run-time. This is used for testing Lamden's blockchain technology - Cilantro. It also includes a command client to make running the tests and building images easier. There is a very simply configuration file that sets up everything. Note that this only works for Python3.

# Setup

1. Install Docker 18.03.1-ce for [MacOS](https://docs.docker.com/docker-for-mac/release-notes/) or [Windows](https://docs.docker.com/docker-for-windows/release-notes/)

2. Setting up a virutal environment is highly recommended
```
$ virtualenv -p python3 venv
$ source venv/bin/activate
```

2. Install vmnet
```
$ pip3 install vmnet
```

# Configuration

1. Create a folder to hold any images and config files inside your main repository which contains the application you want to test. We'll name this one `config_folder`:
```
$ cd /path/to/your_application/
$ mkdir config_folder/
```

2. Use an image file such as this one, we'll call it `config_folder/docknet_base`:
```text
FROM alpine:3.7
COPY . /app
WORKDIR /app

EXPOSE 8080

RUN apk update
RUN apk add --update --no-cache python3 py-pip python3-dev build-base
RUN pip3 install vmnet --upgrade --no-cache-dir
RUN apk del py-pip python3-dev

CMD python3 -m http.server
```

3. Use a configuration file like this, we'll name it `config_folder/nodes.json`:
```json
{
    "services": [
        {
            "name": "node",
            "image": "docknet_base",
            "count": 5,
            "ports": [
                8000
            ]
        }
    ]
}
```

# Run
## Start the network without unit-tests
This will start the nodes without any test code. You can enter the node to see what's happening:
```
$ vment -f /path/to/your_application/config_folder/nodes.json
```
To stop the network:
```
$ vment -f /path/to/your_application/config_folder/nodes.json -s
```
To build the images only:
```
$ vment -f /path/to/your_application/config_folder/nodes.json -b
```
To clean and remove related containers only:
```
$ vment -f /path/to/your_application/config_folder/nodes.json -c
```
To destroy and remove related containers and images:
```
$ vment -f /path/to/your_application/config_folder/nodes.json -d
```
## Start the network with unit-tests
1. First, create a unit-test like this, let's name it `test_hello_world.py`:
```python
import unittest
from vmnet.testcase import BaseTestCase

def hello():
    import time
    from vmnet.logger import get_logger
    log = get_logger('hello')
    while True:
        log.critical('hello')
        time.sleep(1)

def world():
    import time
    from vmnet.logger import get_logger
    log = get_logger('world')
    while True:
        log.important('world')
        time.sleep(1)

class TestExample(BaseTestCase):
    config_file = 'config_folder/node.json'
    def test_example(self):
        self.execute_python('node_1', hello)
        self.execute_python('node_2', world)
        input('Hit enter to terminate')

if __name__ == '__main__':
    unittest.main()
```
2. and... just run it.
```
$ python3 test_hello_world.py
```
