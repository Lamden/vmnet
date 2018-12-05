from vmnet.cloud.aws import AWS

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Run your project on AWS')
    parser.add_argument('--deploy', '-d', help='Currently only support AWS', default='aws')
    parser.add_argument('--config', '-c', help='Configuration JSON', required=True)
    parser.add_argument('--build', '-b', help='Build the images specified in the config', action='store_true')
    args = parser.parse_args()
    if args.deploy == 'aws':
        AWS(args.config, args.build)
    else:
        parser.print_help(sys.stderr)
