import os
import copy
import yaml
from os.path import dirname, abspath, splitext, basename, join

def set_env():
    os.environ['LOCAL_PATH'] = dirname(dirname(abspath(__file__)))
    os.environ['LAUNCH_PATH'] = dirname(abspath(__file__))

def interpolate(compose_file, network_file):
    with open(compose_file, 'r') as f:
        compose_config = yaml.load(f)
    with open(network_file, 'r') as f:
        network_config = yaml.load(f)
    new_compose_config = copy.deepcopy(compose_config)
    new_compose_config['version'] = '2.3'
    nodes = {}
    for service_name in compose_config['services']:
        service = compose_config['services'][service_name]
        network = network_config['services'][service_name]
        new_compose_config['networks'] = network_config['networks']
        if network.get('range'):
            nodes[service_name] = []
            for i in range(network['range'][0], network['range'][1]+1):
                replica_service_name = '{}_{}'.format(service_name, str(i))
                replica_ip = network['ip'].replace('x', str(i))
                service.update(generate_network_config(network['network'], replica_ip))
                new_compose_config['services'][replica_service_name] = copy.deepcopy(service)
                new_compose_config['services'][replica_service_name].update({
                    'environment': ['HOST_IP={}'.format(replica_ip)]
                })
                nodes[service_name].append(replica_ip)
            del new_compose_config['services'][service_name]
        else:
            nodes[service_name] = network['ip']
            service.update(generate_network_config(network['network'], network['ip']))
            new_compose_config['services'][service_name] = service
            new_compose_config['services'][service_name].update({
                'environment': ['HOST_IP={}'.format(network['ip'])]
            })
    for service_name in new_compose_config['services']:
        for n in nodes:
            value = ','.join(nodes[n]) if type(nodes[n]) == list else nodes[n]
            new_compose_config['services'][service_name]['environment'].append(
                '{}={}'.format(n.upper(), value)
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

if __name__ == '__main__':
    compose_file = 'compose_files/app.yml'
    network_file = 'network_files/vmnet_example.yml'
    set_env()
    interpolate(compose_file, network_file)
    run()