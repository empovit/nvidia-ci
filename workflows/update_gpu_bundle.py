#!/usr/bin/env python

# https://docker-docs.uclv.cu/registry/spec/api/
# https://github.com/orgs/community/discussions/26279
# https://stackoverflow.com/questions/70458458/how-do-i-simply-run-a-python-script-from-github-repo-with-actions

# Public, doesn't require authentication, but requires pagination
# curl -SsL -X GET "https://quay.io/v2/openshift-release-dev/ocp-release/tags/list?n=100&last=4.18.0-x86_64" -H 'Content-Type: application/json'

# Public, but requires authentication (haven't figured yet)
# curl -SsL -X GET https://nvcr.io/v2/nvidia/gpu-operator/tags/list -H 'Content-Type: application/json'

# Public, requires authentication
# token=$(curl -SsL https://ghcr.io/token\?scope\="repository:nvidia/gpu-operator:pull" | jq -r .token)
# curl -SsL -X GET https://ghcr.io/v2/nvidia/gpu-operator/gpu-operator-bundle/tags/list -H 'Content-Type: application/json' -H "Authorization: Bearer ${token}" | jq
# curl -SsL -X GET https://ghcr.io/v2/nvidia/gpu-operator/gpu-operator-bundle/manifests/main-latest -H 'Content-Type: application/json' -H "Authorization: Bearer ${token}" | jq -r .config.digest

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

    secret = os.getenv('AUTH_TOKEN') # In a workflow, use env variable AUTH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    if secret:
        logger.info('AUTH_TOKEN env variable is available')
        token = base64.b64encode(secret.encode())
    else:
        logger.info('AUTH_TOKEN is unavailable, calling authentication API')
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