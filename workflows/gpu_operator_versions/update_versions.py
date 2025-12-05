import json
from workflows.common.utils import logger

from workflows.gpu_operator_versions.settings import Settings
from workflows.gpu_operator_versions.openshift import fetch_ocp_versions
from workflows.gpu_operator_versions.version_utils import get_latest_versions, get_earliest_versions
from workflows.gpu_operator_versions.nvidia_gpu_operator import get_operator_versions, get_sha
from workflows.gpu_operator_versions.catalog_checker import check_gpu_operator_availability

# Constants
test_command_template = "/test {ocp_version}-stable-nvidia-gpu-operator-e2e-{gpu_version}"

# Version type constants
VERSION_MASTER = "master"
VERSION_GPU_MAIN_LATEST = "gpu-main-latest"
VERSION_GPU_OPERATOR = "gpu-operator"
VERSION_OCP = "ocp"

# Status constants
STATUS_ACTIVE = "active"
STATUS_MAINTENANCE = "maintenance"

# Configuration keys
CONFIG_STATUS = "status"
CONFIG_PINNED_GPU_OPERATOR = "pinned_gpu_operator"
CONFIG_OPENSHIFT_SUPPORT = "openshift_support"
CONFIG_DEFAULTS = "defaults"
CONFIG_UNLISTED_VERSIONS = "unlisted_versions"


def save_tests_commands(tests_commands: set, file_path: str):
    with open(file_path, "w+") as f:
        for command in sorted(tests_commands):
            f.write(command + "\n")


def get_ocp_support_config(ocp_version: str, support_matrix: dict) -> dict:
    """Get support configuration for a specific OpenShift version."""
    ocp_support = support_matrix.get(CONFIG_OPENSHIFT_SUPPORT, {})
    if ocp_version in ocp_support:
        return ocp_support[ocp_version]
    return support_matrix.get(CONFIG_DEFAULTS, {}).get(CONFIG_UNLISTED_VERSIONS, {
        CONFIG_STATUS: STATUS_ACTIVE
    })


def normalize_pinned_gpu_operator(pinned: any) -> list:
    """Normalize pinned_gpu_operator to a list."""
    if pinned is None:
        return []
    if isinstance(pinned, list):
        return pinned
    if isinstance(pinned, str):
        return [pinned]
    if isinstance(pinned, set):
        return list(pinned)
    return []


def get_active_ocp_versions(ocp_releases: list, support_matrix: dict) -> list:
    """Get list of active (non-maintenance) OpenShift versions."""
    return [
        ocp for ocp in ocp_releases
        if get_ocp_support_config(ocp, support_matrix).get(CONFIG_STATUS) == STATUS_ACTIVE
    ]


def handle_master_bundle_changes(ocp_releases: list, support_matrix: dict) -> set:
    """Generate tests for master bundle (gpu-main-latest) changes."""
    tests = set()
    active_ocp_versions = get_active_ocp_versions(ocp_releases, support_matrix)

    # Test with newest active version
    for ocp_version in get_latest_versions(active_ocp_versions, 1):
        tests.add((ocp_version, VERSION_MASTER))

    # Test with oldest active version
    for ocp_version in get_earliest_versions(active_ocp_versions, 1):
        tests.add((ocp_version, VERSION_MASTER))

    return tests


