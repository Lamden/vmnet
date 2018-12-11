import json, sys, os, time, datetime
from os.path import join, exists, expanduser, dirname
from pprint import pprint
from threading import Thread

from vmnet.cloud.cloud import Cloud

import boto3, botocore
ec2 = boto3.resource('ec2')
ec2_client = boto3.client('ec2')

class AWS(Cloud):

    def __init__(self, config_file):

        super().__init__(config_file)
        self.tasks = {}
        self.threads = []

        if not exists(expanduser('~/.aws/')):
            raise Exception('You must first run "aws configure" to set-up your AWS credentials. Follow these steps from: https://blog.ipswitch.com/how-to-create-an-ec2-instance-with-python')

    def update_security_groups(self, image):
        self.tasks[image['name']] = self.parse_docker_file(image)
        self.create_aws_key_pair(image)
        security_group_id = self.set_aws_security_groups(image)
        return security_group_id

    def build(self, image_name, all):
        print('_' * 128 + '\n')
        print('    Building images on AWS...')
        print('_' * 128 + '\n')
        image_list = list(self.config['aws']['images'].keys()) if all else [image_name]
        for img in image_list:
            image = self.config['aws']['images'][img]
            old_run_ami = self.config['aws']['images'][image['name']].get('run_ami')
            security_group_id = self.update_security_groups(image)
            instances = self.find_aws_instances(image, image['build_ami'])
            if len(instances) == 0:
                instance_ip = self.build_aws_image(image, security_group_id)
            else:
                instance_ip = self.start_aws_image(image, instances[0])
            instance = self.find_aws_instances(image, image['build_ami'])[0]
            self.update_image_code(image, instance_ip, init=True)
            self.run_image_setup_script(image, instance_ip)
            ami_id = self.upload_ami(image, instance)
            self.config['aws']['images'][image['name']]['run_ami'] = ami_id
            self.update_config()
            if old_run_ami:
                self.remove_ami(old_run_ami)

    def up(self, keep_up=False):

        def _update_instance(image, ip, cmd, e={}, init=False):
            try:
                self.update_image_code(image, ip, init=init)
                e.update({'HOST_IP': ip, 'VMNET': 'True'})
                e.update(image.get('environment', {}))
                self.execute_command(ip, cmd, image['username'], e)
            except Exception:
                Cloud.q.put(sys.exc_info())

        if not keep_up: self.down()

        envvars = []
        idx = 0
        for service in self.config['services']:
            for ct in range(service['count']):
                envvars.append({
                    'HOST_NAME': '{}_{}'.format(service['name'], idx)
                })
                idx += 1

        all_instances = []

        for img in self.config['aws']['images']:
            image = self.config['aws']['images'][img]
            image['security_group_id'] = self.update_security_groups(image)
            cmd = self.tasks[image['name']]['cmd']
            instances = self.find_aws_instances(image, image['run_ami'])
            if keep_up and len(instances) > 0:
                for idx, instance in enumerate(instances):
                    all_instances.append(instance)
                    instance_ip = instance['PublicIpAddress']
                    self.threads.append(Thread(target=_update_instance, args=(image, instance_ip, cmd, envvars[idx])))

        if keep_up and len(all_instances) != 0:
            for t in self.threads: t.start()
            for t in self.threads: t.join()
            Cloud._raise_error()
            return

        print('_' * 128 + '\n')
        print('    Brining up services on AWS...')
        print('_' * 128 + '\n')
        instances = []
        for service in self.config['services']:
            image = self.config['aws']['images'][service['image']]
            instances += ec2.create_instances(
                ImageId=image['run_ami'],
                MinCount=service['count'],
                MaxCount=service['count'],
                InstanceType=image['instance_type'],
                KeyName='ec2-{}'.format(image['name']),
                SecurityGroupIds=[image['security_group_id']],
                TagSpecifications=[{
                    'ResourceType': 'instance',
                    'Tags': [{'Key':'Name','Value':'{}:{}:{}-run'.format(
                        image['repo_name'], image['branch'],
                        service['name']
                    )}]
                }]
                # TODO Add regions
            )
        self.wait_for_instances(instances)
        self.find_aws_instances(image, image['run_ami'])
        print('Allocating {} elastic ips for {}...'.format(len(instances), image['name']))
        ips = [self.allocate_elastic_ip(instance) for instance in instances]
        time.sleep(5)
        print('Executing CMD for {}...'.format(image['name']))
        cmd = self.tasks[image['name']]['cmd']
        for idx, instance_ip in enumerate(ips):
            self.threads.append(Thread(target=_update_instance, args=(image, instance_ip, cmd, envvars[idx], True)))

        for t in self.threads: t.start()
        for t in self.threads: t.join()
        print('Done.')

    def down(self):
        print('_' * 128 + '\n')
        print('    Bringing down services on AWS...')
        print('_' * 128 + '\n')
        for img in self.config['aws']['images']:
            image = self.config['aws']['images'][img]
            instances = self.find_aws_instances(image, image['build_ami'])
            print('Terminating the build instance for {}...'.format(image['name']))
            for instance in instances:
                ins = ec2.Instance(instance['InstanceId'])
                ins.terminate()
            if not image.get('run_ami'):
                print('"run_ami" not found for {}, skipping...'.format(image['name']))
                continue
            instances = self.find_aws_instances(image, image['run_ami'])
            print('Dallocating {} elastic ips for {}...'.format(len(instances), image['name']))
            self.deallocate_all_elastic_ips([ins['PublicIpAddress'] for ins in instances])
            print('Terminating {} instances for {}...'.format(len(instances), image['name']))
            for instance in instances:
                ins = ec2.Instance(instance['InstanceId'])
                ins.terminate()

        print('Done.')

    def allocate_elastic_ip(self, instance):
        allocation = ec2_client.allocate_address(Domain='vpc')
        response = ec2_client.associate_address(AllocationId=allocation['AllocationId'],
                                         InstanceId=instance.id)
        return allocation['PublicIp']

    def deallocate_all_elastic_ips(self, public_ips):
        try:
            response = ec2_client.describe_addresses(PublicIps=public_ips)
            for addr in response['Addresses']:
                ec2_client.release_address(AllocationId=addr['AllocationId'])
        except botocore.exceptions.ClientError as e:
            print(e)

    def create_aws_key_pair(self, image):
        image_name = image['name']
        key_file = 'ec2-{}.pem'.format(image_name)
        self.key_path = key_path = join(self.dir, 'certs', key_file)
        if not exists(key_path):
            key_pair = ec2.create_key_pair(KeyName='ec2-{}'.format(image_name))
            with open(key_path, 'w+') as f:
                f.write(str(key_pair.key_material))
            os.chmod(key_path, 0o400)

    def set_aws_security_groups(self, image):
        sg = self.config['aws']['security_groups'][image['security_group']]
        sg_name = sg['name']
        sg_desc = sg.get('description', sg_name)
        permissions = sg['permissions']
        security_group_id = None
        vpc = list(ec2.vpcs.all())
        vpc_id = vpc[0].id
        print('_' * 128 + '\n')
        print('    Setting up security groups for {}...'.format(image['name']))
        print('_' * 128 + '\n')
        print('Creating Security Group "{}"...'.format(sg_name))
        try:
            response = ec2.create_security_group(GroupName=sg_name, Description=sg_desc, VpcId=vpc_id)
            security_group_id = response['GroupId']
        except botocore.exceptions.ClientError as e:
            print(e)
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

                if len(add_permissions) == 0 and len(remove_permissions) == 0:
                    print('No change in securty group permissions settings.')
                    break
                try:
                    if len(remove_permissions):
                        group.revoke_ingress(GroupId=security_group_id, IpPermissions=remove_permissions)
                    if len(add_permissions):
                        data = group.authorize_ingress(GroupId=security_group_id, IpPermissions=add_permissions)
                        print('Successfully set %s using Security Group "%s" in vpc "%s".' % (data, security_group_id, vpc_id))
                except botocore.exceptions.ClientError:
                    raise
                break
        return security_group_id

    def find_aws_instances(self, image, ami_id):
        if not ami_id: return []
        instances = []
        filters = [
            {
                'Name': 'key-name',
                'Values': ['ec2-{}'.format(image['name'])]
            },
            {
                'Name': 'image-id',
                'Values': [ami_id]
            }
        ]
        response = ec2_client.describe_instances(Filters=filters)
        for r in response['Reservations']:
            for ins in r['Instances']:
                if ins['State']['Name'] == 'running':
                    instances.append(ins)
        return instances

    def upload_ami(self, image, instance):

        if instance['State']['Name'] == 'running':
            print('_' * 128 + '\n')
            print('    Creating and uploading image for "{}"...'.format(image['name']))
            print('_' * 128 + '\n')
            vol_id = instance['BlockDeviceMappings'][0]['Ebs']['VolumeId']
            snapshot_id = ec2_client.create_snapshot(
                Description='Snapshot generated by vmnet for {}'.format(vol_id),
                VolumeId=vol_id
            )['SnapshotId']
            while ec2_client.describe_snapshots(Filters=[{'Name':'volume-id', 'Values': [vol_id]}])['Snapshots'][0]['State'] != 'completed':
                print('waiting for snapshot to be created...')
                time.sleep(5)
            ami = ec2_client.create_image(
                InstanceId=instance['InstanceId'],
                Name=image['name'] + str(datetime.datetime.now().strftime("%Y%m%d%H%M")),
                Description='Image generated by vmnet for {}'.format(snapshot_id),
                NoReboot=True,
                BlockDeviceMappings=[{
                    'DeviceName': '/dev/xvda',
                    'Ebs': {
                        'SnapshotId': snapshot_id,
                        'VolumeSize': 8,
                        'VolumeType': 'gp2'
                    },
                }],
            )
            ec2_client.create_tags(Resources=[ami['ImageId']], Tags=[{'Key': 'Name', 'Value': image['name']}])

            print('Tearing down build environment')
            ins = ec2.Instance(instance['InstanceId'])
            ins.terminate()

            print('Building complete ami_id="{}"...'.format(ami['ImageId']))

            return ami['ImageId']

    def remove_ami(self, ami_id):
        try:
            ec2_client.deregister_image(ImageId=ami_id)
        except:
            pass

    def build_aws_image(self, image, security_group_id, instance=None):

        instance = ec2.create_instances(
            ImageId=image['build_ami'],
            MinCount=1,
            MaxCount=1,
            InstanceType=image.get('build_instance_type', image['instance_type']),
            KeyName='ec2-{}'.format(image['name']),
            SecurityGroupIds=[security_group_id],
            TagSpecifications=[{
                'ResourceType': 'instance',
                'Tags': [{'Key':'Name','Value':'{}:{}-build'.format(image['repo_name'], image['branch'])}]
            }]
        )[0]

        self.wait_for_instances([instance])
        time.sleep(10)
        instances = self.find_aws_instances(image, image['build_ami'])
        instance_ip = instances[0]['PublicIpAddress']

        return instance_ip

    def start_aws_image(self, image, instance):
        ins = ec2.Instance(instance['InstanceId'])
        if instance['State']['Name'] == 'stopped':
            ins.start()
            instances = self.wait_for_instances([ins])
            instance_ip = instances[0].public_ip_address
        else:
            instance_ip = instance['PublicIpAddress']
        return instance_ip

    def wait_for_instances(self, instances):
        ready = set()
        instance_ids = set([ins.id for ins in instances])
        print('Waiting for instances: {}'.format(instance_ids))
        while True:
            time.sleep(5)
            print('{}/{} instances is ready: {}'.format(len(ready), len(instance_ids), ready))
            if len(ready) == len(instance_ids):
                return [ec2.Instance(ins_id) for ins_id in instance_ids]
            response = ec2_client.describe_instance_status(InstanceIds=list(instance_ids-ready))
            for status in response['InstanceStatuses']:
                if status['InstanceState']['Name'] == 'running':
                    ready.add(status['InstanceId'])
