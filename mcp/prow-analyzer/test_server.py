#!/usr/bin/env python3
"""
Simple test script to verify the MCP server functions work correctly.

This script tests the core functions without requiring a full MCP client.
"""

import sys
import traceback
from typing import Optional, Tuple, List
from mcp_server import (
    get_failed_jobs_for_pr,
    get_build_log,
    analyze_build_log,
    load_config,
    build_repository_cache,
    resolve_repository,
)

# Constants
SEPARATOR = "=" * 80
HEADER_SEPARATOR = "#" * 80
DEFAULT_LOG_LINES = 100


def print_test_header(test_name: str, repo_full_name: str, pr_number: str) -> None:
    """Print a formatted test header."""
    print(f"\n{SEPARATOR}")
    print(f"Testing: {test_name} for {repo_full_name} PR #{pr_number}")
    print(f"{SEPARATOR}\n")


def print_failed_job_details(job_name: str, build) -> None:
    """Print details of a failed job."""
    print(f"  Repository: {build.repository}")
    print(f"  Job: {job_name}")
    print(f"  Build ID: {build.build_id}")
    print(f"  Status: {build.status}")
    print(f"  URL: {build.prow_url}")
    print()


def print_analysis_summary(analysis: dict) -> None:
    """Print analysis results summary."""
    error_patterns = analysis['error_patterns']

    print(f"\n✓ Analysis complete:")
    print(f"  Summary: {analysis['summary']}")
    print(f"  Test failures: {len(error_patterns['test_failures'])}")
    print(f"  Timeout errors: {len(error_patterns['timeout_errors'])}")
    print(f"  Resource errors: {len(error_patterns['resource_errors'])}")
    print(f"  Build errors: {len(error_patterns['build_errors'])}")
    print(f"  Other errors: {len(error_patterns['other_errors'])}")

    if error_patterns['test_failures']:
        print(f"\n  First test failure:")
        print(f"    {error_patterns['test_failures'][0]}")


def handle_test_error(error: Exception) -> None:
    """Print error information for a failed test."""
    print(f"✗ Error: {error}")
    traceback.print_exc()


def test_list_failed_jobs(repo_identifier: Optional[str], pr_number: str) -> bool:
    """Test listing failed jobs for a PR."""
    try:
        repo_info = resolve_repository(repo_identifier)
        print_test_header("List failed jobs", repo_info.full_name, pr_number)

        failed_jobs = get_failed_jobs_for_pr(repo_info, pr_number)

        if not failed_jobs:
            print(f"✓ No failed jobs found for {repo_info.full_name} PR #{pr_number}")
            return True

        print(f"✓ Found {len(failed_jobs)} failed job(s):\n")
        for job_name, build in failed_jobs.items():
            print_failed_job_details(job_name, build)

        return True

    except Exception as e:
        handle_test_error(e)
        return False


def fetch_and_display_log(repo_info, pr_number: str, job_name: str,
                          build_id: str) -> Optional[str]:
    """Fetch build log and display its size."""
    log_content = get_build_log(repo_info, pr_number, job_name, build_id)

    if not log_content:
        print(f"✗ Failed to fetch build log")
        return None

    num_lines = len(log_content.split('\n'))
    print(f"✓ Fetched build log ({len(log_content)} bytes, {num_lines} lines)")
    return log_content


def test_analyze_failed_job(repo_identifier: Optional[str], pr_number: str,
                           limit_lines: int = DEFAULT_LOG_LINES) -> bool:
    """Test analyzing failed jobs for a PR."""
    try:
        repo_info = resolve_repository(repo_identifier)
        print_test_header("Analyze failed jobs", repo_info.full_name, pr_number)

        failed_jobs = get_failed_jobs_for_pr(repo_info, pr_number)

        if not failed_jobs:
            print(f"✓ No failed jobs to analyze for {repo_info.full_name} PR #{pr_number}")
            return True

        # Analyze the first failed job
        job_name, build = list(failed_jobs.items())[0]

        print(f"Repository: {build.repository}")
        print(f"Analyzing job: {job_name}")
        print(f"Build ID: {build.build_id}\n")

        log_content = fetch_and_display_log(repo_info, pr_number, job_name, build.build_id)
        if not log_content:
            return False

        analysis = analyze_build_log(log_content, max_lines=limit_lines)
        print_analysis_summary(analysis)

        return True

    except Exception as e:
        handle_test_error(e)
        return False


def parse_arguments() -> Tuple[str, Optional[str]]:
    """Parse command line arguments and return PR number and repository identifier."""
    if len(sys.argv) < 2:
        print("Usage: python test_server.py <pr_number> [repository]")
        print("\nExamples:")
        print("  python test_server.py 123                    # Uses default repo if only one configured")
        print("  python test_server.py 123 nvidia-ci          # Just repo name (if unambiguous)")
        print("  python test_server.py 123 rh-ecosystem-edge/nvidia-ci  # Full name")
        sys.exit(1)

    pr_number = sys.argv[1]
    repo_identifier = sys.argv[2] if len(sys.argv) >= 3 else None

    if repo_identifier is None:
        print("No repository specified - will auto-detect from config...")

    return pr_number, repo_identifier


def initialize_config() -> None:
    """Load configuration and build repository cache."""
    import mcp_server
    mcp_server.CONFIG = load_config()
    mcp_server.REPO_CACHE = build_repository_cache()


def print_main_header(repo_full_name: str, pr_number: str) -> None:
    """Print the main test suite header."""
    print(f"\n{HEADER_SEPARATOR}")
    print(f"# Testing MCP Server Functions")
    print(f"# Repository: {repo_full_name}")
    print(f"# PR: #{pr_number}")
    print(f"{HEADER_SEPARATOR}")


def run_tests(repo_identifier: Optional[str], pr_number: str) -> List[Tuple[str, bool]]:
    """Run all tests and return results."""
    return [
        ("List Failed Jobs", test_list_failed_jobs(repo_identifier, pr_number)),
        ("Analyze Failed Jobs", test_analyze_failed_job(repo_identifier, pr_number)),
    ]


def print_test_summary(results: List[Tuple[str, bool]]) -> bool:
    """Print test summary and return whether all tests passed."""
    print(f"\n{SEPARATOR}")
    print("Test Summary")
    print(f"{SEPARATOR}\n")

    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(passed for _, passed in results)

    print()
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")

    return all_passed


def main() -> None:
    """Run the test suite."""
    pr_number, repo_identifier = parse_arguments()
    initialize_config()

    try:
        repo_info = resolve_repository(repo_identifier)
        print_main_header(repo_info.full_name, pr_number)

        results = run_tests(repo_identifier, pr_number)
        all_passed = print_test_summary(results)

        sys.exit(0 if all_passed else 1)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

