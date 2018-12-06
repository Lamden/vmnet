import os, sys, json
from dockerfile_parse import DockerfileParser
from os.path import join, exists, expanduser, dirname

class Cloud:

    def __init__(self, config_file):
        self.config_file = config_file
        self.dir = dirname(config_file)
        with open(config_file) as f:
            self.config = json.loads(f.read())
        self.setup_working_dir()

    def setup_working_dir(self):
        certs_dir = join(self.dir, 'certs')
        scripts_dir = join(self.dir, 'scripts')
        os.makedirs(certs_dir, exist_ok=True)
        os.makedirs(scripts_dir, exist_ok=True)

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
                    dfp.content = open(join(root, file)).read()
                    for line in dfp.structure:
                        if line['instruction'] == 'RUN':
                            tasks['run'].append(line['value'])
                        elif line['instruction'] == 'CMD':
                            tasks['cmd'] = line['value']

                    image_script = join(self.dir, 'scripts', '{}-setup.sh'.format(file))
                    with open(image_script, 'w+') as f:
                        f.write('echo "Building {} ..."\n'.format(file))
                        f.write('\n'.join(tasks) + '\n')
                        f.write('echo "{} is built successfully!"\n'.format(file))
                    return tasks

    def execute_command(self, instance_ip, cmd, username, environment={}):

        key = paramiko.RSAKey.from_private_key_file(self.key_path)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            print('Sending command "{}" to {}'.format(cmd, instance_ip))
            client.connect(hostname=instance_ip, username=username, pkey=key)

            for c in cmd.split('&&'):
                print('+ '+ c)
                stdin, stdout, stderr = client.exec_command('sudo '+c, get_pty=True, environment=environment)
                output = stdout.read().decode("utf-8")
                if 'E: ' in output:
                    stdin, stdout, stderr = client.exec_command(c, get_pty=True, environment=environment)
                    output = stdout.read().decode("utf-8")
                    if 'E: ' in output:
                        raise Exception(output)
                print(output)

            client.close()

        except Exception as e:
            raise

    def send_file(self, instance_ip, username, fname, file_content):
        key = paramiko.RSAKey.from_private_key_file(self.key_path)
        t = paramiko.Transport((hostname, Port))
        t.connect(key, username)
        sftp = paramiko.SFTPClient.from_transport(t)
        with sftp.open(fname, "w+") as f:
            f.write(file_content)
