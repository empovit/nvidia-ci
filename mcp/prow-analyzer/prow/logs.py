"""Prow log fetching and analysis."""

from typing import Any, Dict, Optional

from config import RepositoryInfo
from gcs import client as gcs_client
from gcs.paths import build_pr_path, build_artifacts_path


# Job statuses
STATUS_SUCCESS = "SUCCESS"
STATUS_FAILURE = "FAILURE"
STATUS_UNKNOWN = "UNKNOWN"


def get_build_log(config: Dict[str, Any], repo_info: RepositoryInfo, pr_number: str,
                 job_name: str, build_id: str) -> Optional[str]:
    """Fetch build log for a specific build."""
    bucket = config["gcs_bucket"]
    path_template = config["path_template"]
    pr_path = build_pr_path(repo_info, pr_number, path_template)
    log_path = f"{pr_path}/{job_name}/{build_id}/build-log.txt"

    return gcs_client.fetch_file(bucket, log_path)


def get_step_build_log(config: Dict[str, Any], repo_info: RepositoryInfo, pr_number: str,
                      job_name: str, build_id: str, step_name: str) -> Optional[str]:
    """
    Fetch build log for a specific step/artifact.

    step_name can be either a top-level step or a nested path like "parent/substep".
    """
    bucket = config["gcs_bucket"]
    path_template = config["path_template"]
    log_path = build_artifacts_path(repo_info, pr_number, job_name, build_id, path_template, step_name, "build-log.txt").rstrip('/')

    return gcs_client.fetch_file(bucket, log_path)


def analyze_log_for_failure(log_content: str) -> str:
    """Determine if a build failed based on log content."""
    if not log_content:
        return STATUS_UNKNOWN

    # Check last 500 chars for final job state (most reliable)
    log_end = log_content[-500:]
    log_end_lower = log_end.lower()

    # Check for Prow's final status report
    if "reporting job state" in log_end_lower:
        if "succeeded" in log_end_lower:
            return STATUS_SUCCESS
        if "failed" in log_end_lower or "aborted" in log_end_lower:
            return STATUS_FAILURE

    # Fall back to looking for common failure indicators in the full log
    log_lower = log_content.lower()

    failure_patterns = [
        "fail:", "failed", "test failed", "tests failed",
        "exit code 1", "exit status 1",
    ]

    if any(pattern in log_lower for pattern in failure_patterns):
        return STATUS_FAILURE

    # Check for success indicators
    if "all tests passed" in log_lower:
        return STATUS_SUCCESS

    return STATUS_UNKNOWN

