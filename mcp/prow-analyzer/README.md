# Prow CI Analyzer - MCP Server

[MCP](https://modelcontextprotocol.io/) server for accessing Prow CI job data from GitHub repositories using OpenShift CI infrastructure.

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
gcsweb_base_url: "https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs"
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
        "PROW_GCSWEB_BASE_URL": "https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs",
        "PROW_PATH_TEMPLATE": "pr-logs/pull/{org}_{repo}/{pr_number}",
        "PROW_REPOSITORIES": "rh-ecosystem-edge/nvidia-ci,openshift/release"
      }
    }
  }
}
```

**Environment Variables:**
- `PROW_GCS_BUCKET` - GCS bucket name (for data access)
- `PROW_GCSWEB_BASE_URL` - Base URL for GCSWeb UI links (without trailing slash)
- `PROW_PATH_TEMPLATE` - Path template for job data
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
        "PROW_GCSWEB_BASE_URL": "https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs",
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

This MCP server provides data access tools. The LLM client performs analysis of the retrieved data.

### Overview & Status
- `get_pr_jobs_overview` - Get comprehensive overview of all jobs in a PR including status, counts, success rate, and job details grouped by status

### Job Data Access
- `list_failed_jobs` - List all failed jobs for a PR with build IDs and Prow URLs
- `get_build_log` - Fetch complete build log for a specific job
- `list_build_steps` - List available steps/artifacts in a build (useful for complex multi-step jobs)
- `get_step_build_log` - Fetch build log for a specific step/artifact

## Usage Examples

### Quick Status Check
```
User: "What's the status of PR 123?"
LLM: Calls get_pr_jobs_overview → Shows 5 passed, 2 failed, 95% success rate
```

### Investigating Failures
```
User: "Why did PR 456 fail?"
LLM: 1. Calls list_failed_jobs → Gets failed job names
     2. Calls get_build_log → Retrieves full logs
     3. Analyzes logs using its intelligence
     4. Identifies root cause and explains it
```

### Deep Dive into Complex Jobs
```
User: "What step failed in the e2e-test job?"
LLM: 1. Calls list_build_steps → Shows all test steps
     2. Calls get_step_build_log for specific steps
     3. Pinpoints exact failure location
```

## Architecture

This server follows MCP best practices:
- **Server role**: Fetch and provide CI data
- **LLM role**: Analyze logs, identify issues, suggest solutions
- **Clean separation**: Server has no opinions, LLM provides intelligence

