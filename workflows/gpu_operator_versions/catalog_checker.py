#!/usr/bin/env python3
"""
Check if GPU operator versions exist in OpenShift catalog using Red Hat Catalog API.
"""

import requests
from workflows.common.utils import logger

# Red Hat Catalog API base URL
CATALOG_API_BASE = "https://catalog.redhat.com/api/containers/v1"


def get_operator_channel(version: str) -> str:
    """
    Extract operator channel from version.
    Channel has 'v' prefix and is major.minor (e.g., "v25.10" from "25.10.1")
    """
    parts = version.lstrip('v').split('.')
    if len(parts) >= 2:
        return f"v{parts[0]}.{parts[1]}"
    return f"v{version.lstrip('v')}"


def build_catalog_filter(
    operator_package: str,
    gpu_versions: set[str],
    channels: set[str],
    ocp_versions: set[str]
) -> str:
    """Build optimized API filter query for catalog bundles."""
    version_filters = ','.join(f"version=={v}" for v in gpu_versions)
    channel_filters = ','.join(f"channel_name=={c}" for c in channels)
    ocp_filters = ','.join(f"ocp_version=={ocp}" for ocp in ocp_versions)

    return f"package=={operator_package};({version_filters});({channel_filters});({ocp_filters})"


def should_stop_pagination(
    found_combinations: set,
    expected_combinations: int,
    fetched_count: int,
    total_count: int
) -> bool:
    """Determine if we should stop paginating through API results."""
    if len(found_combinations) == expected_combinations:
        logger.debug(f"Found all {expected_combinations} combinations, stopping pagination")
        return True

    return fetched_count >= total_count


def fetch_catalog_bundles(
    filter_query: str,
    normalized_gpu_versions: set[str],
    ocp_versions_set: set[str]
) -> list[dict]:
    """Fetch operator bundles from catalog API with smart pagination."""
    url = f"{CATALOG_API_BASE}/operators/bundles"
    page = 0
    page_size = 100
    all_bundles = []
    expected_combinations = len(normalized_gpu_versions) * len(ocp_versions_set)

    while True:
        params = {"filter": filter_query, "page_size": page_size, "page": page}

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        bundles = data.get('data', [])

        if not bundles:
            break

        all_bundles.extend(bundles)

        # Check if we've found all needed combinations (early termination)
        found_combinations = {
            (b.get('version', '').lstrip('v'), b.get('ocp_version'))
            for b in all_bundles
            if b.get('version', '').lstrip('v') in normalized_gpu_versions
            and b.get('ocp_version') in ocp_versions_set
        }

        if should_stop_pagination(found_combinations, expected_combinations,
                                 (page + 1) * page_size, data.get('total', 0)):
            break

        page += 1

    logger.debug(f"Fetched {len(all_bundles)} bundles")
    return all_bundles


def parse_bundle_availability(
    bundles: list[dict],
    gpu_versions: list[str],
    ocp_versions: list[str]
) -> dict[str, dict[str, bool]]:
    """Parse bundles and build availability matrix."""
    normalized_gpu_versions = set(v.lstrip('v') for v in gpu_versions)
    ocp_versions_set = set(ocp_versions)

    # Initialize matrix with False
    results = {gpu_ver: {ocp: False for ocp in ocp_versions} for gpu_ver in gpu_versions}

    # Mark available combinations
    for bundle in bundles:
        bundle_version = bundle.get('version', '').lstrip('v')
        ocp_version = bundle.get('ocp_version')

        if bundle_version in normalized_gpu_versions and ocp_version in ocp_versions_set:
            for orig_ver in gpu_versions:
                if orig_ver.lstrip('v') == bundle_version:
                    results[orig_ver][ocp_version] = True

    return results


def check_gpu_operator_availability(
    gpu_versions: list[str],
    ocp_versions: list[str],
    operator_package: str = "gpu-operator-certified"
) -> dict[str, dict[str, bool]]:
    """
    Check if GPU operator versions are available across OpenShift versions.

    Args:
        gpu_versions: List of GPU operator versions (e.g., ["25.10.1", "24.6.2"] or ["25.10.1"])
        ocp_versions: List of OpenShift versions (e.g., ["4.20", "4.19"])
        operator_package: Package name in the catalog

    Returns:
        Nested dictionary: {gpu_version: {ocp_version: bool}}
        Example: {"25.10.1": {"4.20": True, "4.19": False}}

    Raises:
        requests.exceptions.RequestException: If API calls fail
    """
    # Normalize and prepare data
    normalized_gpu_versions = set(v.lstrip('v') for v in gpu_versions)
    channels = set(get_operator_channel(v) for v in gpu_versions)
    ocp_versions_set = set(ocp_versions)

    logger.info(
        f"Checking {operator_package} versions {list(normalized_gpu_versions)} "
        f"across OCP {', '.join(ocp_versions)}"
    )

    # Build filter and fetch bundles
    filter_query = build_catalog_filter(operator_package, normalized_gpu_versions,
                                       channels, ocp_versions_set)
    bundles = fetch_catalog_bundles(filter_query, normalized_gpu_versions, ocp_versions_set)

    # Parse results
    results = parse_bundle_availability(bundles, gpu_versions, ocp_versions)

    # Log summary
    for gpu_ver, ocp_results in results.items():
        available_count = sum(1 for avail in ocp_results.values() if avail)
        total_count = len(ocp_results)
        if available_count == total_count:
            logger.info(f"✓ {gpu_ver}: available in all {total_count} OCP versions")
        elif available_count == 0:
            logger.warning(f"✗ {gpu_ver}: not available in any OCP version")
        else:
            available_ocps = [ocp for ocp, avail in ocp_results.items() if avail]
            logger.warning(f"⚠ {gpu_ver}: available in {available_count}/{total_count} OCP versions ({', '.join(available_ocps)})")

    return results


if __name__ == "__main__":
    # CLI for manual testing/verification
    import sys

    if len(sys.argv) < 3:
        print("Usage: python catalog_checker.py <gpu_version> <ocp_version1> [ocp_version2 ...]")
        print("Example: python catalog_checker.py 25.10.1 4.20 4.19")
        sys.exit(1)

    gpu_ver = sys.argv[1]
    ocp_vers = sys.argv[2:]

    results = check_gpu_operator_availability([gpu_ver], ocp_vers)

    print(f"\nAvailability of GPU Operator v{gpu_ver}:")
    gpu_results = results.get(gpu_ver, {})
    for ocp, available in gpu_results.items():
        status = "✓ Available" if available else "✗ Not available"
        print(f"  OpenShift {ocp}: {status}")

    # Exit with error if not available in any version
    if not any(gpu_results.values()):
        sys.exit(1)



