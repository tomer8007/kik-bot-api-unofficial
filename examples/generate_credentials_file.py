#!/usr/bin/env python3

import argparse
import json

import os
import sys

from kik_unofficial.utilities.credential_utilities import random_device_id, random_android_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', default='creds.json', help='Name of output credentials file')
    parser.add_argument('-u', '--username', required=True, help='Kik username')
    parser.add_argument('-p', '--password', help='Kik password (optional)')
    parser.add_argument('-n', '--node', help='Kik node (optional)')
    args = parser.parse_args()

    if os.path.exists(args.output):
        print(f'Output file {args.output} already exists!')
        return

    file_obj = {
        'device_id': random_device_id(),
        'android_id': random_android_id(),
        'username': args.username,
    }
    if args.password:
        file_obj['password'] = args.password
    if args.node:
        file_obj['node'] = args.node
    with open(args.output, 'w') as f:
        json.dump(file_obj, f, indent=2)
        print(f'Wrote credentials to {args.output}')


if __name__ == '__main__':
    main()
