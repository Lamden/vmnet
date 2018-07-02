<p align="center">
  <img src="https://preview.ibb.co/i3Q6Ao/vmnet.png" />
</p>

# Setup

1. Clone vmnet
```bash
$ git clone https://github.com/Lamden/vmnet.git
```

2. Install [Docker](https://docs.docker.com/install/#desktop)

# Configuration

1. Make sure that the version is "2.3" to allow specifying "networks"

```yaml
version: "2.3"
networks:
  vmnet:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
          iprange: 172.28.5.0/24
          gateway: 172.28.5.254
```

2. Configure your node replication. The following config creates 5 nodes with ips `172.28.5.1` `172.28.5.2` ... `172.28.5.5`

```yaml
services:
  api_service:
    range:
      - 1
      - 5
    ip: 172.28.5.x

    ...

```

3. Configure the image, context, dockerfile and any volumes for your node
```yaml
services:
  api_service:

    ...

    build:
      context: ${LOCAL_PATH}/api_source_code
      dockerfile: ${DOCKER_DIR}/api_service_dockerfile
    image: vmnet_client
    volumes:
      - type: bind
        source: ${LOCAL_PATH}/logs
        target: /app/

```

# Run
1. Run `launch.py`
```bash
$ cd vmnet/docker
$ python launch.py --project your_project_name --compose_file your_compose_file.yml --docker_dir your_docker_dir
```
2. List your nodes
```bash
$ docker ps
```
3. Enter your nodes
```bash
$ docker exec -ti your_node_name /bin/bash
```

# Example
Confused? Run an example set up just for you!
```bash
$ cd examples/sample
$ python3 test_sample.py
```

# Testing
Need to test your network of services? You can run your unittests using the `BastTestCase` which will set-up your network, run it for a specified amount of time, log the results into a file, and stop the network on teardown. The setup and teardown will only happen once in your test. Your tests should read and parse the logfile to verify the expected results. That said, you need to control what gets written to the logfile. The logfile for the test will be automatically stored as `vmnet/logs/<test_name>.log`.

1. Write a unittest
```python
from vmnet.tests.base import *
from vmnet.tests.util import *
import unittest

class TestVmnetExample(BaseTestCase):
    setuptime = 15
    testname = 'vmnet_example'
    def test_your_tasks(self):
        self.assertTrue('Test it' == 'Test it')
```

2. Run your test. Example output:
```bash
$ python -m unittest discover -v
```
```console
test_each_can_receive_messages (test_vmnet.TestVmnetExample) ... Running test "vmnet_example" and waiting for 20s...
Creating vmnet_client_5 ... done
Creating vmnet_client_1 ... done
Creating vmnet_client_4 ... done
Creating vmnet_server   ... done
Creating vmnet_client_2 ... done
Creating vmnet_client_3 ... done
vmnet_client_4 exited with code 137
vmnet_server exited with code 137
vmnet_client_1 exited with code 137
cf88aa06cb0d
7952279ad8bc
5fa9c857fed8
vmnet_client_2 exited with code 137
vmnet_client_5 exited with code 137
d78305d04dfe
5b2007dd6f26
vmnet_client_3 exited with code 137
682de1ba134d
7172c4b6dd87
cf88aa06cb0d
7952279ad8bc
5fa9c857fed8
d78305d04dfe
5b2007dd6f26
682de1ba134d
7172c4b6dd87
ok
test_has_listeners (test_vmnet.TestVmnetExample) ... ok

----------------------------------------------------------------------
Ran 2 tests in 33.523s

OK

```