def handle_ocp_version_changes(diffs: dict, ocp_releases: list, gpu_releases: list,
                               support_matrix: dict) -> set:
    """Generate tests for OpenShift version changes (new patches)."""
    tests = set()

    for ocp_version in diffs.get(VERSION_OCP, {}):
        if ocp_version not in ocp_releases:
            logger.warning(
                f'OpenShift version "{ocp_version}" is not in the list of releases. '
                f'Check if there was an update to an old version.'
            )
            continue

        ocp_config = get_ocp_support_config(ocp_version, support_matrix)

        if ocp_config.get(CONFIG_STATUS) == STATUS_MAINTENANCE:
            # Maintenance versions: test only with pinned GPU operators
            pinned_gpus = normalize_pinned_gpu_operator(ocp_config.get(CONFIG_PINNED_GPU_OPERATOR))
            for pinned_gpu in pinned_gpus:
                if pinned_gpu not in gpu_releases:
                    logger.warning(
                        f'Maintenance OCP version "{ocp_version}" has pinned GPU operator "{pinned_gpu}" '
                        f'which is not in the list of supported releases.'
                    )
                    continue

                tests.add((ocp_version, pinned_gpu))
        else:
            # Active versions: test with latest 2 GPU operator versions
            for gpu_version in gpu_releases:
                tests.add((ocp_version, gpu_version))

    return tests


def handle_gpu_operator_changes(diffs: dict, ocp_releases: list, gpu_releases: list,
                                support_matrix: dict) -> set:
    """Generate tests for GPU operator version changes (new releases or patches)."""
    tests = set()

    for gpu_version in diffs.get(VERSION_GPU_OPERATOR, {}):
        if gpu_version not in gpu_releases:
            logger.warning(
                f'GPU operator version "{gpu_version}" is not in the list of releases: {list(gpu_releases)}. '
                f'Check if there was an update to an old version.'
            )
            continue

        # GPU operator changes only test with active OCP versions
        # Maintenance OCP versions are frozen and never test GPU operator updates
        active_ocp_versions = get_active_ocp_versions(ocp_releases, support_matrix)

        for ocp_version in active_ocp_versions:
            tests.add((ocp_version, gpu_version))

    return tests


def create_tests_matrix(diffs: dict, ocp_releases: list, gpu_releases: list,
                       support_matrix: dict) -> set:
    """
    Create test matrix based on version changes and support matrix.

    Rules:
    1. GPU main-latest changed: Test with newest/oldest active OCP versions
    2. OCP version changed: Active versions test with latest 2 GPU operators,
                           maintenance versions test only with pinned GPU operators
    3. GPU operator changed: Test only with active OCP versions (maintenance is frozen)
    """
    tests = set()

    if VERSION_GPU_MAIN_LATEST in diffs:
        tests.update(handle_master_bundle_changes(ocp_releases, support_matrix))

    if VERSION_OCP in diffs:
        tests.update(handle_ocp_version_changes(diffs, ocp_releases, gpu_releases, support_matrix))

    if VERSION_GPU_OPERATOR in diffs:
        tests.update(handle_gpu_operator_changes(diffs, ocp_releases, gpu_releases, support_matrix))

    return tests


def create_tests_commands(diffs: dict, ocp_releases: list, gpu_releases: list,
                         support_matrix: dict) -> set:
    tests_commands = set()
    tests = create_tests_matrix(diffs, ocp_releases, gpu_releases, support_matrix)
    for t in tests:
        gpu_version_suffix = version2suffix(t[1])
        tests_commands.add(test_command_template.format(ocp_version=t[0], gpu_version=gpu_version_suffix))
    return tests_commands


def calculate_diffs(old_versions: dict, new_versions: dict, ocp_versions: dict = None,
                    support_matrix: dict = None, check_catalog: bool = False) -> dict:
    diffs = {}
    for key, value in new_versions.items():
        if isinstance(value, dict):
            logger.info(f'Comparing versions under "{key}"')
            sub_diff = calculate_diffs(old_versions.get(key, {}), value)
            if sub_diff:
                diffs[key] = sub_diff
        else:
            if key not in old_versions or old_versions[key] != value:
                logger.info(f'Key "{key}" has changed: {old_versions.get(key)} > {value}')
                diffs[key] = value

    # Filter GPU operator diffs by catalog availability
    if check_catalog and VERSION_GPU_OPERATOR in diffs and ocp_versions and support_matrix:
        gpu_diffs = diffs[VERSION_GPU_OPERATOR]
        if gpu_diffs:
            filtered = filter_new_gpu_versions_by_catalog(
                gpu_diffs,
                new_versions[VERSION_GPU_OPERATOR],
                ocp_versions,
                support_matrix
            )
            if filtered:
                diffs[VERSION_GPU_OPERATOR] = filtered
            else:
                del diffs[VERSION_GPU_OPERATOR]

    return diffs


