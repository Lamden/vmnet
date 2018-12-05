from vmnet.cloud.aws import AWS

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Run your project on AWS')
    parser.add_argument('--platform', '-p', help='Currently only support AWS', default='aws')
    parser.add_argument('--config', '-c', help='Configuration JSON', required=True)
    parser.add_argument('--build', '-b', help='Build the images specified in the config', action='store_true')
    parser.add_argument('--up', '-u', help='Bring up the services and get it ready for vmnet to use', action='store_true')
    parser.add_argument('--down', '-d', help='Stop and bring down the services', action='store_true')
    parser.add_argument('--reload', '-r', help='Reload the code in the services', action='store_true')
    args = parser.parse_args()
    if args.platform == 'aws':
        AWS(args.config, build=args.build, up=args.up, down=args.down, reload=args.reload)
    else:
        parser.print_help(sys.stderr)
