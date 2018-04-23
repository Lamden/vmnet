import os
import copy
import yaml
import subprocess
from os.path import dirname, abspath, splitext, basename, join

def set_env(local_path, docker_dir):
    os.environ['LOCAL_PATH'] = local_path
    os.environ['DOCKER_DIR'] = docker_dir

def build_image(service):
    print('Building {}...'.format(service['image']))
    os.system('docker build -t {} -f {} {}'.format(
        service['image'], service['build']['dockerfile'], service['build']['context']
    ))

def build_if_not_exist(services):
    lines = subprocess.check_output(['docker', 'images']).decode().split('\n')[1:]
    built_images = {line.split()[0]: True for line in lines if len(line)}
    images = [services[i] for i in services if not built_images.get(services[i]['image'])]
    ordered_images = { 'base':[], 'build':[] }
    for image in images:
        ordered_images['base' if 'base' in image['image'] else 'build'].append(image)
    for service in ordered_images['base'] + ordered_images['build']:
        build_image(service)

def generate_configs(compose_file):
    with open(compose_file, 'r') as f:
        compose_config = yaml.load(f)
    new_compose_config = copy.deepcopy(compose_config)

    nodes = {}
    build_if_not_exist(compose_config['services'])

    for service_name in compose_config['services']:
        if 'base' in service_name:
            del new_compose_config['services'][service_name]
            continue
        service = compose_config['services'][service_name]
        network = service['network'] if service.get('network') else list(compose_config['networks'].keys())[0]
        if service.get('range'):
            nodes[service_name] = []
            for i in range(service['range'][0], service['range'][1]+1):
                slot_num = int(i) - int(service['range'][0])
                replica_service_name = '{}_{}'.format(service_name, str(i))
                replica_ip = service['ip'].replace('x', str(i))
                service.update(generate_network_config(network, replica_ip))
                new_compose_config['services'][replica_service_name] = copy.deepcopy(service)
                new_compose_config['services'][replica_service_name].update({
                    'container_name': replica_service_name,
                    'environment': ['HOST_IP={}'.format(replica_ip), 'SLOT_NUM={}'.format(slot_num)]
                })
                nodes[service_name].append(replica_ip)
            del new_compose_config['services'][service_name]
        else:
            nodes[service_name] = service['ip']
            service.update(generate_network_config(network, service['ip']))
            new_compose_config['services'][service_name] = service
            new_compose_config['services'][service_name].update({
                'container_name': service_name,
                'environment': ['HOST_IP={}'.format(service['ip'])]
            })
    for service_name in new_compose_config['services']:
        for n in nodes:
            value = ','.join(nodes[n]) if type(nodes[n]) == list else nodes[n]
            if not new_compose_config['services'][service_name].get('environment'): continue
            new_compose_config['services'][service_name]['environment'].append(
                '{}={}'.format(n.upper(), value)
            )
        if new_compose_config['services'][service_name].get('range'): del new_compose_config['services'][service_name]['range']
        if new_compose_config['services'][service_name].get('ip'): del new_compose_config['services'][service_name]['ip']
        if os.getenv('TEST_NAME'):
            new_compose_config['services'][service_name]['environment'].append(
                'TEST_NAME={}'.format(os.getenv('TEST_NAME'))
            )
    with open('docker-compose.yml', 'w') as yaml_file:
        yaml.dump(new_compose_config, yaml_file, default_flow_style=False)

def generate_network_config(network_name, ip):
    config = {
        'networks': {
            network_name: {
                'ipv4_address': ip
            }
        }
    }
    return config


def run():
    os.system('docker-compose up')

def prune():
    os.system('echo y | docker system prune')

def clean():
    prune()
    os.system('docker stop $(docker ps -aq)')
    os.system('docker rm $(docker ps -aq) -f')

def destroy(compose_file):
    clean()
    with open(compose_file, 'r') as f:
        compose_config = yaml.load(f)
        services = compose_config['services']
        images = ' '.join([image_name for image_name in services])
        os.system('docker rmi {} -f'.format(images))

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run your project on a network')
    parser.add_argument('--project', help='specify project', required=True)
    parser.add_argument('--prune', action='store_true', help='removes any hanging images or containers')
    parser.add_argument('--clean', action='store_true', help='remove all containers')
    parser.add_argument('--destroy', action='store_true', help='remove all images and containers')

    parser.add_argument('--local_path', help='path containing vmnet and your project', default=dirname(dirname(dirname(abspath(__file__)))))
    parser.add_argument('--compose_file', help='.yml file which specifies the image, contexts and build of your services')
    parser.add_argument('--docker_dir', help='the directory containing the docker files which your compose_file uses')

    args = parser.parse_args()

    project = args.project
    compose_file = args.compose_file or 'compose_files/{}-compose.yml'.format(project)
    docker_dir = args.docker_dir or 'docker_files/{}'.format(project)
    local_path = args.local_path

    if args.prune:
        prune()
    elif args.clean:
        clean()
    elif args.destroy:
        destroy(compose_file)
    else:
        set_env(local_path, docker_dir)
        generate_configs(compose_file)
        run()
