#!/usr/bin/env python3
"""
MCP Server for analyzing failed Prow CI jobs in any GitHub repository using OpenShift CI.

Simplified approach:
- Lists directories to discover jobs
- Reads latest-build.txt for current build IDs
- Fetches build-log.txt directly
- No regex patterns needed!
"""

import json
import urllib.parse
import yaml
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# Job statuses
STATUS_SUCCESS = "SUCCESS"
STATUS_FAILURE = "FAILURE"
STATUS_UNKNOWN = "UNKNOWN"

# Default configuration
DEFAULT_CONFIG = {
    "gcs_bucket": "test-platform-results",
    "path_template": "pr-logs/pull/{org}_{repo}/{pr_number}",
    "repositories": [
        {
            "org": "rh-ecosystem-edge",
            "repo": "nvidia-ci",
        }
    ],
}

# Global configuration
CONFIG = None
REPO_CACHE = {}


@dataclass
class RepositoryInfo:
    """Information about a configured repository."""
    org: str
    repo: str

    @property
    def full_name(self) -> str:
        """Get GitHub-style org/repo name."""
        return f"{self.org}/{self.repo}"

    @property
    def gcs_name(self) -> str:
        """Get GCS path format (org_repo with underscore)."""
        return f"{self.org}_{self.repo}"

    def __str__(self) -> str:
        return self.full_name


