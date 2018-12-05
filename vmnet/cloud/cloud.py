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
