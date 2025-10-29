#!/usr/bin/env python3
"""
Simple test script to verify the MCP server functions work correctly.

This script tests the core functions without requiring a full MCP client.
"""

import sys
import json
from mcp_server import (
    get_failed_jobs_for_pr,
    get_build_log,
    analyze_build_log,
    load_config,
    build_repository_cache,
    resolve_repository,
    CONFIG as SERVER_CONFIG,
)


def test_list_failed_jobs(repo_identifier: str, pr_number: str):
    """Test listing failed jobs for a PR."""
    try:
        repo_info = resolve_repository(repo_identifier)
        print(f"\n{'='*80}")
        print(f"Testing: List failed jobs for {repo_info.full_name} PR #{pr_number}")
        print(f"{'='*80}\n")

        failed_jobs = get_failed_jobs_for_pr(repo_info, pr_number)

        if not failed_jobs:
            print(f"✓ No failed jobs found for {repo_info.full_name} PR #{pr_number}")
            return True

        print(f"✓ Found {len(failed_jobs)} failed job(s):\n")
        for job_name, build in failed_jobs.items():
            print(f"  Repository: {build.repository}")
            print(f"  Job: {job_name}")
            print(f"  Build ID: {build.build_id}")
            print(f"  Status: {build.status}")
            print(f"  URL: {build.prow_url}")
            print()

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_analyze_failed_job(repo_identifier: str, pr_number: str, limit_lines: int = 100):
    """Test analyzing failed jobs for a PR."""
    try:
        repo_info = resolve_repository(repo_identifier)
        print(f"\n{'='*80}")
        print(f"Testing: Analyze failed jobs for {repo_info.full_name} PR #{pr_number}")
        print(f"{'='*80}\n")

        failed_jobs = get_failed_jobs_for_pr(repo_info, pr_number)

        if not failed_jobs:
            print(f"✓ No failed jobs to analyze for {repo_info.full_name} PR #{pr_number}")
            return True

        # Analyze the first failed job
        job_name, build = list(failed_jobs.items())[0]

        print(f"Repository: {build.repository}")
        print(f"Analyzing job: {job_name}")
        print(f"Build ID: {build.build_id}\n")

        # Resolve repo to get repo_info
        repo_info = resolve_repository(repo_identifier)
        log_content = get_build_log(repo_info, pr_number, job_name, build.build_id)

        if not log_content:
            print(f"✗ Failed to fetch build log")
            return False

        print(f"✓ Fetched build log ({len(log_content)} bytes, {len(log_content.split(chr(10)))} lines)")

        analysis = analyze_build_log(log_content, max_lines=limit_lines)
        print(f"\n✓ Analysis complete:")
        print(f"  Summary: {analysis['summary']}")
        print(f"  Test failures: {len(analysis['error_patterns']['test_failures'])}")
        print(f"  Timeout errors: {len(analysis['error_patterns']['timeout_errors'])}")
        print(f"  Resource errors: {len(analysis['error_patterns']['resource_errors'])}")
        print(f"  Build errors: {len(analysis['error_patterns']['build_errors'])}")
        print(f"  Other errors: {len(analysis['error_patterns']['other_errors'])}")

        if analysis['error_patterns']['test_failures']:
            print(f"\n  First test failure:")
            print(f"    {analysis['error_patterns']['test_failures'][0]}")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run tests."""
    if len(sys.argv) < 2:
        print("Usage: python test_server.py <pr_number> [repository]")
        print("\nExamples:")
        print("  python test_server.py 123                    # Uses default repo if only one configured")
        print("  python test_server.py 123 nvidia-ci          # Just repo name (if unambiguous)")
        print("  python test_server.py 123 rh-ecosystem-edge/nvidia-ci  # Full name")
        sys.exit(1)

    pr_number = sys.argv[1]

    # Load configuration
    import mcp_server
    mcp_server.CONFIG = load_config()
    mcp_server.REPO_CACHE = build_repository_cache()

    # Determine repository
    if len(sys.argv) >= 3:
        repo_identifier = sys.argv[2]
    else:
        # Use None - will default to the only repository if just one configured
        repo_identifier = None
        print(f"No repository specified - will auto-detect from config...")

    try:
        # Resolve the repository
        repo_info = resolve_repository(repo_identifier)

        print(f"\n{'#'*80}")
        print(f"# Testing MCP Server Functions")
        print(f"# Repository: {repo_info.full_name}")
        print(f"# PR: #{pr_number}")
        print(f"{'#'*80}")

        # Run tests
        results = []

        results.append(("List Failed Jobs", test_list_failed_jobs(repo_identifier, pr_number)))
        results.append(("Analyze Failed Jobs", test_analyze_failed_job(repo_identifier, pr_number)))

        # Summary
        print(f"\n{'='*80}")
        print("Test Summary")
        print(f"{'='*80}\n")

        for test_name, passed in results:
            status = "✓ PASSED" if passed else "✗ FAILED"
            print(f"{status}: {test_name}")

        all_passed = all(result for _, result in results)

        print()
        if all_passed:
            print("✓ All tests passed!")
            sys.exit(0)
        else:
            print("✗ Some tests failed")
            sys.exit(1)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