@dataclass
class JobBuild:
    """Represents a single job build."""
    repository: str
    pr_number: str
    job_name: str
    build_id: str
    status: str
    prow_url: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository": self.repository,
            "pr_number": self.pr_number,
            "job_name": self.job_name,
            "build_id": self.build_id,
            "status": self.status,
            "prow_url": self.prow_url,
        }


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration with priority: ENV vars > config.yaml > defaults.

    Environment variables (for MCP client configuration):
    - PROW_GCS_BUCKET: GCS bucket name
    - PROW_PATH_TEMPLATE: Path template string
    - PROW_REPOSITORIES: Comma-separated list of org/repo (e.g., "rh-ecosystem-edge/nvidia-ci,openshift/release")
    """
    import os

    # Start with defaults
    config = DEFAULT_CONFIG.copy()

    # Load from config.yaml if it exists (unless disabled)
    if os.environ.get("PROW_NO_CONFIG_FILE") != "1":
        if config_path is None:
            script_dir = Path(__file__).parent
            config_path = script_dir / "config.yaml"

        if isinstance(config_path, str):
            config_path = Path(config_path)

        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        config.update(file_config)
            except Exception as e:
                print(f"Warning: Failed to load config from {config_path}: {e}", flush=True)

    # Override with environment variables if present
    if "PROW_GCS_BUCKET" in os.environ:
        config["gcs_bucket"] = os.environ["PROW_GCS_BUCKET"]

    if "PROW_PATH_TEMPLATE" in os.environ:
        config["path_template"] = os.environ["PROW_PATH_TEMPLATE"]

    if "PROW_REPOSITORIES" in os.environ:
        # Parse "org1/repo1,org2/repo2" format
        repos_str = os.environ["PROW_REPOSITORIES"]
        repos = []
        for repo_spec in repos_str.split(","):
            repo_spec = repo_spec.strip()
            if "/" in repo_spec:
                org, repo = repo_spec.split("/", 1)
                repos.append({"org": org.strip(), "repo": repo.strip()})
        if repos:
            config["repositories"] = repos

    return config


def build_repository_cache() -> Dict[str, RepositoryInfo]:
    """Build a cache mapping repository identifiers to RepositoryInfo objects."""
    cache = {}

    if not CONFIG or "repositories" not in CONFIG:
        return cache

    for repo_config in CONFIG["repositories"]:
        org = repo_config.get("org")
        repo = repo_config.get("repo")

        if not org or not repo:
            continue

        repo_info = RepositoryInfo(org=org, repo=repo)

        # Store multiple mappings for easy lookup
        if repo in cache:
            cache[repo] = "AMBIGUOUS"
        else:
            cache[repo] = repo_info

        cache[repo_info.full_name] = repo_info  # "org/repo"
        cache[repo_info.gcs_name] = repo_info   # "org_repo"

    return cache


def _get_unique_repos() -> List[RepositoryInfo]:
    """Get list of unique repositories from cache."""
    repos = [r for r in REPO_CACHE.values() if isinstance(r, RepositoryInfo)]
    return list({r.gcs_name: r for r in repos}.values())


def resolve_repository(repo_identifier: Optional[str]) -> RepositoryInfo:
    """Resolve a repository identifier to a RepositoryInfo object."""
    # If no identifier provided, check if there's only one repository
    if not repo_identifier:
        unique_repos = _get_unique_repos()

        if not unique_repos:
            raise ValueError("No repositories configured")

        if len(unique_repos) == 1:
            return unique_repos[0]

        available = [r.full_name for r in unique_repos]
        raise ValueError(
            f"Multiple repositories configured. Please specify which repository to use. "
            f"Available: {', '.join(available)}"
        )

    # Try to resolve the identifier
    if repo_identifier in REPO_CACHE:
        result = REPO_CACHE[repo_identifier]

        if result == "AMBIGUOUS":
            matches = [r for r in REPO_CACHE.values()
                      if isinstance(r, RepositoryInfo) and r.repo == repo_identifier]
            match_names = [r.full_name for r in matches]
            raise ValueError(
                f"Repository name '{repo_identifier}' is ambiguous. "
                f"Please specify the full name (org/repo). Matches: {', '.join(match_names)}"
            )

        return result

    # Not found
    available = {r.full_name for r in REPO_CACHE.values() if isinstance(r, RepositoryInfo)}
    raise ValueError(
        f"Repository '{repo_identifier}' not found. "
        f"Available: {', '.join(sorted(available))}"
    )


def get_gcs_bucket() -> str:
    """Get GCS bucket name from config."""
    return CONFIG.get("gcs_bucket", DEFAULT_CONFIG["gcs_bucket"])


def get_path_template() -> str:
    """Get path template from config."""
    return CONFIG.get("path_template", DEFAULT_CONFIG["path_template"])


def build_pr_path(repo_info: RepositoryInfo, pr_number: str) -> str:
    """Build the GCS path for a PR."""
    template = get_path_template()
    return template.format(
        org=repo_info.org,
        repo=repo_info.repo,
        org_repo=repo_info.gcs_name,
        pr_number=pr_number
    )


def list_gcs_directories(prefix: str) -> List[str]:
    """List directories (common prefixes) under a GCS prefix."""
    bucket = get_gcs_bucket()
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/o"

    params = {
        "prefix": prefix,
        "delimiter": "/",
        "alt": "json",
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Extract directory names from prefixes
        prefixes = data.get("prefixes", [])
        # Remove the common prefix and trailing slash to get just the directory names
        directories = [p.rstrip('/').split('/')[-1] for p in prefixes]
        return directories
    except Exception as e:
        print(f"Error listing directories: {e}", flush=True)
        return []


def fetch_gcs_file(path: str) -> Optional[str]:
    """Fetch a file from GCS."""
    bucket = get_gcs_bucket()
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/o/{urllib.parse.quote(path, safe='')}"

    try:
        response = requests.get(url, params={"alt": "media"}, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception:
        return None


def get_latest_build_id(repo_info: RepositoryInfo, pr_number: str, job_name: str) -> Optional[str]:
    """Get the latest build ID for a job."""
    pr_path = build_pr_path(repo_info, pr_number)
    latest_build_path = f"{pr_path}/{job_name}/latest-build.txt"

    content = fetch_gcs_file(latest_build_path)
    return content.strip() if content else None


def get_build_log(repo_info: RepositoryInfo, pr_number: str, job_name: str, build_id: str) -> Optional[str]:
    """Fetch build log for a specific build."""
    pr_path = build_pr_path(repo_info, pr_number)
    log_path = f"{pr_path}/{job_name}/{build_id}/build-log.txt"

    return fetch_gcs_file(log_path)


def _check_build_log_exists(artifacts_prefix: str, path: str) -> bool:
    """Check if a build-log.txt exists at the given path."""
    build_log_path = f"{artifacts_prefix}{path}/build-log.txt"
    return fetch_gcs_file(build_log_path) is not None


def _process_step_directory(artifacts_prefix: str, top_dir: str) -> List[Dict[str, Any]]:
    """Process a single step directory and return its steps."""
    has_top_level_log = _check_build_log_exists(artifacts_prefix, top_dir)

    if has_top_level_log:
        return [{"path": top_dir, "has_build_log": True}]

    # Check one level deeper for sub-steps
    sub_dirs = list_gcs_directories(f"{artifacts_prefix}{top_dir}/")
    if not sub_dirs:
        return [{"path": top_dir, "has_build_log": False}]

    # Process sub-directories
    steps = []
    for sub_dir in sub_dirs:
        sub_path = f"{top_dir}/{sub_dir}"
        has_sub_log = _check_build_log_exists(artifacts_prefix, sub_path)
        steps.append({"path": sub_path, "has_build_log": has_sub_log})

    return steps


def list_build_steps(repo_info: RepositoryInfo, pr_number: str, job_name: str, build_id: str) -> List[Dict[str, Any]]:
    """
    List available steps/artifacts in a build with their nested structure.

    Returns a list of dicts with 'path' and 'has_build_log' keys.
    """
    pr_path = build_pr_path(repo_info, pr_number)
    artifacts_prefix = f"{pr_path}/{job_name}/{build_id}/artifacts/"

    # List top-level directories under artifacts/
    top_level_dirs = list_gcs_directories(artifacts_prefix)

    # Process each directory and flatten results
    steps = []
    for top_dir in top_level_dirs:
        steps.extend(_process_step_directory(artifacts_prefix, top_dir))

    return steps


def get_step_build_log(repo_info: RepositoryInfo, pr_number: str, job_name: str, build_id: str, step_name: str) -> Optional[str]:
    """
    Fetch build log for a specific step/artifact.

    step_name can be either a top-level step or a nested path like "parent/substep".
    """
    pr_path = build_pr_path(repo_info, pr_number)
    log_path = f"{pr_path}/{job_name}/{build_id}/artifacts/{step_name}/build-log.txt"

    return fetch_gcs_file(log_path)


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


def build_prow_url(repo_info: RepositoryInfo, pr_number: str, job_name: str, build_id: str) -> str:
    """Build web UI URL for a job build."""
    pr_path = build_pr_path(repo_info, pr_number)
    return f"https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/{get_gcs_bucket()}/{pr_path}/{job_name}/{build_id}"


def get_all_jobs_for_pr(repo_info: RepositoryInfo, pr_number: str) -> List[JobBuild]:
    """Get all jobs and their latest builds for a PR."""
    pr_path = build_pr_path(repo_info, pr_number)

    # List all job directories
    job_names = list_gcs_directories(pr_path + "/")

    builds = []
    for job_name in job_names:
        # Get latest build ID
        build_id = get_latest_build_id(repo_info, pr_number, job_name)
        if not build_id:
            continue

        # Fetch build log to determine status
        log_content = get_build_log(repo_info, pr_number, job_name, build_id)
        status = analyze_log_for_failure(log_content) if log_content else STATUS_UNKNOWN

        prow_url = build_prow_url(repo_info, pr_number, job_name, build_id)

        build = JobBuild(
            repository=repo_info.gcs_name,
            pr_number=pr_number,
            job_name=job_name,
            build_id=build_id,
            status=status,
            prow_url=prow_url,
        )
        builds.append(build)

    return builds


def get_failed_jobs_for_pr(repo_info: RepositoryInfo, pr_number: str) -> Dict[str, JobBuild]:
    """Get all jobs where the latest build failed."""
    all_builds = get_all_jobs_for_pr(repo_info, pr_number)

    failed_jobs = {}
    for build in all_builds:
        if build.status == STATUS_FAILURE:
            failed_jobs[build.job_name] = build

    return failed_jobs


def get_pr_jobs_overview(repo_info: RepositoryInfo, pr_number: str) -> Dict[str, Any]:
    """Get comprehensive overview of all jobs in a PR, including status and statistics."""
    all_builds = get_all_jobs_for_pr(repo_info, pr_number)

    # Count by status
    status_counts = defaultdict(int)
    for build in all_builds:
        status_counts[build.status] += 1

    total_jobs = len(all_builds)
    success_count = status_counts[STATUS_SUCCESS]
    failure_count = status_counts[STATUS_FAILURE]
    unknown_count = status_counts[STATUS_UNKNOWN]

    # Calculate success rate
    success_rate = (success_count / total_jobs * 100) if total_jobs > 0 else 0

    # Group jobs by status
    jobs_by_status = {
        "success": [build.to_dict() for build in all_builds if build.status == STATUS_SUCCESS],
        "failure": [build.to_dict() for build in all_builds if build.status == STATUS_FAILURE],
        "unknown": [build.to_dict() for build in all_builds if build.status == STATUS_UNKNOWN],
    }

    return {
        "repository": repo_info.full_name,
        "pr_number": pr_number,
        "total_jobs": total_jobs,
        "statistics": {
            "success_count": success_count,
            "failure_count": failure_count,
            "unknown_count": unknown_count,
            "success_rate_percent": round(success_rate, 2),
        },
        "jobs_by_status": jobs_by_status,
        "summary": f"{total_jobs} total jobs: {success_count} passed, {failure_count} failed, {unknown_count} unknown ({success_rate:.1f}% success rate)",
    }


def _categorize_error_line(line: str) -> Optional[str]:
    """Categorize an error line into a specific error type."""
    line_lower = line.lower()

    if "fail" in line_lower or "failed" in line_lower:
        return "test_failures"
    elif "timeout" in line_lower or "timed out" in line_lower:
        return "timeout_errors"
    elif "resource" in line_lower and "error" in line_lower:
        return "resource_errors"
    elif "build" in line_lower and ("error" in line_lower or "fail" in line_lower):
        return "build_errors"
    elif "error" in line_lower:
        return "other_errors"

    return None


def _extract_error_patterns(lines: List[str], max_per_category: int = 20) -> Dict[str, List[str]]:
    """Extract and categorize error patterns from log lines."""
    error_patterns = {
        "test_failures": [],
        "timeout_errors": [],
        "resource_errors": [],
        "build_errors": [],
        "other_errors": [],
    }

    for line in lines:
        category = _categorize_error_line(line)
        if category and len(error_patterns[category]) < max_per_category:
            error_patterns[category].append(line.strip())

    return error_patterns


def _build_error_summary(error_patterns: Dict[str, List[str]]) -> str:
    """Build a human-readable summary of error patterns."""
    summary_parts = []
    for key, errors in error_patterns.items():
        if errors:
            label = key.replace("_", " ").title()
            summary_parts.append(f"Found {len(errors)} {label}")

    return "; ".join(summary_parts) if summary_parts else "No obvious error patterns found"


def analyze_build_log(log_content: str, max_lines: int = 500) -> Dict[str, Any]:
    """Analyze build log for error patterns."""
    lines = log_content.split('\n')
    total_lines = len(lines)

    # Analyze last N lines for errors
    analysis_lines = lines[-max_lines:] if len(lines) > max_lines else lines

    # Extract and categorize errors
    error_patterns = _extract_error_patterns(analysis_lines)

    # Build summary
    summary = _build_error_summary(error_patterns)

    return {
        "log_size_lines": total_lines,
        "analyzed_lines": len(analysis_lines),
        "error_patterns": error_patterns,
        "last_lines": '\n'.join(lines[-50:]) if len(lines) > 50 else log_content,
        "summary": summary,
    }


# Create MCP server
app = Server("prow-analyzer")


def _get_repository_info() -> tuple[str, str, List[str], bool]:
    """Get repository configuration info for tool schemas."""
    unique_repos = _get_unique_repos()
    repo_names = [r.full_name for r in unique_repos]
    repos_str = ", ".join(repo_names)
    repo_required = len(repo_names) > 1

    if not repo_names:
        repo_desc = "No repositories configured"
    elif len(repo_names) == 1:
        repo_desc = f"Optional. Defaults to {repo_names[0]} if not specified."
    else:
        repo_desc = f"Repository to analyze. Available: {repos_str}"

    return repo_desc, repos_str, ["pr_number"] if not repo_required else ["repository", "pr_number"], repo_required


def _build_base_properties(repo_desc: str) -> Dict[str, Any]:
    """Build base properties common to all tools."""
    return {
        "repository": {
            "type": "string",
            "description": repo_desc,
        },
        "pr_number": {
            "type": "string",
            "description": "PR number",
        },
    }


def _build_tool_schema(name: str, description: str, properties: Dict[str, Any], required: List[str]) -> Tool:
    """Build a tool schema with the given parameters."""
    return Tool(
        name=name,
        description=description,
        inputSchema={
            "type": "object",
            "properties": properties,
            "required": required,
        },
    )


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    repo_desc, repos_str, base_required, _ = _get_repository_info()
    base_props = _build_base_properties(repo_desc)

    # Simple tools with only base properties
    tools = [
        _build_tool_schema(
            "get_pr_jobs_overview",
            f"Get comprehensive overview of all jobs in a PR including their status, counts, and details. Use this first to understand the state of a PR's CI jobs. Configured repositories: {repos_str}",
            base_props,
            base_required
        ),
        _build_tool_schema(
            "list_failed_jobs",
            f"List all Prow jobs where the latest build failed. Configured repositories: {repos_str}",
            base_props,
            base_required
        ),
    ]

    # Tools with job_name and build_id
    job_build_props = {**base_props,
        "job_name": {"type": "string", "description": "Job name"},
        "build_id": {"type": "string", "description": "Build ID"},
    }

    tools.extend([
        _build_tool_schema(
            "get_build_log",
            "Fetch build log for a specific job build.",
            job_build_props,
            base_required + ["job_name", "build_id"]
        ),
        _build_tool_schema(
            "list_build_steps",
            "List available steps/artifacts in a build. Useful for identifying which steps failed.",
            job_build_props,
            base_required + ["job_name", "build_id"]
        ),
    ])

    # Tool with step_name
    step_props = {**job_build_props,
        "step_name": {"type": "string", "description": "Step/artifact name"},
    }
    tools.append(_build_tool_schema(
        "get_step_build_log",
        "Fetch build log for a specific step/artifact within a job build. Use list_build_steps first to see available steps.",
        step_props,
        base_required + ["job_name", "build_id", "step_name"]
    ))

    # Tool with max_log_lines
    analyze_job_props = {**job_build_props,
        "max_log_lines": {
            "type": "integer",
            "description": "Maximum lines to analyze from end of log (default: 500)",
            "default": 500,
        },
    }
    tools.append(_build_tool_schema(
        "analyze_failed_job",
        "Analyze a failed job by extracting error patterns from the build log.",
        analyze_job_props,
        base_required + ["job_name", "build_id"]
    ))

    # Tool for analyzing all failed jobs
    analyze_all_props = {**base_props,
        "max_log_lines": {
            "type": "integer",
            "description": "Maximum lines to analyze per log (default: 500)",
            "default": 500,
        },
    }
    tools.append(_build_tool_schema(
        "analyze_all_failed_jobs",
        "Analyze all failed jobs for a PR.",
        analyze_all_props,
        base_required
    ))

    return tools


def _handle_error(error: Exception) -> list[TextContent]:
    """Create error response for tool calls."""
    return [TextContent(
        type="text",
        text=json.dumps({"error": str(error)}, indent=2),
    )]


def _handle_success(data: Any) -> list[TextContent]:
    """Create success response for tool calls."""
    return [TextContent(
        type="text",
        text=json.dumps(data, indent=2),
    )]


def _handle_get_pr_jobs_overview(arguments: dict) -> list[TextContent]:
    """Handle get_pr_jobs_overview tool call."""
    try:
        repo_info = resolve_repository(arguments.get("repository"))
        overview = get_pr_jobs_overview(repo_info, arguments["pr_number"])
        return _handle_success(overview)
    except Exception as e:
        return _handle_error(e)


def _handle_list_failed_jobs(arguments: dict) -> list[TextContent]:
    """Handle list_failed_jobs tool call."""
    try:
        repo_info = resolve_repository(arguments.get("repository"))
        pr_number = arguments["pr_number"]
        failed_jobs = get_failed_jobs_for_pr(repo_info, pr_number)

        if not failed_jobs:
            result = {
                "message": f"No failed jobs found for {repo_info.full_name} PR #{pr_number}",
                "repository": repo_info.full_name,
                "pr_number": pr_number,
                "failed_jobs_count": 0,
            }
        else:
            result = {
                "repository": repo_info.full_name,
                "pr_number": pr_number,
                "failed_jobs_count": len(failed_jobs),
                "failed_jobs": [build.to_dict() for build in failed_jobs.values()],
            }

        return _handle_success(result)
    except Exception as e:
        return _handle_error(e)


def _handle_get_build_log(arguments: dict) -> list[TextContent]:
    """Handle get_build_log tool call."""
    try:
        repo_info = resolve_repository(arguments.get("repository"))
        pr_number = arguments["pr_number"]
        job_name = arguments["job_name"]
        build_id = arguments["build_id"]

        log_content = get_build_log(repo_info, pr_number, job_name, build_id)

        if not log_content:
            return _handle_error(ValueError("Build log not found"))

        result = {
            "repository": repo_info.full_name,
            "pr_number": pr_number,
            "job_name": job_name,
            "build_id": build_id,
            "log_size_bytes": len(log_content),
            "log_size_lines": len(log_content.split('\n')),
            "log_content": log_content,
        }

        return _handle_success(result)
    except Exception as e:
        return _handle_error(e)


def _handle_list_build_steps(arguments: dict) -> list[TextContent]:
    """Handle list_build_steps tool call."""
    try:
        repo_info = resolve_repository(arguments.get("repository"))
        pr_number = arguments["pr_number"]
        job_name = arguments["job_name"]
        build_id = arguments["build_id"]

        steps = list_build_steps(repo_info, pr_number, job_name, build_id)

        # Separate steps with and without build logs
        steps_with_logs = [s for s in steps if s.get("has_build_log")]

        result = {
            "repository": repo_info.full_name,
            "pr_number": pr_number,
            "job_name": job_name,
            "build_id": build_id,
            "total_steps": len(steps),
            "steps_with_build_logs": len(steps_with_logs),
            "steps": steps,
            "summary": f"Found {len(steps)} steps, {len(steps_with_logs)} have build logs available"
        }

        return _handle_success(result)
    except Exception as e:
        return _handle_error(e)


def _handle_get_step_build_log(arguments: dict) -> list[TextContent]:
    """Handle get_step_build_log tool call."""
    try:
        repo_info = resolve_repository(arguments.get("repository"))
        pr_number = arguments["pr_number"]
        job_name = arguments["job_name"]
        build_id = arguments["build_id"]
        step_name = arguments["step_name"]

        log_content = get_step_build_log(repo_info, pr_number, job_name, build_id, step_name)

        if not log_content:
            return _handle_error(ValueError(f"Build log not found for step '{step_name}'"))

        result = {
            "repository": repo_info.full_name,
            "pr_number": pr_number,
            "job_name": job_name,
            "build_id": build_id,
            "step_name": step_name,
            "log_size_bytes": len(log_content),
            "log_size_lines": len(log_content.split('\n')),
            "log_content": log_content,
        }

        return _handle_success(result)
    except Exception as e:
        return _handle_error(e)


def _handle_analyze_failed_job(arguments: dict) -> list[TextContent]:
    """Handle analyze_failed_job tool call."""
    try:
        repo_info = resolve_repository(arguments.get("repository"))
        pr_number = arguments["pr_number"]
        job_name = arguments["job_name"]
        build_id = arguments["build_id"]
        max_log_lines = arguments.get("max_log_lines", 500)

        log_content = get_build_log(repo_info, pr_number, job_name, build_id)

        if not log_content:
            return _handle_error(ValueError("Build log not found"))

        analysis = analyze_build_log(log_content, max_log_lines)

        result = {
            "repository": repo_info.full_name,
            "pr_number": pr_number,
            "job_name": job_name,
            "build_id": build_id,
            "analysis": analysis,
        }

        return _handle_success(result)
    except Exception as e:
        return _handle_error(e)


def _handle_analyze_all_failed_jobs(arguments: dict) -> list[TextContent]:
    """Handle analyze_all_failed_jobs tool call."""
    try:
        repo_info = resolve_repository(arguments.get("repository"))
        pr_number = arguments["pr_number"]
        max_log_lines = arguments.get("max_log_lines", 500)

        failed_jobs = get_failed_jobs_for_pr(repo_info, pr_number)

        if not failed_jobs:
            result = {
                "message": f"No failed jobs found for {repo_info.full_name} PR #{pr_number}",
                "repository": repo_info.full_name,
                "pr_number": pr_number,
                "failed_jobs_count": 0,
            }
        else:
            analyses = []
            for job_name, build in failed_jobs.items():
                log_content = get_build_log(repo_info, pr_number, job_name, build.build_id)
                if log_content:
                    analysis = analyze_build_log(log_content, max_log_lines)
                    analyses.append({
                        "job_info": build.to_dict(),
                        "analysis": analysis,
                    })

            result = {
                "repository": repo_info.full_name,
                "pr_number": pr_number,
                "failed_jobs_count": len(failed_jobs),
                "analyses": analyses,
            }

        return _handle_success(result)
    except Exception as e:
        return _handle_error(e)


# Tool handler registry
TOOL_HANDLERS = {
    "get_pr_jobs_overview": _handle_get_pr_jobs_overview,
    "list_failed_jobs": _handle_list_failed_jobs,
    "get_build_log": _handle_get_build_log,
    "list_build_steps": _handle_list_build_steps,
    "get_step_build_log": _handle_get_step_build_log,
    "analyze_failed_job": _handle_analyze_failed_job,
    "analyze_all_failed_jobs": _handle_analyze_all_failed_jobs,
}


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls by dispatching to appropriate handler."""
    handler = TOOL_HANDLERS.get(name)

    if handler:
        return handler(arguments)

    return _handle_error(ValueError(f"Unknown tool: {name}"))


async def main():
    """Run the MCP server."""
    global CONFIG, REPO_CACHE

    # Load configuration at startup
    CONFIG = load_config()

    # Build repository cache
    REPO_CACHE = build_repository_cache()

    # Log configuration
    import sys
    unique_repos = _get_unique_repos()
    repo_names = [r.full_name for r in unique_repos]

    print(f"Loaded configuration: {len(unique_repos)} repositories configured", file=sys.stderr, flush=True)
    print(f"Repositories: {', '.join(repo_names)}", file=sys.stderr, flush=True)
    print(f"GCS Bucket: {CONFIG.get('gcs_bucket')}", file=sys.stderr, flush=True)

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

