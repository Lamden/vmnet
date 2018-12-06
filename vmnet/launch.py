import json, yaml, os, time, subprocess, sys
from os.path import basename, dirname, join, abspath
from vmnet.parser import load_test_envvar

GATEWAY = "252"
IPRANGE = "172.29"
SUBNET = "172.29.0.0"

def _run_command(command):
    return subprocess.check_output(command.split(' ')).decode()

def _generate_compose_file(config_file, test_name='sample_test'):
    if not config_file:
        return {}
    print('_' * 128 + '\n')
    print('    Generating docker-compose.yml for "{}"...'.format(test_name))
    print('_' * 128 + '\n')
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
                envvar = load_test_envvar(test_name, test_id, name,
                    '{}.{}.{}'.format(IPRANGE, int(ip/256.0), ip%256))
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
                    "volumes": ['{}:{}'.format(project_path, '/app/')]
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

    print('\nDone.\n')

    return {
        'test_name': test_name,
        'test_id': test_id,
        'project_path': project_path,
        'groups_ips': group_ips,
        'groups': group_names,
        'nodemap': nodemap
    }

def _build(config_file=None, rebuild=False, image_name=None):
    def _build_image(image):
        print('_' * 128 + '\n')
        print('    Building image "{}"'.format(image))
        print('_' * 128 + '\n')
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
        print('\nDone.\n')

    if image_name:
        for root, dirs, files in os.walk('.'):
            for file in files:
                if image_name == file:
                    os.system('docker build {} -t {} -f {} {}'.format(
                        '--no-cache' if rebuild else '',
                        image_name, os.path.join(root, image_name),
                        '.'
                    ))
    else:
        with open(config_file) as f:
            config = json.loads(f.read())
            project_path = os.getenv('PROJECT_PATH', dirname(dirname(abspath(config_file))))
            built = {}
            for service in config["services"]:
                if built.get(service['image']): continue
                if rebuild: _build_image(service['image'])
                else:
                    if not service['image'] in _run_command('docker images'):
                        _build_image(service['image'])
                built[service['image']] = True

def _run(config_file):
    _stop()
    _build(config_file)
    print('_' * 128 + '\n')
    print('    Starting Docker Containers...')
    print('_' * 128 + '\n')
    os.system('docker-compose up --remove-orphans &')
    ports, containers_up = {}, {}
    project_path = os.getenv('PROJECT_PATH', dirname(dirname(abspath(config_file))))
    with open('docker-compose.yml') as f:
        config = yaml.load(f)
        services = list(config["services"].keys())
        time.sleep(3.5)
        while True:
            for s in services:
                if containers_up.get(s): continue
                if s in _run_command('docker ps'):
                    containers_up[s] = True
            if len(services) == len(containers_up):
                break
            time.sleep(0.5)

        for s in config["services"]:
            if os.getenv('CIRCLECI'):
                os.system('docker cp {}/. {}:/app/'.format(project_path, s))
            service = config["services"][s]
            for port in service.get('ports', []):
                cmd = """docker inspect --format='{{(index (index .NetworkSettings.Ports """ + '"{}/tcp"'.format(port) + """) 0).HostPort}}' """ + s
                if not ports.get(s): ports[s] = {}
                proc = os.popen(cmd)
                ports[s][str(port)] = 'localhost:{}'.format(proc.read().strip())
                proc.close()
    print('_' * 128 + '\n')
    print('    Docker Containers are now ready for use')
    print('_' * 128 + '\n')
    return ports

def _rm_network():
    os.system('echo "y" | docker system prune 1>/dev/null')
    os.system('docker network rm $(docker network ls | grep "bridge" | awk \'/ / { print $1 }\') 2>/dev/null')

def _stop():
    with open('docker-compose.yml') as f:
        config = yaml.load(f)
        containers = ' '.join(list(config["services"].keys()))
        print('_' * 128 + '\n')
        print('    Killing Docker Containers for {}...'.format(containers))
        print('_' * 128 + '\n')
        os.system('docker kill {} 2>/dev/null'.format(containers))
        os.system('docker rm -f {} 2>/dev/null'.format(containers))
    _rm_network()
    print('\nOk.\n')

def _clean():
    print('_' * 128 + '\n')
    print('    Killing all Docker Containers...')
    print('_' * 128 + '\n')
    os.system('echo "y" | docker network prune 1>/dev/null')
    os.system('docker kill $(docker ps -aq) 2>/dev/null')
    os.system('docker rm $(docker ps -aq) -f 2>/dev/null')
    _rm_network()
    print('\nOk.\n')

def _destroy(config_file=None, image_name=None):

    if not config_file:
        print('_' * 128 + '\n')
        print('    Wiping all Docker Images...')
        print('_' * 128 + '\n')
        os.system('docker rmi -f {}'.format(image_name))
    else:
        with open(config_file) as f:
            config = json.loads(f.read())
            print('_' * 128 + '\n')
            print('    Wiping Docker Images for {}...'.format(config["services"].keys()))
            print('_' * 128 + '\n')
            for service in config["services"]:
                if service['image'] in _run_command('docker images'):
                    os.system('docker rmi -f {}'.format(service['image']))

    print('\nOk.\n')

def launch(config_file, test_name, clean=False, destroy=False, build=False, stop=False, project_path=None):
    configs = _generate_compose_file(config_file, test_name)
    if project_path:
        os.environ['PROJECT_PATH'] = os.path.abspath(project_path)
    if stop:
        _stop()
    elif clean:
        _clean()
    elif destroy:
        if type(destroy) == str:
            _destroy(image_name=destroy)
        else:
            _destroy(config_file)
    elif build:
        if type(build) == str:
            _build(rebuild=True, image_name=build)
        else:
            _build(build)
    else:
        if not config_file:
            raise Exception('You must provide the path to the config file via --config_file or -f')
        ports = _run(config_file)
        configs['ports'] = ports

    return configs

def main():
    print('''
                               _
     _   _ ____  ____  _____ _| |_
    | | | |    \|  _ \| ___ (_   _)
     \ V /| | | | | | | ____| | |_
      \_/ |_|_|_|_| |_|_____)  \__)

      Brought to you by Lamden.io

    ''')
    import argparse
    parser = argparse.ArgumentParser(description='Run your project on a docker bridge network')
    parser.add_argument('--config_file', '-f', help='.yml file which specifies the image, contexts and build of your services')
    parser.add_argument('--project_path', '-p', help='Project path to run your code from', required=True)
    parser.add_argument('--test_name', '-t', help='name of your test', default='testname')
    parser.add_argument('--clean', '-c', action='store_true', help='remove all containers')
    parser.add_argument('--destroy', '-d', help='remove all images and containers listed in the config')
    parser.add_argument('--build', '-b', help='builds the image and does not run the container')
    parser.add_argument('--stop', '-s', action='store_true', help='stops and removes the containers for the specified config file')
    args = parser.parse_args()
    if not launch(args.config_file, args.test_name, args.clean, args.destroy, args.build, args.stop, args.project_path):
        parser.print_help(sys.stderr)
