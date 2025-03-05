#!/usr/bin/env python

import requests
import os
import base64
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

def update_sha(versions_file, version_key):

    token = os.getenv('AUTH_TOKEN') # In a workflow, set `AUTH_TOKEN=$(echo ${{ secrets.GITHUB_TOKEN }} | base64)`
    if token:
        logger.info('AUTH_TOKEN env variable is available, using it for authentication')
    else:
        logger.info('AUTH_TOKEN is not available, calling authentication API')
        auth_req = requests.get(f'https://ghcr.io/token?scope=repository:nvidia/gpu-operator:pull', allow_redirects=True, headers={'Content-Type': 'application/json'})
        auth_req.raise_for_status()
        token = auth_req.json()['token']

    req = requests.get('https://ghcr.io/v2/nvidia/gpu-operator/gpu-operator-bundle/manifests/main-latest', headers={
        'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
    req.raise_for_status()
    digest = req.json()['config']['digest']
    print(digest)

    with open(versions_file, "r+") as json_f:
        data = json.load(json_f)
        old_digest = data.get(version_key)
        if old_digest != digest:
            logger.info(f'New digest detected: {digest} (was {old_digest})')
            data[version_key] = digest
            json_f.seek(0)  # rewind
            json.dump(data, json_f, indent=4)
            json_f.truncate()
    pass


if __name__ == '__main__':
    update_sha(sys.argv[1], 'gpu-main-latest')