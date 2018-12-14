from vmnet.cloud.aws import AWS
import click, vmnet
from os.path import abspath, exists, join

class API:
    platform = None

@click.command()
@click.option('--image_name', '-n', help='Rebuild specific image in the config')
@click.option('--all', '-a', help='Rebuild all images listed in the config', is_flag=True)
def build(image_name, all):
    assert image_name or all, 'Must specify --image_name -n or --all -a to build'
    API.platform.build(image_name, all)

@click.command()
@click.option('--logging', '-l', help='Enable logging storage if the platform supports it', is_flag=True)
def up(logging):
    API.platform.up(logging=logging)

@click.command()
@click.option('--destroy', '-d', help='Destroy resources for each platform as much as possible', is_flag=True)
def down(destroy):
    API.platform.down(destroy=destroy)

@click.command()
@click.option('--service_name', '-n', help='Service name of the node as specified in the config.')
@click.option('--index', '-i', help='The node index number in the service', type=int, default=0)
def ssh(service_name, index):
    API.platform.ssh(service_name, index)

@click.group()
@click.option('--platform', '-p', help='Currently only support AWS', default='aws')
@click.option('--config', '-c', help='Configuration JSON')
def main(platform, config):
    print('''
                                              _                 _
                               _             | |               | |
     _   _ ____  ____  _____ _| |_ _____ ____| | ___  _   _  __| |
    | | | |    \|  _ \| ___ (_   _|_____) ___) |/ _ \| | | |/ _  |
     \ V /| | | | | | | ____| | |_     ( (___| | |_| | |_| ( (_| |
      \_/ |_|_|_|_| |_|_____)  \__)     \____)\_)___/|____/ \____|

                    Brought to you by Lamden.io

    ''')
    if platform == 'aws':
        API.platform = AWS(config)

main.add_command(build)
main.add_command(up)
main.add_command(down)
main.add_command(ssh)

if __name__ == '__main__':

    main()
