import os, sys, json, paramiko, socket, queue, select, time, select, vmnet, uuid
from dockerfile_parse import DockerfileParser
from os.path import join, exists, expanduser, dirname, abspath, basename, splitext
from vmnet.logger import get_logger
from vmnet.cloud.comm import success_msg
from threading import Thread
import datetime
path = abspath(vmnet.__path__[0])

class Cloud:

    q = queue.Queue()

    def __init__(self, config_file=None):

        old_config = join(path, '.vmnet_cloud_previous_config')
        if not config_file:
            if not exists(old_config):
                raise Exception('Please specify --config -c as it has not been set in the previous run.')
            else:
                with open(old_config) as f:
                    config_file = f.read().strip()
                    print('Old config found, using "{}"'.format(config_file))
        else:
            with open(old_config, 'w+') as f:
                f.write(abspath(config_file))
        self.config_name = splitext(basename(config_file))[0]
        self.config_file = abspath(config_file)
        self.dir = dirname(self.config_file)
        with open(self.config_file) as f:
            self.config = json.loads(f.read())
        self.setup_working_dir()

    def log(self, msg):
        print(msg, end='')

    @classmethod
    def _raise_error(cls, api=None):
        try:
            exc = Cloud.q.get(block=False)
            return exc
        except queue.Empty:
            pass
        else:
            if api:
                print('Bringing down services...')
                api.down()
            raise exc[0].with_traceback(exc[1], exc[2])

    def update_config(self):
        with open(self.config_file, 'w+') as f:
            f.write(json.dumps(self.config, indent=4))

    def setup_working_dir(self):
        self.certs_dir = join(self.dir, 'certs')
        os.makedirs(self.certs_dir, exist_ok=True)

    def parse_docker_file(self, image):

        dfp = DockerfileParser()
        image_setup = {}

        for root, dirs, files in os.walk(self.dir):
            for file in files:
                if file == image['name']:
                    tasks = {
                        'run': [],
                        'cmd': ''
                    }
                    with open(join(root, file)) as f:
                        dfp.content = f.read()
                    for line in dfp.structure:
                        if line['instruction'] == 'RUN':
                            tasks['run'].append(line['value'])
                        elif line['instruction'] == 'CMD':
                            tasks['cmd'] = line['value']

                    return tasks

    def execute_command(self, instance_ip, cmd, username, environment={}, immediate_raise=False, hostname=None):

        def _run(ssh, command):

            env_str = ''
            for k,v in environment.items():
                env_str += '{}={}\n'.format(k,v)
            if env_str != '':
                command = 'echo "{}" > .env; source .env; '.format(env_str) + command

            stdin, stdout, stderr = ssh.exec_command(command)
            err = ''
            complete = False
            log_prefix_fmt = "[{datetime}"
            if hostname:
                log_prefix_fmt += " {}".format(hostname)
            log_prefix_fmt += "]"
            prefix_colors  = {
                    "green": "\033[92m",
                    "endc": "\033[0m",
                    "error": "\033[91m"
            }
            while True:
                if stdout.channel.recv_ready():
                    out = stdout.channel.recv(1024).decode()
                    self.log(out)
                    self.log("{color}{prefix}{endc} {out}".format(
                        color = prefix_colors['green'],
                        prefix = log_prefix_fmt.format(datetime=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                        endc = prefix_colors['endc'],
                        out = out
                    ))
                    if success_msg in out: return
                if stdout.channel.recv_stderr_ready():
                    err = stderr.channel.recv_stderr(len(stderr.channel.in_stderr_buffer)).decode()
                    self.log("{color}{prefix}{endc} {out}".format(
                        color = prefix_colors['green'],
                        prefix = log_prefix_fmt.format(datetime=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                        endc = prefix_colors['endc'],
                        out = err
                    ))
                    if success_msg in err: return
                if complete:
                    break
                if stdout.channel.exit_status_ready():
                    complete = True

            status = stdout.channel.recv_exit_status()

            if status == 1 and err != '':
                raise Exception(err)

        key = paramiko.RSAKey.from_private_key_file(self.key_path)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        environment.update({'VMNET_CLOUD': self.config_name})
        environment.update(self.config.get('environment', {}))

        try:
            print('Sending commands to {}'.format(instance_ip))
            for _ in range(6):
                if self.check_ssh_alive(instance_ip, username):
                    break
                print("SSH connection to {host} not alive yet, waiting 5 seconds then retrying...".format(host=instance_ip))
                time.sleep(5)
            ssh.connect(hostname=instance_ip, username=username, pkey=key)
            for c in cmd.split('&&'):
                print('+ '+ c +'\n')
                if immediate_raise:
                    if self.config['deployment_mode'] == 'production':
                        _run(ssh, c + ' > /dev/null 2>&1 &')
                    else:
                        _run(ssh, c)
                else:
                    if c.startswith('sudo'):
                        _run(ssh, c)
                    else:
                        try: _run(ssh, 'sudo '+c)
                        except: _run(ssh, c)

        except Exception as e:
            raise

    def send_file(self, instance_ip, username, fname, file_content, password=None):
        print('_' * 128 + '\n')
        print('    Sending file "{}" to {}'.format(fname, instance_ip))
        print('_' * 128 + '\n')
        key = paramiko.RSAKey.from_private_key_file(self.key_path)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=instance_ip, username=username, pkey=key)
        sftp = client.open_sftp()
        with open(fname, 'w+') as f:
            f.write(file_content)
        sftp.put(fname, fname, callback=None, confirm=True)
        try: os.remove(fname)
        except: pass
        print('\n{} is done.\n'.format(instance_ip))

    def check_ssh_alive(self, instance_ip, username):
        try:
            key = paramiko.RSAKey.from_private_key_file(self.key_path)
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=instance_ip, username=username, pkey=key)
        except:
            return False
        return True


    def update_image_code(self, image, instance_ip, hostname, init=False, update_commands=[], env={}):
        print('_' * 128 + '\n')
        print('    Cloning repository into instance with ip {}'.format(instance_ip))
        print('_' * 128 + '\n')
        pull = [
            'git fetch origin',
            'git checkout -f {}'.format(image['branch']),
            'git pull origin {}'.format(image['branch'])
        ]
        environment = image.get('environment', {})
        environment.update(env)
        environment.update(self.config.get('environment', {}))
        if init == False:
            for cmd in pull + update_commands:
                self.execute_command(instance_ip, cmd, image['username'], environment, hostname=hostname)
        else:
            for cmd in [
                'sudo chown -R {} .'.format(image['username']),
                'git init',
                'git remote add origin {}'.format(image['repo_url'])
            ] + pull:
                self.execute_command(instance_ip, cmd, image['username'], environment, hostname=hostname)

    def run_image_setup_script(self, image, instance_ip):
        print('_' * 128 + '\n')
        print('    Running setup scripts from Docker Image "{}" on instance with ip {}'.format(image['name'], instance_ip))
        print('_' * 128 + '\n')
        for cmd in self.tasks[image['name']]['run']:
            environment = image.get('environment', {})
            environment.update(self.config.get('environment', {}))
            self.execute_command(instance_ip, cmd, image['username'], environment, hostname=hostname)
