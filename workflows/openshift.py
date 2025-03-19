#!/usr/bin/env python

import re
import requests
import semver

from settings import settings
from typing import Pattern, AnyStr
from utils import get_logger

logger = get_logger(__name__)

release_url_api = 'https://amd64.ocp.releases.ci.openshift.org/api/v1/releasestreams/accepted'

def fetch_ocp_versions() -> dict:
    """
    Fetches accepted OpenShift versions from the release API.

    The function filters out versions based on the regex pattern defined in settings.ignored_versions.
    For each minor version (e.g., 4.12), only the highest patch version is kept.

    Returns:
        dict: A dictionary mapping minor versions (e.g., '4.12') to their highest patch version (e.g., '4.12.3').
    """

    logger.info(f'Ignored versions: {settings.ignored_versions}')
    ignored_regex: Pattern[AnyStr] = re.compile(settings.ignored_versions)
    versions: dict = {}

    logger.info('Listing accepted OpenShift versions')
    response = requests.get(release_url_api, timeout=30)
    response.raise_for_status()
    response_json = response.json()

    accepted_versions = response_json.get('4-stable')
    logger.debug(f'Received OpenShift versions: {accepted_versions}')

    for ver in accepted_versions:
        sem_ver = semver.VersionInfo.parse(ver)
        minor = f'{sem_ver.major}.{sem_ver.minor}'
        if ignored_regex.fullmatch(minor):
            logger.debug(f'Version {ver} ignored')
            continue

        patches = versions.get(minor)
        versions[minor] = semver.max_ver(versions[minor], ver) if patches else ver

    return versions
