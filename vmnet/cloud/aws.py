import json, sys, os, time, datetime, subprocess, logging, uuid, coloredlogs, io
from os.path import join, exists, expanduser, dirname, splitext, basename
from pprint import pprint
from threading import Thread
from vmnet.cloud.cloud import Cloud
import boto3, botocore, requests

class AWS(Cloud):

    def __init__(self, config_file=None):

        super().__init__(config_file)
        self.tasks = {}
        self.threads = []
        self.logging = False
        self.profile_name = self.config['aws'].get('profile_name', 'default')
        self.region_name = self.config['aws'].get('region_name', 'us-east-2')
        self.keyname = '{}-{}'.format(self.profile_name, self.config_name)
        self.environment = self.config.get('environment', {})

        instance_data_dir = join(self.dir, 'instance_data')
        os.makedirs(instance_data_dir, exist_ok=True)
        self.instance_data_file = join(instance_data_dir, self.config_name + '.json')

        if os.getenv('VMNET_CLOUD') and self.config['aws'].get('logging'):
            import s3fs
            logging.getLogger('s3fs.core').setLevel(logging.WARNING)
            creds = requests.get('http://169.254.169.254/latest/meta-data/iam/security-credentials/{}'.format(self.config['aws']['logging']['arn_name'])).json()
            self.boto_session = boto3.session.Session(
                aws_access_key_id=creds['AccessKeyId'],
                aws_secret_access_key=creds['SecretAccessKey'],
                aws_session_token=creds['Token'],
                region_name=self.region_name
            )
            self.s3 = self.boto_session.resource('s3')
            self.fs = s3fs.S3FileSystem(session=self.boto_session)
            self.log_config = {
                'interval': 1800,
                'bucket': 'vmnet-{}-{}'.format(os.getenv('IAM_NAME'), self.config_name)
            }
            self.log_config.update(self.config['aws'].get('logging', {}))
        elif not exists(expanduser('~/.aws/')):
            raise Exception('You must first run "aws configure" to set-up your AWS credentials. Follow these steps from: https://blog.ipswitch.com/how-to-create-an-ec2-instance-with-python')
        else:
            self.boto_session = boto3.session.Session(
                profile_name=self.profile_name,
                region_name=self.region_name
            )
            self.ec2 = self.boto_session.resource('ec2')
            self.ec2_client = self.boto_session.client('ec2')
            self.iam = self.boto_session.resource('iam')
            self.iam_name = self.iam.CurrentUser().arn.rsplit('user/')[-1]

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
            instances = self.find_aws_instances(image, 'build')
            if len(instances) == 0:
                instance_ip = self.build_aws_image(image, security_group_id)
            else:
                instance_ip = self.start_aws_image(image, instances[0])
            instance = self.find_aws_instances(image, 'build')[0]
            self.update_image_code(image, instance_ip, init=True)
            self.run_image_setup_script(image, instance_ip)
            ami_id = self.upload_ami(image, instance)
            self.config['aws']['images'][image['name']]['run_ami'] = ami_id
            self.update_config()
            if old_run_ami:
                self.remove_ami(old_run_ami)

    def ssh(self, service_name):
        sn, idx = service_name.rsplit('_') if len(service_name.rsplit('_')) == 2 else (service_name, 0)
        idx = int(idx)
        try: service = [s for s in self.config['services'] if s['name'] == sn][0]
        except: raise Exception('No service named "{}"'.format(sn))
        if idx+1 > service['count']:
            raise Exception('There are only {} nodes in {}'.format(service['count'], sn))
        image = self.config['aws']['images'][service['image']]
        instance = self.find_aws_instances(image, 'run', [{
            'Name': 'tag:Name',
            'Values': ['{}:{}:{}-run'.format(image['repo_name'], image['branch'], service['name'])]
        },{
            'Name': 'launch-index',
            'Values': [str(idx)]
        }])[0]
        cert = join(self.certs_dir, '{}.pem'.format(self.keyname))
        url = '{}@{}'.format(image['username'], instance['PublicDnsName'])
        ssh = subprocess.Popen(["ssh", "-i", cert, url],
                       shell=False)
        ssh.wait()

    def up(self, keep_up=False, logging=False, service_name=None):

        self.logging = logging

        def _update_instance(image, ip, cmd, e={}, init=False):
            try:
                self.update_image_code(image, ip, init=init, update_commands=image.get('update_commands', []))
                e.update({'HOST_IP': ip, 'VMNET_CLOUD': self.config_name, 'IAM_NAME': self.iam_name})
                e.update(image.get('environment', {}))
                self.execute_command(ip, cmd, image['username'], e)
            except Exception:
                Cloud.q.put(sys.exc_info())

        def _create_instance(image, service, count):
            return self.ec2.create_instances(
                ImageId=image['run_ami'],
                MinCount=count,
                MaxCount=count,
                InstanceType=image['instance_type'],
                KeyName=self.keyname,
                SecurityGroupIds=[image['security_group_id']],
                TagSpecifications=[{
                    'ResourceType': 'instance',
                    'Tags': [{'Key':'Name','Value':'{}:{}:{}-run'.format(
                        image['repo_name'], image['branch'],
                        service['name']
                    )}]
                }],
                IamInstanceProfile={
                    'Arn': self.config['aws']['logging']['arn_id']
                },
                # TODO Add regions
            )

        if not keep_up: self.down()

        for img in self.config['aws']['images']:
            image = self.config['aws']['images'][img]
            image['security_group_id'] = self.update_security_groups(image)

        print('_' * 128 + '\n')
        print('    Brining up services on AWS...')
        print('_' * 128 + '\n')

        self.all_instances = []

        if service_name:
            sn, idx = service_name.rsplit('_') if len(service_name.rsplit('_')) == 2 else (service_name, 0)
            service = [s for s in self.config['services'] if s['name'] == sn][0]
            image = self.config['aws']['images'][service['image']]
            instances = self.find_aws_instances(image, 'run', [{
                'Name': 'launch-index',
                'Values': [idx]
            }])
            if len(instances) == 0:
                self.all_instances += _create_instance(image, service, 1)
        else:
            for service in self.config['services']:
                image = self.config['aws']['images'][service['image']]
                instances = self.find_aws_instances(image, 'run')
                instances = [ins for ins in instances if service['name'] in ins['Tags'][0]['Value']]
                print('{}/{} instances are up for "{}".'.format(len(instances), service['count'], service['name']))
                missing_count = service['count'] - len(instances)
                if missing_count > 0:
                    print('Creating {} new instances...'.format(missing_count))
                    self.all_instances += _create_instance(image, service, missing_count)
                print('Ok.')

        self.wait_for_instances(self.all_instances)
        self.all_instances = []

        for img in self.config['aws']['images']:
            image = self.config['aws']['images'][img]
            instances = self.find_aws_instances(image, 'run')
            if self.config['aws'].get('use_elastic_ips'):
                self.allocate_elastic_ips(instances, image)
            instances = self.find_aws_instances(image, 'run')
            for instance in instances:
                self.all_instances.append(instance)
                cmd = self.tasks[image['name']]['cmd']
                service = [s for s in self.config['services'] if s['image'] == image['name']][0]
                self.threads.append(Thread(target=_update_instance, args=(image, instance['PublicIpAddress'], cmd, {
                    'HOST_NAME': '{}_{}'.format(service['name'], int(instance['AmiLaunchIndex'])+1)
                })))

        self.save_instance_data(self.all_instances)
        for t in self.threads: t.start()
        for t in self.threads: t.join()
        Cloud._raise_error()
        print('_' * 128 + '\n')
        print('    AWS instances are now ready for use')
        print('_' * 128 + '\n')

    def down(self, destroy=False, service_name=None):
        print('_' * 128 + '\n')
        print('    Bringing down services on AWS...')
        print('_' * 128 + '\n')
        if service_name:
            sn, idx = service_name.rsplit('_') if len(service_name.rsplit('_')) == 2 else (service_name, 0)
            img_name = [s['image'] for s in self.config['services'] if s['name'] == sn][0]
        for img in self.config['aws']['images']:
            image = self.config['aws']['images'][img]
            instances = self.find_aws_instances(image, mode='build')
            print('Terminating the build instance for {}...'.format(image['name']))
            for instance in instances:
                ins = self.ec2.Instance(instance['InstanceId'])
                ins.terminate()
            if not image.get('run_ami'):
                print('"run_ami" not found for {}, skipping...'.format(image['name']))
                continue
            if service_name:
                if img_name != image['name']: continue
                instances = self.find_aws_instances(image, 'run', [{
                    'Name': 'launch-index',
                    'Values': [idx]
                }])
            else:
                instances = self.find_aws_instances(image, mode='run')
            if self.config['aws'].get('use_elastic_ips'):
                self.deallocate_all_elastic_ips([ins['PublicIpAddress'] for ins in instances], image, release=destroy)
            print('Terminating {} instances for {}...'.format(len(instances), image['name']))
            for instance in instances:
                ins = self.ec2.Instance(instance['InstanceId'])
                ins.terminate()
        if destroy:
            self.remove_instance_data()
        print('Done.')

    def save_instance_data(self, instances):
        if exists(self.instance_data_file): return
        with open(self.instance_data_file, 'w+') as f:
            f.write(json.dumps([{
                key: instance[key] for key in instance if key in \
                    ('PublicIpAddress', 'Tags', 'AmiLaunchIndex')
            } for instance in instances], indent=4))
        print('Saved instance data to {}'.format(self.instance_data_file))

    def remove_instance_data(self):
        if exists(self.instance_data_file):
            print('Removing instance data file')
            os.remove(self.instance_data_file)

    def allocate_elastic_ips(self, instances, image):
        print('{} elastic IPs in total are needed for {}...'.format(len(instances), image['name']))

        instance_data = []
        if exists(self.instance_data_file):
            with open(self.instance_data_file) as f:
                instance_data = json.loads(f.read())
        addrs = self.ec2_client.describe_addresses()['Addresses']
        ins_ids = set([addr.get('InstanceId') for addr in addrs])
        if len(instance_data) == 0:
            for instance in instances:
                 print('Requesting a new IP for {}'.format(instance['InstanceId']))
                 allocation = self.ec2_client.allocate_address(Domain='vpc')
                 self.ec2_client.associate_address(AllocationId=allocation['AllocationId'],
                                                  InstanceId=instance['InstanceId'])
        else:
            for instance in instances:
                for ins in instance_data:
                    if ins['Tags'] == instance['Tags'] and ins['AmiLaunchIndex'] == instance['AmiLaunchIndex']:
                        if instance['InstanceId'] in ins_ids:
                            print('No change for {}.'.format(instance['InstanceId']))
                            break
                        else:
                            print('Associating IP {} to {}'.format(ins['PublicIpAddress'], instance['InstanceId']))
                            self.ec2_client.associate_address(PublicIp=ins['PublicIpAddress'],
                                                             InstanceId=instance['InstanceId'])
                            break

        return instances

    def deallocate_all_elastic_ips(self, public_ips, image, release=False):
        if len(public_ips) == 0: return
        mode = 'Releasing' if release else 'Disassociating'
        print('{} {} elastic ips for {}...'.format(mode, len(public_ips), image['name']))
        try:
            response = self.ec2_client.describe_addresses(PublicIps=public_ips)
            for addr in response['Addresses']:
                if release:
                    self.ec2_client.release_address(AllocationId=addr['AllocationId'])
                else:
                    self.ec2_client.disassociate_address(PublicIp=addr['PublicIp'])
        except botocore.exceptions.ClientError as e:
            print(e)

    def create_aws_key_pair(self, image):
        image_name = image['name']
        key_file = '{}.pem'.format(self.keyname)
        self.key_path = key_path = join(self.dir, 'certs', key_file)
        if not exists(key_path):
            key_pair = self.ec2.create_key_pair(KeyName='{}'.format(self.keyname))
            with open(key_path, 'w+') as f:
                f.write(str(key_pair.key_material))
            os.chmod(key_path, 0o400)
        return key_path

    def set_aws_security_groups(self, image):
        sg = self.config['aws']['security_groups'][image['security_group']]
        sg_name = sg['name']
        sg_desc = sg.get('description', sg_name)
        permissions = sg['permissions']
        security_group_id = None
        vpc = list(self.ec2.vpcs.all())
        vpc_id = vpc[0].id
        print('_' * 128 + '\n')
        print('    Setting up security groups for {}...'.format(image['name']))
        print('_' * 128 + '\n')
        print('Creating Security Group "{}"...'.format(sg_name))
        try:
            response = self.ec2.create_security_group(GroupName=sg_name, Description=sg_desc, VpcId=vpc_id)
            security_group_id = response.id
        except botocore.exceptions.ClientError as e:
            if 'already exists' not in str(e):
                raise

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

    def find_aws_instances(self, image, mode, additional_filters=[], return_all=False):
        instances = []
        filters = [
            {
                'Name': 'key-name',
                'Values': [self.keyname]
            },
            {
                'Name': 'image-id',
                'Values': [image['{}_ami'.format(mode)]]
            }
        ] + additional_filters
        response = self.ec2_client.describe_instances(Filters=filters)
        for r in response['Reservations']:
            for ins in r['Instances']:
                if not ins.get('Tags'): continue
                if ins['Tags'][0]['Value'].endswith(mode):
                    if return_all:
                        instances.append(ins)
                    elif ins['State']['Name'] == 'running':
                        instances.append(ins)
        return instances

    def upload_ami(self, image, instance):

        if instance['State']['Name'] == 'running':
            print('_' * 128 + '\n')
            print('    Creating and uploading image for "{}"...'.format(image['name']))
            print('_' * 128 + '\n')
            vol_id = instance['BlockDeviceMappings'][0]['Ebs']['VolumeId']
            snapshot_id = self.ec2_client.create_snapshot(
                Description='Snapshot generated by vmnet for {}'.format(vol_id),
                VolumeId=vol_id
            )['SnapshotId']
            while self.ec2_client.describe_snapshots(Filters=[{'Name':'volume-id', 'Values': [vol_id]}])['Snapshots'][0]['State'] != 'completed':
                print('waiting for snapshot to be created...')
                time.sleep(5)
            ami = self.ec2_client.create_image(
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
            self.ec2_client.create_tags(Resources=[ami['ImageId']], Tags=[{'Key': 'Name', 'Value': image['name']}])

            print('Tearing down build environment')
            ins = self.ec2.Instance(instance['InstanceId'])
            ins.terminate()

            print('Building complete ami_id="{}"...'.format(ami['ImageId']))

            return ami['ImageId']

    def remove_ami(self, ami_id):
        try:
            self.ec2_client.deregister_image(ImageId=ami_id)
        except:
            pass

    def build_aws_image(self, image, security_group_id, instance=None):

        instance = self.ec2.create_instances(
            ImageId=image['build_ami'],
            MinCount=1,
            MaxCount=1,
            InstanceType=image.get('build_instance_type', image['instance_type']),
            KeyName=self.keyname,
            SecurityGroupIds=[security_group_id],
            TagSpecifications=[{
                'ResourceType': 'instance',
                'Tags': [
                    {'Key':'Name','Value':'{}:{}-build'.format(image['repo_name'], image['branch'])}
                ]
            }]
        )[0]

        self.wait_for_instances([instance])
        time.sleep(10)
        instances = self.find_aws_instances(image, 'build')
        instance_ip = instances[0]['PublicIpAddress']

        return instance_ip

    def start_aws_image(self, image, instance):
        ins = self.ec2.Instance(instance['InstanceId'])
        if instance['State']['Name'] == 'stopped':
            ins.start()
            instances = self.wait_for_instances([ins])
            instance_ip = instances[0].public_ip_address
        else:
            instance_ip = instance['PublicIpAddress']
        return instance_ip

    def wait_for_instances(self, instances):
        if len(instances) == 0: return
        ready = set()
        instance_ids = set([ins.id for ins in instances])
        print('Waiting for instances: {}'.format(instance_ids))
        while True:
            time.sleep(5)
            print('{}/{} instances is ready: {}'.format(len(ready), len(instance_ids), ready))
            if len(ready) == len(instance_ids):
                return [self.ec2.Instance(ins_id) for ins_id in instance_ids]
            response = self.ec2_client.describe_instance_status(InstanceIds=list(instance_ids-ready))
            for status in response['InstanceStatuses']:
                if status['InstanceState']['Name'] == 'running':
                    ready.add(status['InstanceId'])

class S3Handler(logging.StreamHandler):

    is_setup = False

    def __init__(self, *args, **kwargs):
        config_file = None
        for root, dirs, files in os.walk(os.getcwd()):
            for f in files:
                if f == os.getenv('VMNET_CLOUD', '') + '.json' and 'instance_data' not in root:
                    config_file = os.path.join(root, f)
                    break
            if config_file: break
        self.aws = AWS(config_file)
        self.log_captor = io.StringIO()
        super().__init__(self.log_captor, *args, **kwargs)
        format = '%(asctime)s.%(msecs)03d %(name)s[%(process)d][%(processName)s] <{}> %(levelname)-2s %(message)s'.format(os.getenv('HOST_NAME', 'Node'))
        self.setFormatter(
            coloredlogs.ColoredFormatter(format)
        )
        if not S3Handler.is_setup:
            S3Handler.is_setup = True
            t = Thread(target=self._log_to_s3)
            t.start()

    def _log_to_s3(self):
        fname = datetime.datetime.fromtimestamp(int(time.time() / self.aws.log_config['interval']) * self.aws.log_config['interval']).strftime("%Y_%m_%d_%H_%M_%S")
        log_file = '{}/{}-{}'.format(self.aws.log_config['bucket'], os.getenv('HOST_NAME'), fname)
        try: self.aws.s3.create_bucket(
            Bucket=self.aws.log_config['bucket'],
            CreateBucketConfiguration={'LocationConstraint': self.aws.boto_session.region_name}
        )
        except: pass
        try: bucket = self.aws.fs.ls(self.aws.log_config['bucket'])
        except: bucket = []
        while True:
            content = self.log_captor.getvalue().encode()
            if content:
                if log_file in bucket:
                    with self.aws.fs.open(log_file, 'rb') as f:
                        content = f.read() + content
                if len(content) == 0: return
                with self.aws.fs.open(log_file, 'wb') as f:
                    f.write(content)
            time.sleep(1)
