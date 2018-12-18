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
    "environment": {
       "SOME_ENV": "applies to all nodes"
    },
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

# Guide

## Docker-based Workflow

### The `vmnet` command line tool
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
### Unit-testing for Docker-based tests
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

## Cloud-based Workflow

For now, we only support AWS. The workflow will remain the same for other platforms in potential future releases.

### Configuration

1. Go to [AWS IAM](https://console.aws.amazon.com/iam) and get your `AWS Access Key ID` and `AWS Access Secret`

2. Enter the keys into your local system
```
$ aws configure
```

3. The configuration remains the same as before but now includes the `aws` section:
```
{
    "aws": {
        "use_elastic_ips": true or false, <-- false by default, makes sure that IPs remain the same through its life-time
        "security_groups": {
            "my_security_group": {
                "name": "my_security_group", <-- This must be the same as the name in the above line
                "description": "I am a sample security group",
                "permissions": [
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 22, <-- The SSH Port 22 must be enabled for `vmnet` to work
                        "ToPort": 22,
                        "IpRanges": [
                            {
                                "CidrIp": "0.0.0.0/0"
                            }
                        ]
                    },
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 10000,
                        "ToPort": 10100,
                        "IpRanges": [
                            {
                                "CidrIp": "0.0.0.0/0"
                            }
                        ]
                    }
                ]
            }
        },
        "images": {
            "my_service": {
                "name": "my_service", <-- This must be the same as the name in the above line
                "repo_name": "my_repo",
                "repo_url": "https://github.com/MyUsername/my_repo.git",
                "branch": "my-branch-name",
                "username": "ubuntu", <-- May differ depending on your operating system and setup
                "security_group": "my_security_group",
                "build_ami": "ami-0f65671a86f061fcd", <-- Get the ami_id from AWS corresponding to your docker image
                "instance_type": "t2.micro",
                "build_instance_type": "t2.medium" <-- This is used when building the service image
            }
        }
    },
    "services": [
        ...
    ]
}
```

### The `vmnet-cloud` command line tool

To build all of your AMIs from a docker image on AWS (may cost money due to instances spinning up):
```
$ vmnet-cloud -p aws -c path/to/your/config/file build -a
```
To build a single AMI from a docker image:
```
$ vmnet-cloud build -n sample_Dockerfile
```
To bring up the network or any missing node:
```
$ vmnet-cloud up
```
To bring up a specific instance:
```
$ vmnet-cloud up -n node_1
```
To bring down the entire network:
```
$ vmnet-cloud down
```
To bring down the entire network, deallocate, terminate, destroy, etc as many resources as can be done:
```
$ vmnet-cloud down -d
```
To start a specific node:
```
$ vmnet start -n node_1
```
To ssh into a node:
```
$ vmnet ssh -n node_1
```

### Unit-testing for Cloud-based tests
1. Guess what? It is pretty much the same as the Docker tests:
```python
import unittest
from vmnet.cloud.testcase import AWSTestCase
 
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
 
class TestExample(AWSTestCase):
    config_file = 'config_folder/node.json'
    keep_up = True # Brings down the nodes when the test completes
    timeout = 30 # Defaults to run forever
    def test_example(self):
        self.execute_python('node_1', hello)
        self.execute_python('node_2', world)
 
if __name__ == '__main__':
    unittest.main()
```
2. Once again, just run it.
```
$ python3 test_hello_world.py
```
