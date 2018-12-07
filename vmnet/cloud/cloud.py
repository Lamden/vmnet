import os, sys, json, paramiko, socket, queue
from dockerfile_parse import DockerfileParser
from os.path import join, exists, expanduser, dirname

class Cloud:

    q = queue.Queue()

    def __init__(self, config_file):
        self.config_file = config_file
        self.dir = dirname(config_file)
        with open(config_file) as f:
            self.config = json.loads(f.read())
        self.setup_working_dir()

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
        certs_dir = join(self.dir, 'certs')
        os.makedirs(certs_dir, exist_ok=True)

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

    def execute_command(self, instance_ip, cmd, username, environment={}, immediate_raise=False, ignore_q=False):

        def _has_err(out):
            if ignore_q: return False
            return out.channel.recv_exit_status() == 1

        key = paramiko.RSAKey.from_private_key_file(self.key_path)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            print('Sending commands to {}'.format(instance_ip))
            client.connect(hostname=instance_ip, username=username, pkey=key)

            for c in cmd.split('&&'):
                print('+ '+ c)
                stdin, stdout, stderr = client.exec_command('sudo '+c, get_pty=True, environment=environment)
                output = stdout.read().decode("utf-8")

                if _has_err(stdout):
                    if immediate_raise:
                        raise Exception(output)
                    else:
                        stdin, stdout, stderr = client.exec_command(c, get_pty=True, environment=environment)
                        output = stdout.read().decode("utf-8")
                        if _has_err(stdout):
                            raise Exception(output)

                print(output)

            client.close()

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
        os.system('rm {}'.format(fname))
        print('\ndone.\n')

    def update_image_code(self, image, instance_ip):
        print('_' * 128 + '\n')
        print('    Cloning repository into instance with ip {}'.format(instance_ip))
        print('_' * 128 + '\n')
        for cmd in [
            'git init',
            'git remote add origin {}'.format(image['repo_url']),
            'git fetch origin',
            'git checkout -b {} --track origin/{}'.format(image['branch'], image['branch']),
            'git pull'
        ]:
            self.execute_command(instance_ip, cmd, image['username'], image.get('environment', {}))

    def run_image_setup_script(self, image, instance_ip):
        print('_' * 128 + '\n')
        print('    Running setup scripts from Docker Image "{}" on instance with ip {}'.format(image['name'], instance_ip))
        print('_' * 128 + '\n')
        for cmd in self.tasks[image['name']]['run']:
            self.execute_command(instance_ip, cmd, image['username'], image.get('environment', {}))
