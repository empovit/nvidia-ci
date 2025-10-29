# Prow CI Analyzer - MCP Server

[MCP](https://modelcontextprotocol.io/) server for analyzing failed Prow CI jobs in GitHub repositories.

## Setup

### Important: Cursor AppImage Environment Issue

If you're setting up this project from **Cursor's integrated terminal**, you may encounter issues with Python virtual environment creation due to Cursor's AppImage environment pollution. The symptoms include:

- Symlinks in `venv/bin/python*` pointing to `cursor.appimage` instead of the system Python
- MCP server failing with `SyntaxError: Invalid or unexpected token` when Cursor tries to run it

**Solution:** Use the provided setup script instead:

```bash
cd mcp/prow-analyzer
./setup_venv.sh
```

See `setup_venv.sh` comments for technical details about why this is necessary.

### Standard Setup (from a clean terminal)

If you're setting up from a system terminal (not Cursor's integrated terminal):

```bash
cd mcp/prow-analyzer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

**Priority:** Environment variables > `config.yaml` > defaults

### Option 1: config.yaml

```yaml
gcs_bucket: "test-platform-results"
path_template: "pr-logs/pull/{org}_{repo}/{pr_number}"
repositories:
  - org: rh-ecosystem-edge
    repo: nvidia-ci
```

### Option 2: Environment Variables

```json
{
  "mcpServers": {
    "prow-analyzer": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/mcp_server.py"],
      "env": {
        "PROW_GCS_BUCKET": "test-platform-results",
        "PROW_PATH_TEMPLATE": "pr-logs/pull/{org}_{repo}/{pr_number}",
        "PROW_REPOSITORIES": "rh-ecosystem-edge/nvidia-ci,openshift/release"
      }
    }
  }
}
```

**Environment Variables:**
- `PROW_GCS_BUCKET` - GCS bucket name
- `PROW_PATH_TEMPLATE` - Path template
- `PROW_REPOSITORIES` - Comma-separated `org/repo` list
- `PROW_NO_CONFIG_FILE` - Set to "1" to ignore config.yaml

## MCP Client Configuration

### Cursor

Add to `~/.config/Cursor/mcp.json` or `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "prow-analyzer": {
      "command": "/absolute/path/to/venv/bin/python",
      "args": ["/absolute/path/to/mcp_server.py"],
      "env": {
        "PROW_GCS_BUCKET": "test-platform-results",
        "PROW_PATH_TEMPLATE": "pr-logs/pull/{org}_{repo}/{pr_number}",
        "PROW_REPOSITORIES": "rh-ecosystem-edge/nvidia-ci,openshift/release"
      }
    }
  }
}
```

**Important:** Use absolute paths, not `~` or relative paths, for the `command` and `args` fields.

### Claude Desktop

Add to `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "prow-analyzer": {
      "command": "/absolute/path/to/venv/bin/python",
      "args": ["/absolute/path/to/mcp_server.py"]
    }
  }
}
```

## Tools

### Overview
- `get_pr_jobs_overview` - Get overview of all jobs in a PR (status, counts, success rate, job details grouped by status)

### Job Details
- `list_failed_jobs` - List failed jobs for a PR
- `get_build_log` - Fetch main build log for a job
- `list_build_steps` - List available steps/artifacts in a build
- `get_step_build_log` - Fetch build log for a specific step

### Analysis
- `analyze_failed_job` - Extract error patterns from a failed job's log
- `analyze_all_failed_jobs` - Extract error patterns from all failed jobs in a PR

## Usage

1. Use `get_pr_jobs_overview` to see the overall state of a PR's jobs
2. Use `list_build_steps` and `get_step_build_log` to drill down into specific failures
3. Use `analyze_failed_job` or `analyze_all_failed_jobs` for automated error pattern extraction

