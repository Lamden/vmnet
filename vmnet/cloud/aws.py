import json, sys, os, time, datetime, subprocess, logging, uuid, coloredlogs, io, psutil, threading, logging
from os.path import join, exists, expanduser, dirname, splitext, basename
from pprint import pprint
from threading import Thread
from vmnet.cloud.cloud import Cloud
import boto3, botocore, requests
from contextlib import contextmanager

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class AWS(Cloud):

    def __init__(self, config_file=None):

        super().__init__(config_file)
        self.tasks = {}
        self.threads = []
        self.logging = False
        self.profile_name = self.config['aws'].get('profile_name', 'default')
        self.region_name = self.config['aws'].get('region_name', 'us-east-2')
        self.environment = self.config.get('environment', {})

        instance_data_dir = join(self.dir, 'instance_data')
        os.makedirs(instance_data_dir, exist_ok=True)
        self.instance_data_file = join(instance_data_dir, self.config_name + '.json')

        self.launch_begin = datetime.datetime.now()

        self.log_config = self.config['aws'].get('logging', {})

        if os.getenv('VMNET_CLOUD') and self.log_config.get('enabled') == True:
            creds = requests.get('http://169.254.169.254/latest/meta-data/iam/security-credentials/{}'.format(
                self.config['aws']['logging']['arn_name'])).json()
            self.boto_session = boto3.session.Session(
                aws_access_key_id=creds['AccessKeyId'],
                aws_secret_access_key=creds['SecretAccessKey'],
                aws_session_token=creds['Token'],
                region_name=self.region_name
            )
            self.cloudwatch = self.boto_session.client('logs')
            self.log_config.update({
                'log_group': 'vmnet-{}-{}'.format(os.getenv('IAM_NAME'), self.config_name)
            })
            self.keyname = '{}-{}'.format(os.getenv('IAM_NAME'), self.config_name)

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
            self.r53 = self.boto_session.client('route53')
            self.iam_name = self.iam.CurrentUser().arn.rsplit('user/')[-1]
            self.cloudwatch = self.boto_session.client('logs')
            self.log_config.update({
                'log_group': 'vmnet-{}-{}'.format(self.iam_name, self.config_name)
            })
            self.keyname = '{}-{}'.format(self.iam_name, self.config_name)

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
            hostname = None
            self.update_image_code(image, instance_ip, hostname, init=True)
            self.run_image_setup_script(image, instance_ip, hostname)
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

        def _update_instance(image, ip, cmd, hostname, e={}, init=False):
            prefix_colors  = {
                    "green": "\033[92m",
                    "endc": "\033[0m",
                    "error": "\033[91m"
            }
            try:
                self.update_image_code(image, ip, hostname, init=init, update_commands=image.get('update_commands', []), env=e)
                e.update({'HOST_IP': ip, 'VMNET_CLOUD': self.config_name, 'IAM_NAME': self.iam_name})
                e.update(image.get('environment', {}))
                self.execute_command(ip, cmd, image['username'], e, hostname=hostname)
            except Exception as e:
                print("{color}[THREAD ERROR {host}] {err}{endc}".format(
                    color=prefix_colors['error'],
                    host=hostname,
                    err=e,
                    endc=prefix_colors['endc']
                ))
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

        self.set_log_groups()

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
                service = [ x['Value'] for x in instance['Tags'] if x['Key'] == 'Name' ][0].split(':')[-1].split('-')[0]
                hostname = '{}_{}'.format(service, instance['AmiLaunchIndex'])
                env = {
                    'HOST_NAME': hostname
                }
                if self.config['aws'].get('use_dns', ''):
                    self.dns_records([instance], image, service, 'UPSERT')
                    if self.config['aws']['dns_configuration'].get('use_ssl', ''):
                        env['SSL_ENABLED'] = 'True'
                        env['TYPEREGEX'] = "'^(" + '|'.join(self.config['aws']['dns_configuration']['ssl_nodes']) + ")$'"
                    if self.config['aws']['dns_configuration'].get('subnet_prefix', ''):
                        env['SUBNET_PREFIX'] = self.config['aws']['dns_configuration']['subnet_prefix']
                    env['DNS_NAME'] = self.config['aws']['dns_configuration']['domain_name']
                self.all_instances.append(instance)
                cmd = self.tasks[image['name']]['cmd']
                self.threads.append(Thread(target=_update_instance, name=hostname, args=(image, instance['PublicIpAddress'], cmd, hostname, env)))

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
            service = [s for s in self.config['services'] if s['image'] == image['name']][0]
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
            if self.config['aws'].get('use_dns') and destroy:
                self.dns_records(instances, image, service, 'DELETE');
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

    def _load_instance_data(self):
        """
        Load in the instance data file if it exists

        Args:
            N/A (all requirements internal to class)

        Returns:
            instance_data (list): A list of instance data loaded from the instance_data file, if not exists, empty list

        Raises:
            N/A
        """
        if exists(self.instance_data_file):
            with open(self.instance_data_file) as f:
                return json.loads(f.read())
        return []

    def dns_records(self, instances, image, service, operation):
        """
        Creates DNS records for EIPs if feature is enabled

        Args:
            instances (list): A list of instance information returned from the boto3 ec2 call 'describe instances'
            image (dict):     A section of the configuration dedicated to the runtime configuration of different
                              types of nodes
            service (str):    The name of the service being brought up (e.g. masternode, delegate, etc)
            operation (str):  The operation to take on the record, options are 'UPSERT', 'CREATE', 'DELETE'

        Returns:
            N/A

        Raises:
            ValueError:       If the service is incorrectly specified
            ValueError:       Could not find domain name in route53 for account
        """
        if not self.config['aws']['use_elastic_ips']:
            print("WARNING (create_dns_records): Generating DNS records for instances without elastic ip addresses. \
                    Records are not guaranteed to stay active for any extended period of time.")

        # Load in expected parameters at beginning of function to fail fast in the case of misconfiguration
        dns_config = self.config['aws']['dns_configuration']
        domain_name = dns_config['domain_name']
        record_type = dns_config.get('record_type', 'A')
        dns_service = dns_config.get('service', 'route53')
        subnet_prefix = dns_config.get('subnet_prefix', '')
        ttl = dns_config.get("TTL", 20)
        if subnet_prefix:
            subnet_prefix += '-'
        if dns_service != 'route53':
            raise ValueError("Only DNS service type 'route53' supported at this time")

        print("Creating DNS records for image {} on domain {}".format(image['name'], domain_name))

        # Get hosted_zone from route53 and validate we got the correct one
        hosted_zone = self.r53.list_hosted_zones_by_name(DNSName=domain_name)['HostedZones'][0]
        if domain_name not in hosted_zone['Name']:
            raise ValueError("Was unable to retrieve domain name {}. Are you sure you're running in the correct AWS account?".format(domain_name))
        hzid = hosted_zone['Id']

        #
        instance_data = self._load_instance_data()
        for instance in instances:
            changebatch = {
                'Comment': 'Procedurally generated record for service {} index {}'.format(service, instance['AmiLaunchIndex']),
                'Changes': [
                    {
                        'Action': operation,
                        'ResourceRecordSet': {
                            'Name': '{}{}{}.{}'.format(subnet_prefix, service, instance['AmiLaunchIndex'], domain_name),
                            'Type': record_type,
                            'TTL': ttl,
                            'ResourceRecords': [
                                {
                                    "Value": instance['PublicIpAddress']
                                }
                            ]
                        }
                    }
                ]
            }
            print(json.dumps(changebatch, indent=2))
            self.r53.change_resource_record_sets(
                HostedZoneId = hzid,
                ChangeBatch = changebatch
            )


    def allocate_elastic_ips(self, instances, image):
        print('{} elastic IPs in total are needed for {}...'.format(len(instances), image['name']))

        instance_data = self._load_instance_data()
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

    def set_log_groups(self):
        print('_' * 128 + '\n')
        print('    Creating Log Group {}...'.format(self.log_config['log_group']))
        print('_' * 128 + '\n')
        try:
            self.cloudwatch.create_log_group(logGroupName=self.log_config['log_group'])
            print('Created log group "{}"'.format(self.log_config['log_group']))
        except:
            print('Log group "{}" already exist'.format(self.log_config['log_group']))

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
            print('waiting for snapshot to be created...')
            while self.ec2_client.describe_snapshots(Filters=[{'Name':'volume-id', 'Values': [vol_id]}])['Snapshots'][0]['State'] != 'completed':
                time.sleep(5)
            print('done.')

            print('Creating image...')
            while True:
                try:
                    ami = self.ec2_client.create_image(
                        InstanceId=instance['InstanceId'],
                        Name=image['name'] + str(self.launch_begin.strftime("%Y%m%d%H%M")),
                        Description='Image generated by vmnet for {}-{}'.format(image['name'], snapshot_id),
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
                    break
                except:
                    time.sleep(5)
            self.ec2_client.create_tags(Resources=[ami['ImageId']], Tags=[{'Key': 'Name', 'Value': image['name']}])

            print('Waiting for AMI to be created...')
            while self.ec2_client.describe_images(Filter=[{'image-id': ami['ImageId']}])['Images'][0]['State'] != 'available':
                time.sleep(5)
            print('done.')

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

import watchtower, logging

class AWSCloudWatchHandler(watchtower.CloudWatchLogHandler):
    def __init__(self, name):
        aws = AWS(self._find_config_file())
        if aws.config.get('deployment_mode') == 'production':
            logging.raiseExceptions = False
        super().__init__(
            log_group=aws.log_config['log_group'], stream_name="{}-{}".format(os.getenv('HOST_NAME'), name),
            boto3_session=aws.boto_session,
            send_interval=aws.log_config.get('interval', 60),
            create_log_group=False, use_queues=False)

    def _find_config_file(self):
        config_file = None
        for root, dirs, files in os.walk(os.getcwd()):
            for f in files:
                if f == os.getenv('VMNET_CLOUD', '') + '.json' and 'instance_data' not in root:
                    config_file = os.path.join(root, f)
                    break
            if config_file: break
        return config_file
