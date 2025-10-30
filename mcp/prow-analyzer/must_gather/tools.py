"""Must-gather artifact analysis tools."""

from fnmatch import fnmatch
from typing import Any, Callable, Dict, List

from config import RepositoryInfo
from gcs import client as gcs_client
from gcs.paths import build_artifacts_path


def _search_directory_recursive(bucket: str, base_path: str, filter_fn: Callable[[Dict[str, Any]], bool],
                                max_depth: int = 5) -> List[Dict[str, Any]]:
    """
    Recursively search a directory structure and collect files matching a filter.

    Args:
        bucket: GCS bucket name
        base_path: GCS base path to start search
        filter_fn: Function that takes file_info dict and returns True if file should be included
        max_depth: Maximum recursion depth

    Returns:
        List of matching files with path, name, size, and full_path
    """
    results = []

    def search_directory(dir_path: str, relative_path: str = ""):
        """Inner recursive function."""
        data = gcs_client.list_files_and_directories(bucket, dir_path + "/")

        # Check files in current directory
        for file_info in data.get("files", []):
            if filter_fn(file_info):
                results.append({
                    "name": file_info["name"],
                    "path": f"{relative_path}/{file_info['name']}" if relative_path else file_info["name"],
                    "full_path": f"{dir_path}/{file_info['name']}",
                    "size": file_info["size"],
                })

        # Recursively search subdirectories (with depth limit)
        if relative_path.count('/') < max_depth:
            for subdir in data.get("directories", []):
                new_relative = f"{relative_path}/{subdir}" if relative_path else subdir
                search_directory(f"{dir_path}/{subdir}", new_relative)

    search_directory(base_path)
    return results


def find_must_gather_dirs(config: Dict[str, Any], repo_info: RepositoryInfo,
                         pr_number: str, job_name: str, build_id: str) -> List[Dict[str, Any]]:
    """
    Find all extracted must-gather directories (skip archives).

    Returns list of must-gather directories with their paths.
    Only returns directories containing 'must-gather' in the name, excluding archives.
    """
    bucket = config["gcs_bucket"]
    path_template = config["path_template"]
    artifacts_prefix = build_artifacts_path(repo_info, pr_number, job_name, build_id, path_template)

    # List top-level directories
    top_dirs = gcs_client.list_directories(bucket, artifacts_prefix)

    must_gather_dirs = []

    # Search for must-gather directories at multiple levels
    for top_dir in top_dirs:
        dir_path = f"{artifacts_prefix}{top_dir}"

        # Check if this directory itself is a must-gather
        if "must-gather" in top_dir.lower():
            must_gather_dirs.append({
                "path": top_dir,
                "full_path": dir_path,
                "level": "step",
            })

        # Check one level deeper for must-gather directories
        subdirs_data = gcs_client.list_files_and_directories(bucket, dir_path + "/")
        for subdir in subdirs_data.get("directories", []):
            if "must-gather" in subdir.lower():
                # Check if it's an extracted directory (has subdirectories, not just .tar files)
                subdir_full_path = f"{dir_path}/{subdir}"
                subdir_contents = gcs_client.list_files_and_directories(bucket, subdir_full_path + "/")

                # Only include if it has directories (meaning it's extracted)
                if subdir_contents.get("directories"):
                    must_gather_dirs.append({
                        "path": f"{top_dir}/{subdir}",
                        "full_path": subdir_full_path,
                        "level": "nested",
                    })

    return must_gather_dirs


def list_must_gather_pod_logs(config: Dict[str, Any], repo_info: RepositoryInfo,
                              pr_number: str, job_name: str, build_id: str,
                              must_gather_path: str) -> List[Dict[str, Any]]:
    """
    List all pod log files in a must-gather directory.

    Returns list of pod log files with their paths and sizes.
    """
    bucket = config["gcs_bucket"]
    path_template = config["path_template"]
    mg_base_path = build_artifacts_path(repo_info, pr_number, job_name, build_id, path_template, must_gather_path)

    # Search for all .log files
    return _search_directory_recursive(
        bucket,
        mg_base_path.rstrip('/'),
        filter_fn=lambda f: f["name"].endswith(".log")
    )


def get_must_gather_pod_log(config: Dict[str, Any], repo_info: RepositoryInfo,
                           pr_number: str, job_name: str, build_id: str,
                           must_gather_path: str, log_path: str) -> Dict[str, Any]:
    """
    Fetch a specific pod log from a must-gather directory.

    Returns the log content with metadata.
    """
    bucket = config["gcs_bucket"]
    path_template = config["path_template"]
    full_path = build_artifacts_path(repo_info, pr_number, job_name, build_id, path_template, must_gather_path, log_path).rstrip('/')

    log_content = gcs_client.fetch_file(bucket, full_path)
    if not log_content:
        return {
            "repository": repo_info.full_name,
            "pr_number": pr_number,
            "job_name": job_name,
            "build_id": build_id,
            "must_gather_path": must_gather_path,
            "log_path": log_path,
            "error": "Log file not found",
        }

    return {
        "repository": repo_info.full_name,
        "pr_number": pr_number,
        "job_name": job_name,
        "build_id": build_id,
        "must_gather_path": must_gather_path,
        "log_path": log_path,
        "content": log_content,
        "size_bytes": len(log_content),
        "size_lines": len(log_content.split('\n')),
    }


def search_must_gather_files(config: Dict[str, Any], repo_info: RepositoryInfo,
                            pr_number: str, job_name: str, build_id: str,
                            must_gather_path: str, pattern: str) -> List[Dict[str, Any]]:
    """
    Search for files matching a pattern in a must-gather directory.

    Pattern supports wildcards: *.yaml, *events*, etc.
    Returns list of matching files with their paths and sizes.
    """
    bucket = config["gcs_bucket"]
    path_template = config["path_template"]
    mg_base_path = build_artifacts_path(repo_info, pr_number, job_name, build_id, path_template, must_gather_path)

    # Search for files matching pattern (case-insensitive)
    return _search_directory_recursive(
        bucket,
        mg_base_path.rstrip('/'),
        filter_fn=lambda f: fnmatch(f["name"].lower(), pattern.lower())
    )

