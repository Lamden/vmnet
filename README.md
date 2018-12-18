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
 
RUN apk update \
   && apk add --update --no-cache python3 py-pip python3-dev build-base \
   && pip3 install vmnet --upgrade --no-cache-dir \
   && apk del py-pip python3-dev
 
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
To start the network for the first time:
```
$ vmnet -c /path/to/your_application/config_folder/nodes.json -p /path/to/your_application start
```
To stop the network:
```
$ vmnet stop
```
To stop a specific node:
```
$ vmnet stop -n node_1
```
To start the same network again (cached from previous run):
```
$ vmnet start
```
To start a specific node:
```
$ vmnet start -n node_1
```
To enter a node:
```
$ vmnet enter -n node_1
```
To (re)build all the images found in your project:
```
$ vmnet build
```
To build the specific image in your project:
```
$ vmnet build -n specific_image_name
```
To kill and remove containers used by your project:
```
$ vmnet clean
```
To kill, remove both containers and images used in your project:
```
$ vmnet destroy
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
