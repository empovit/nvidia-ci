#!/usr/bin/env python

import requests
import os
import logging
import json
import sys

logger = logging.getLogger('update_sha')
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

def get_sha():

    token = os.getenv('AUTH_TOKEN') # In a GitHub workflow, set `AUTH_TOKEN=$(echo ${{ secrets.GITHUB_TOKEN }} | base64)`
    if token:
        logger.info('AUTH_TOKEN env variable is available, using it for authentication')
    else:
        logger.info('AUTH_TOKEN is not available, calling authentication API')
        auth_req = requests.get(f'https://ghcr.io/token?scope=repository:nvidia/gpu-operator:pull', allow_redirects=True,
                                headers={'Content-Type': 'application/json'})
        auth_req.raise_for_status()
        token = auth_req.json()['token']

    req = requests.get('https://ghcr.io/v2/nvidia/gpu-operator/gpu-operator-bundle/manifests/main-latest', headers={
        'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
    req.raise_for_status()
    return req.json()['config']['digest']

def update_key(versions_file, version_key, version_value):

    with open(versions_file, "r+") as json_f:
        data = json.load(json_f)
        old_version = data.get(version_key)
        if old_version == version_value:
            logger.info('No changes detected, exit')
            return

        logger.info(f'New version detected: {version_value} (was {old_version})')
        data[version_key] = version_value
        json_f.seek(0)  # rewind
        json.dump(data, json_f, indent=4)
        json_f.truncate()

if __name__ == '__main__':
    sha = get_sha()
    update_key(sys.argv[1], 'gpu-main-latest', sha)