def version2suffix(v: str):
    return v if v == VERSION_MASTER else f'{v.replace(".", "-")}-x'


def filter_new_gpu_versions_by_catalog(
    gpu_diffs: dict,
    all_gpu_versions: dict,
    ocp_versions: dict,
    support_matrix: dict
) -> dict:
    """Filter out new GPU versions that aren't in any active OCP catalog."""
    if not gpu_diffs:
        return gpu_diffs

    new_gpu_versions = list(gpu_diffs.keys())
    ocp_releases = list(ocp_versions.keys())
    gpu_releases = get_latest_versions(list(all_gpu_versions.keys()), 2)
    active_ocp_versions = get_active_ocp_versions(ocp_releases, support_matrix)

    # Only check latest 2 GPU releases
    versions_to_check = [v for v in new_gpu_versions if v in gpu_releases]
    if not versions_to_check:
        return gpu_diffs

    # Check catalog availability
    logger.info(f'Checking catalog availability for {len(versions_to_check)} new GPU version(s)')
    all_catalog_results = check_gpu_operator_availability(
        gpu_versions=versions_to_check,
        ocp_versions=active_ocp_versions,
        operator_package="gpu-operator-certified"
    )

    # Filter out versions not in any catalog
    filtered_diffs = dict(gpu_diffs)
    for gpu_version in versions_to_check:
        catalog_results = all_catalog_results.get(gpu_version, {})
        available_in_any = any(catalog_results.values())

        if not available_in_any:
            logger.warning(
                f'GPU operator {gpu_version} not available in any active OCP catalog - '
                f'excluding from versions.json (will retry next run)'
            )
            del filtered_diffs[gpu_version]

    return filtered_diffs


def apply_diffs(old_versions: dict, diffs: dict) -> dict:
    """Apply diffs to old versions to create updated versions."""
    updated = dict(old_versions)
    for key, value in diffs.items():
        if isinstance(value, dict) and key in updated and isinstance(updated[key], dict):
            # Recursively apply nested diffs
            updated[key] = apply_diffs(updated[key], value)
        else:
            updated[key] = value
    return updated


def main():
    settings = Settings()
    sha = get_sha(settings)
    gpu_versions = get_operator_versions(settings)
    ocp_versions = fetch_ocp_versions(settings)

    new_versions = {
        VERSION_GPU_MAIN_LATEST: sha,
        VERSION_GPU_OPERATOR: gpu_versions,
        VERSION_OCP: ocp_versions
    }

    with open(settings.version_file_path, "r+") as json_f:
        old_versions = json.load(json_f)

        # Calculate diffs with catalog filtering
        diffs = calculate_diffs(
            old_versions,
            new_versions,
            ocp_versions=ocp_versions,
            support_matrix=settings.support_matrix,
            check_catalog=settings.check_catalog_availability
        )

        # Apply filtered diffs to get final versions
        final_versions = apply_diffs(old_versions, diffs)

        json_f.seek(0)
        json.dump(final_versions, json_f, indent=4)
        json_f.truncate()

    diffs = calculate_diffs(old_versions, new_versions)
    ocp_releases = list(ocp_versions.keys())
    gpu_releases = get_latest_versions(list(gpu_versions.keys()), 2)

    tests_commands = create_tests_commands(
        diffs,
        ocp_releases,
        gpu_releases,
        settings.support_matrix
    )
    save_tests_commands(tests_commands, settings.tests_to_trigger_file_path)

if __name__ == '__main__':
    main()
