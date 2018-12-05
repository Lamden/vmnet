import json, sys, os, time, datetime
from os.path import join, exists, expanduser, dirname
from pprint import pprint

from vmnet.cloud.cloud import Cloud

import boto3, botocore, paramiko
ec2 = boto3.resource('ec2')
ec2_client = boto3.client('ec2')


class AWS(Cloud):

    def __init__(self, config_file, build=False, up=False, down=False, reload=False):

        super().__init__(config_file)

        if not exists(expanduser('~/.aws/')):
            raise Exception('You must first run "aws configure" to set-up your AWS credentials. Follow these steps from: https://blog.ipswitch.com/how-to-create-an-ec2-instance-with-python')

        for image in self.config['images']:

            image['tasks'] = self.parse_docker_file(image)
            self.create_aws_key_pair(image)
            security_group_id = self.set_aws_security_groups(image)

            if build or reload:
                instance = self.find_instance(image, start=True)
            else:
                instance = self.find_instance(image)

            if build:
                instance = self.build_aws_image(image, security_group_id, instance)
                ami_id = self.upload_ami(image, instance)
            elif reload:
                self.update_aws_image_code(image, instance)

    def create_aws_key_pair(self, image):
        image_name = image['name']
        key_file = 'ec2-{}.pem'.format(image_name)
        self.key_path = key_path = join(self.dir, 'certs', key_file)
        if not exists(key_path):
            with open(key_path, 'w+') as f:
                key_pair = ec2.create_key_pair(KeyName='ec2-{}'.format(image_name))
                f.write(str(key_pair.key_material))
                os.chmod(key_path, 0o400)

    def set_aws_security_groups(self, image):
        # SECURITY GROUPS
        sg_name = self.config['security_group']['name']
        sg_desc = self.config['security_group'].get('description', sg_name)
        permissions = self.config['security_group']['permissions']
        security_group_id = None
        vpc = list(ec2.vpcs.all())
        vpc_id = vpc[0].id
        print('#' * 64)
        print('    Setting up security groups...')
        print('#' * 64)
        print('Creating Security Group "{}"...'.format(sg_name))
        try:
            response = ec2.create_security_group(GroupName=sg_name, Description=sg_desc, VpcId=vpc_id)
            security_group_id = response['GroupId']
        except botocore.exceptions.ClientError:
            # Already exist skipping step
            pass
        print('Done.')
        print('Setting permissions for Security Group "{}"...'.format(sg_name))
        for group in list(vpc[0].security_groups.all()):
            if group.group_name == sg_name:
                security_group_id = group.id

                add_permissions = []
                remove_permissions = []
                for p in group.ip_permissions:
                    if (p['FromPort'], p['ToPort']) not in [(_p['FromPort'], _p['ToPort']) for _p in permissions]:
                        remove_permissions.append(p)
                for p in permissions:
                    if (p['FromPort'], p['ToPort']) not in [(_p['FromPort'], _p['ToPort']) for _p in group.ip_permissions]:
                        add_permissions.append(p)

                if len(add_permissions) == 0 and len(remove_permissions):
                    print('No change in securty group permissions settings.')
                    break
                try:
                    group.revoke_ingress(GroupId=security_group_id, IpPermissions=remove_permissions)
                    data = group.authorize_ingress(GroupId=security_group_id, IpPermissions=add_permissions)
                    print('Successfully set %s using Security Group "%s" in vpc "%s".' % (data, security_group_id, vpc_id))
                except botocore.exceptions.ClientError:
                    print('Permissions in Security Group "%s" in vpc "%s" had already been set.' % (security_group_id, vpc_id))
                break
        return security_group_id

    def find_instance(self, image, start=False):
        response = ec2_client.describe_instances(Filters=[
            {
                'Name': 'key-name',
                'Values': ['ec2-{}'.format(image['name'])]
            },
            {
                'Name': 'image-id',
                'Values': [image['build_ami']]
            }
        ])

        for r in response['Reservations']:
            for ins in r['Instances']:
                if ins['State']['Name'] == 'running':
                    return ins
                elif start:
                    _ins = ec2.Instance(ins['InstanceId']).start()
                    self.wait_for_instances([_ins])

    def upload_ami(self, image, instance):

        if instance['State']['Name'] == 'running':
            print('#' * 64)
            print('    Creating and uploading image for "{}"...'.format(image['name']))
            print('#' * 64)
            ami = ec2_client.create_image(
                InstanceId=instance['InstanceId'],
                Name=image['name'] + str(datetime.datetime.now().strftime("%Y%m%d%H%M")),
                Description='Image generated by vmnet',
                NoReboot=True,
            )
            ec2_client.create_tags(Resources=[ami['ImageId']], Tags=[{'Key': 'Name', 'Value': image['name']}])

            print('#' * 64)
            print('    Tearing down build environment')
            print('#' * 64)
            ins = ec2.Instance(instance['InstanceId'])
            ins.stop()

            print('#' * 64)
            print('    Building complete ami_id="{}"...'.format(ami['ImageId']))
            print('#' * 64)

            return ami['ImageId']

    def build_aws_image(self, image, security_group_id, instance=None):

        if not instance:
            instance = ec2.create_instances(
                ImageId=image['build_ami'],
                MinCount=1,
                MaxCount=1,
                InstanceType=image['instance_type'],
                KeyName='ec2-{}'.format(image['name']),
                SecurityGroupIds=[security_group_id]
            )[0]
            self.wait_for_instances([instance])
            instance_ip = instance.public_ip_address
        else:
            instance_ip = instance.get('PublicIpAddress')

        self.update_aws_image_code(image)

        print('#' * 64)
        print('    Running setup scripts from Docker Image "{}" on AWS instance'.format(image['name']))
        print('#' * 64)
        for cmd in image['tasks']['run']:
            self.execute_command(instance_ip, cmd, image['username'], image.get('environment', {}))

        return instance

    def execute_command(self, instance_ip, cmd, username, environment={}):

        key = paramiko.RSAKey.from_private_key_file(self.key_path)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            print('Sending command "{}" to {}'.format(cmd, instance_ip))
            client.connect(hostname=instance_ip, username=username, pkey=key)

            for c in cmd.split('&&'):
                print('+ '+ c)
                stdin, stdout, stderr = client.exec_command(c, get_pty=True, environment=environment)
                output = stdout.read().decode("utf-8")
                if 'Permission denied' in output:
                    stdin, stdout, stderr = client.exec_command('sudo '+c, get_pty=True, environment=environment)
                    output = stdout.read().decode("utf-8")
                print(output)

            client.close()

        except Exception as e:
            raise

    def update_aws_image_code(self, image, instance):




        print('#' * 64)
        print('    Cloning repository into AWS instance')
        print('#' * 64)
        for cmd in [
            'rm -rf ./*',
            'git clone --single-branch -b {} {} .tmp_repo && echo "cloned."'.format(image['branch'], image['repo_url']),
            'mv .tmp_repo/* ./',
            'rm -rf ./.tmp_repo'
        ]:
            self.execute_command(instance_ip, cmd, image['username'], image.get('environment', {}))

    def wait_for_instances(self, instances):
        ready = []
        while True:
            for instance in instances:
                instance.reload()
                if instance.state == 'running':
                    ready.append(instance)
                    if len(ready) == len(instances):
                        return
            time.sleep(5)
