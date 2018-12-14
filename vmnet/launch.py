import os, sys, json, paramiko, socket, queue, select, time, select, vmnet, subprocess, click, yaml
from vmnet.parser import load_test_envvar
from os.path import join, exists, expanduser, dirname, abspath, basename, splitext

path = abspath(vmnet.__path__[0])
GATEWAY = "252"
IPRANGE = "172.29"
SUBNET = "172.29.0.0"

class Docker:
    pass

def _run_command(command):
    return subprocess.check_output(command.split(' ')).decode()

def _generate_compose_file(config_file, test_name='sample_test', environment={}):
    if not config_file:
        return {}
    print('_' * 128 + '\n')
    print('    Generating docker-compose.yml for "{}"...'.format(test_name))
    print('_' * 128 + '\n')
    dc = {}
    test_id = str(int(time.time()))
    with open(config_file) as f:
        config = json.loads(f.read())

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
        config_env = dc.get('environment', {})
        config_env.update(environment)
        global_environment = ['{}={}'.format(k,v) for k,v in config_env.items()]
        global_environment.append('VMNET_DOCKER=True')
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
                    "environment": envvar + global_environment,
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
                    "volumes": ['{}:{}'.format(Docker.project_path, '/app/')]
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
        'project_path': Docker.project_path,
        'groups_ips': group_ips,
        'groups': group_names,
        'nodemap': nodemap
    }

@click.command()
@click.option('--image_name', '-n', help='Rebuild specific image in the config', default='')
def build(image_name=''):
    _build(image_name)

def _build_image(image):
    print('_' * 128 + '\n')
    print('    Building image "{}"'.format(image))
    print('_' * 128 + '\n')
    dockerfile = None
    for root, dirs, files in os.walk(Docker.project_path):
        for file in files:
            if file == image:
                # The API does not show any output!!!
                os.system('docker build -t {} -f {} {}'.format(
                    image, join(root, file),
                    Docker.project_path
                ))
    print('\nDone.\n')

def _build(image_name=''):
    if image_name != '':
        for root, dirs, files in os.walk('.'):
            for file in files:
                if image_name == file:
                    os.system('docker build -t {} -f {} {}'.format(
                        image_name, join(root, image_name),
                        '.'
                    ))
    else:
        with open(Docker.config_file) as f:
            config = json.loads(f.read())
            built = {}
            for service in config["services"]:
                if built.get(service['image']): continue
                if not service['image'] in _run_command('docker images'):
                    _build_image(service['image'])
                built[service['image']] = True

def run(node_name=None):
    ports, containers_up = {}, {}
    if node_name:
        os.system('docker-compose start {}'.format(node_name))
    else:
        _stop()
        _build()
        print('_' * 128 + '\n')
        print('    Starting Docker Containers...')
        print('_' * 128 + '\n')
        os.system('docker-compose up --remove-orphans &')

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
                os.system('docker cp {}/. {}:/app/'.format(Docker.project_path, s))
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
    Docker.config['ports'] = ports


@click.command()
@click.option('--node_name', '-n', help='Name of node to stop', default=None)
def stop(node_name):
    _stop(node_name)

def _rm_network():
    print('Removing bridge network...')
    os.system('echo "y" | docker system prune 1>/dev/null')
    os.system('docker network rm $(docker network ls | grep "bridge" | awk \'/ / { print $1 }\') 2>/dev/null')

def _stop(node_name=None):
    if node_name:
        os.system('docker kill {}'.format(node_name))
    else:
        with open('docker-compose.yml') as f:
            config = yaml.load(f)
            containers = ' '.join(list(config["services"].keys()))
            print('_' * 128 + '\n')
            print('    Killing Docker Containers {}...'.format(containers))
            print('_' * 128 + '\n')
            os.system('docker kill {} 2>/dev/null'.format(containers))
            os.system('docker rm -f {} 2>/dev/null'.format(containers))
        _rm_network()
    print('\nOk.\n')

@click.command()
def clean():
    _clean()

def teardown():
    _clean()

def _clean():
    print('_' * 128 + '\n')
    print('    Killing all Docker Containers...')
    print('_' * 128 + '\n')
    os.system('echo "y" | docker network prune 1>/dev/null')
    os.system('docker kill $(docker ps -aq) 2>/dev/null')
    os.system('docker rm $(docker ps -aq) -f 2>/dev/null')
    _rm_network()
    print('\nOk.\n')

@click.command()
def destroy(config_file=None, image_name=None):

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

def _setup_config(config_file, test_name='sample_test', project_path='', environment={}):
    Docker.old_config = join(path, '.vmnet_previous_config')

    if config_file == '':
        if not exists(Docker.old_config):
            raise Exception('Please specify --config -c as it has not been set in the previous run.')
        else:
            with open(Docker.old_config) as f:
                config = json.loads(f.read())
                config_file, project_path = config['config_file'], config['project_path']
                print('Old config found, using "{}"'.format(config_file))
    else:
        with open(Docker.old_config, 'w+') as f:
            f.write(json.dumps({
                'config_file': abspath(config_file),
                'project_path': abspath(project_path)
            }))

    if project_path == '':
        project_path = dirname(dirname(abspath(config_file)))
    Docker.project_path = project_path
    Docker.config_name = splitext(basename(config_file))[0]
    Docker.config_file = abspath(config_file)
    Docker.dir = dirname(Docker.config_file)
    Docker.config = _generate_compose_file(Docker.config_file, test_name, environment=environment)
    os.environ['PROJECT_PATH'] = project_path
    if not config_file:
        raise Exception('You must provide the path to the config file via --config_file or -f')

def launch(config_file, test_name='sample_test', project_path='', environment={}):
    _setup_config(config_file, test_name, project_path, environment=environment)
    run()
    return Docker.config

@click.command()
@click.option('--node_name', '-n', help='Name of node to enter')
@click.option('--shell', '-s', help='Shell', default='/bin/bash')
def enter(node_name, shell):
    os.system('docker exec -ti {} {}'.format(node_name, shell))

@click.command()
@click.option('--config_file', '-c', help='.json file which specifies the image, contexts and build of your services', default='')
@click.option('--project_path', '-p', help='Project path to run your code from', default='')
@click.option('--node_name', '-n', help='Name of node to start', default=None)
def start(config_file='', project_path='', node_name=None):
    if node_name:
        _setup_config(config_file, project_path=project_path)
        run(node_name)
    else:
        launch(config_file, project_path=project_path)

@click.group()
def main():
    print('''
                               _
     _   _ ____  ____  _____ _| |_
    | | | |    \|  _ \| ___ (_   _)
     \ V /| | | | | | | ____| | |_
      \_/ |_|_|_|_| |_|_____)  \__)

      Brought to you by Lamden.io

    ''')

main.add_command(start)
main.add_command(build)
main.add_command(stop)
main.add_command(clean)
main.add_command(enter)

if __name__ == '__main__':
    main()
