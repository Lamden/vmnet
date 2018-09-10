import json, yaml, os, time, docker
from os.path import basename, dirname, join, abspath
from docker.utils import kwargs_from_env

client = docker.APIClient(
    version='1.37', timeout=60, **kwargs_from_env()
)

GATEWAY = "252"
IPRANGE = "172.29"
SUBNET = "172.29.0.0"

def _generate_compose_file(config_file, test_name='sample_test'):
    dc = {}
    test_id = str(int(time.time()))
    with open(config_file) as f:
        config = json.loads(f.read())
        project_path = os.getenv('PROJECT_PATH', dirname(dirname(abspath(config_file))))

        # Set Docker-compose version
        dc["version"] = '2.3'

        # Generate network configs
        dc["networks"] = {
            'vmnet': {
                "driver": "bridge",
                "ipam": {
                    "config": [{
                        "gateway": "{}.255.{}".format(IPRANGE, GATEWAY),
                        "iprange": "{}.1/16".format(IPRANGE),
                        "subnet": "{}/16".format(SUBNET)
                    }]
                }
            }
        }

        # Generate services
        dc["services"] = {}
        nodemap = {}
        group_ips = {}
        group_names = {}
        ip = 1
        for service in config["services"]:
            group_ips[service["name"]] = []
            group_names[service["name"]] = []
            for c in range(service["count"]):
                if service["count"] == 1:
                    name = service["name"]
                else:
                    name = '{}_{}'.format(service["name"], ip)
                ip_addr = '{}.{}.{}'.format(IPRANGE, int(ip/256.0), ip%256)
                group_ips[service["name"]].append(ip_addr)
                group_names[service["name"]].append(name)
                nodemap[name] = ip_addr
                envvar = [
                    'TEST_NAME={}'.format(test_name),
                    'TEST_ID={}'.format(test_id),
                    'HOST_NAME={}'.format(name),
                    'HOST_IP={}.{}.{}'.format(IPRANGE, int(ip/256.0), ip%256)
                ]
                dc["services"][name] = {
                    "container_name": name,
                    "environment": envvar,
                    "expose": ['1024-49151'],
                    "ports": service.get('ports', []),
                    "image": service['image'],
                    "networks": {
                        'vmnet': {
                            "ipv4_address": ip_addr
                        }
                    },
                    "stdin_open": True,
                    "tty": True,
                    "volumes": [{
                        "source": project_path,
                        "target": '/app/',
                        "type": 'bind'
                    }]
                }
                ip += 1

        # Set IPs for groups
        for s in dc["services"]:
            service = dc["services"][s]
            for g in group_ips:
                service['environment'].append(
                    '{}={}'.format(g.upper(), ','.join(group_ips[g]))
                )

    with open('docker-compose.yml', 'w+') as outfile:
        yaml.dump(dc, outfile, default_flow_style=False)

    return {
        'test_name': test_name,
        'test_id': test_id,
        'project_path': project_path,
        'groups_ips': group_ips,
        'groups': group_names,
        'nodemap': nodemap
    }

def _build(config_file, rebuild=False):
    def _build_image(image):
        dockerfile = None
        for root, dirs, files in os.walk(project_path):
            for file in files:
                if file == image:
                    # The API does not show any output!!!
                    os.system('docker build {} -t {} -f {} {}'.format(
                        '--no-cache' if rebuild else '',
                        image, join(root, file),
                        project_path
                    ))

    with open(config_file) as f:
        config = json.loads(f.read())
        project_path = os.getenv('PROJECT_PATH', dirname(dirname(abspath(config_file))))
        built = {}
        for service in config["services"]:
            if built.get(service['image']): continue
            if rebuild: _build_image(service['image'])
            else:
                try: client.inspect_image(service['image'])
                except: _build_image(service['image'])
            built[service['image']] = True

def run(config_file):
    _stop()
    _build(config_file)
    os.system('docker-compose up --remove-orphans &')
    ports, containers_up = {}, {}
    with open('docker-compose.yml') as f:
        config = yaml.load(f)
        services = list(config["services"].keys())
        time.sleep(3.5)
        while True:
            for s in services:
                if containers_up.get(s): continue
                try:
                    c = client.containers(filters={'name': s, 'status':'running'})
                    if not c: continue
                    containers_up[s] = c
                except Exception as e:
                    pass
            if len(services) == len(containers_up):
                break
            time.sleep(0.5)

        for s in config["services"]:
            service = config["services"][s]
            for port in service.get('ports', []):
                cmd = """docker inspect --format='{{(index (index .NetworkSettings.Ports """ + '"{}/tcp"'.format(port) + """) 0).HostPort}}' """ + s
                if not ports.get(s): ports[s] = {}
                proc = os.popen(cmd)
                ports[s][str(port)] = 'localhost:{}'.format(proc.read().strip())
                proc.close()
    return ports

def _rm_network():
    os.system('echo "y" | docker system prune 1>/dev/null')
    os.system('docker network rm $(docker network ls | grep "bridge" | awk \'/ / { print $1 }\') 2>/dev/null')

def _stop():
    with open('docker-compose.yml') as f:
        config = yaml.load(f)
        containers = ' '.join(list(config["services"].keys()))
        os.system('docker kill {} 2>/dev/null'.format(containers))
        os.system('docker rm -f {} 2>/dev/null'.format(containers))
    _rm_network()

def _clean():
    os.system('echo "y" | docker network prune 1>/dev/null')
    os.system('docker kill $(docker ps -aq) 2>/dev/null')
    os.system('docker rm $(docker ps -aq) -f 2>/dev/null')
    _rm_network()

def _destroy(config_file):
    with open(config_file) as f:
        config = json.loads(f.read())
        for service in config["services"]:
            try:
                client.inspect_image(service['image'])
                os.system('docker rmi -f {}'.format(service['image']))
            except:
                pass

def launch(config_file, test_name, clean=False, destroy=False, build=False, stop=False):
    configs = _generate_compose_file(config_file, test_name)
    if stop:
        _stop()
    elif clean:
        _clean()
    elif destroy:
        _destroy(config_file)
    elif build:
        _build(config_file, rebuild=True)
    else:
        _clean()
        ports = run(config_file)
        configs['ports'] = ports
    return configs

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Run your project on a docker bridge network')
    parser.add_argument('--config_file', '-f', help='.yml file which specifies the image, contexts and build of your services', required=True)
    parser.add_argument('--test_name', '-t', help='name of your test', default='testname')
    parser.add_argument('--clean', '-c', action='store_true', help='remove all containers')
    parser.add_argument('--destroy', '-d', action='store_true', help='remove all images and containers listed in the config')
    parser.add_argument('--build', '-b', action='store_true', help='builds the image and does not run the container')
    parser.add_argument('--stop', '-s', action='store_true', help='stops and removes the containers for the specified config file')
    args = parser.parse_args()
    launch(args.config_file, args.test_name, args.clean, args.destroy, args.build, args.stop)
