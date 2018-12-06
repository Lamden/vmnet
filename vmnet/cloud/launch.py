from vmnet.cloud.aws import AWS
import click

class API:
    platform = None

@click.command()
@click.option('--image_name', '-n', help='Rebuild specific image in the config')
@click.option('--all', '-a', help='Rebuild all images listed in the config', is_flag=True)
def build(image_name, all):
    assert image_name or all, 'Must specify --image_name -n or --all -a to build'
    API.platform.build(image_name, all)

@click.command()
def up():
    API.platform.up()

@click.command()
def down():
    API.platform.down()

@click.group()
@click.option('--platform', '-p', help='Currently only support AWS', default='aws')
@click.option('--config', '-c', help='Configuration JSON', required=True)
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

if __name__ == '__main__':
    main()
