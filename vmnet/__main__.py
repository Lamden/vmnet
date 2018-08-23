#!/usr/bin/env python3

import argparse
from vmnet.launch import launch

def main():
    parser = argparse.ArgumentParser(description='Run your project on a docker bridge network')
    parser.add_argument('--config_file', '-f', help='.yml file which specifies the image, contexts and build of your services', required=True)
    parser.add_argument('--test_name', '-t', help='name of your test', default='testname')
    parser.add_argument('--clean', '-c', action='store_true', help='remove all containers')
    parser.add_argument('--destroy', '-d', action='store_true', help='remove all images and containers listed in the config')
    parser.add_argument('--build', '-b', action='store_true', help='builds the image and does not run the container')
    parser.add_argument('--stop', '-s', action='store_true', help='stops and removes the containers for the specified config file')
    args = parser.parse_args()
    launch(args.config_file, args.test_name, args.clean, args.destroy, args.build)

if __name__ == '__main__':
    main()
