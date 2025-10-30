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

This MCP server provides **16 tools** organized into three categories: high-level domain-specific tools, specialized must-gather tools, and low-level exploration tools.

### High-Level vs Low-Level Tools: Why Both?

The server provides both **high-level** and **low-level** tools to balance efficiency with flexibility:

**High-Level Tools** (✅ Use these first):
- **Fast**: Get answers in 1-3 tool calls instead of 20+
- **Efficient**: Pre-parsed structured data (JSON, XML) saves tokens
- **Focused**: Return exactly what you need for common workflows
- **Domain-aware**: Encode OpenShift/Prow CI knowledge

**Low-Level Tools** (🔧 Use when needed):
- **Flexible**: Access any file or directory not covered by high-level tools
- **Exploratory**: Discover unknown structures and patterns
- **Future-proof**: Handle new CI patterns without code changes
- **Complete**: No data is hidden from the LLM

**Example Trade-off:**
```
❌ Without high-level tools:
   20+ calls: list dir → list subdir → fetch file → parse XML → extract failures

✅ With high-level tools:
   1 call: find_junit_files → Returns all test files with paths
   1 call: get_junit_results → Returns parsed failures with details
```

### Overview & Status Tools

**`get_pr_jobs_overview`** - Get comprehensive overview of all jobs in a PR
- Returns: Status counts, success rate, jobs grouped by status
- Use: First call to understand PR health

**`list_failed_jobs`** - List all failed jobs for a PR
- Returns: Failed job names, build IDs, Prow URLs
- Use: Quick list of what to investigate

### Build & Step Tools

**`get_build_log`** - Fetch complete build log for a job
- Returns: Full log content with size metadata
- Use: Main log for analyzing failures

**`list_build_steps`** - List all steps/artifacts in a build
- Returns: Step names, whether they have logs
- Use: Understand build structure, find failing steps

**`get_step_build_log`** - Fetch log for a specific step
- Returns: Step log content
- Use: Deep dive into specific step failures

**`get_step_metadata`** - Get parsed metadata for a step
- Returns: `started.json`, `finished.json` with timing and status
- Use: Get structured timing and status data without parsing logs

### Test Result Tools

**`find_junit_files`** - Find all JUnit XML test files in a build
- Returns: Paths to all `junit*.xml` files
- Use: Discover available test results

**`get_junit_results`** - Parse JUnit XML and extract test failures
- Returns: Test counts, failure details, error messages
- Use: Get structured test results instead of parsing logs

### Must-Gather Tools (OpenShift Debugging)

Must-gather artifacts contain comprehensive cluster state dumps. These tools help navigate them efficiently.

**`find_must_gather_directories`** - Find extracted must-gather dirs
- Returns: Paths to must-gather directories (archives excluded)
- Use: Discover what debug data is available
- Note: Only analyzes extracted directories, not `.tar`/`.tar.gz` archives

**`list_must_gather_pod_logs`** - List all pod logs in must-gather
- Returns: All `.log` files with paths and sizes
- Use: Find relevant pod logs without manual traversal

**`get_must_gather_pod_log`** - Fetch specific pod log
- Returns: Log content from must-gather
- Use: Retrieve specific pod logs for analysis

**`search_must_gather_files`** - Search files by pattern in must-gather
- Returns: Files matching wildcards (`*.yaml`, `*events*`, etc.)
- Use: Find configuration files, events, resource dumps

### Low-Level Exploration Tools

Use these when high-level tools don't cover your needs.

**`list_directory`** - List any GCS directory
- Input: Any GCS path
- Returns: Files and subdirectories with sizes
- Use: Explore unknown structures, find unexpected files

**`fetch_file`** - Fetch any file by path
- Input: Full GCS file path
- Returns: File content with metadata
- Use: Get any file not covered by specialized tools

**`get_pr_base_path`** - Get base GCS path for a PR
- Returns: GCS paths and URLs for the PR
- Use: Helper for constructing paths for low-level tools

## Usage Examples

### Quick Status Check (High-Level)
```
User: "What's the status of PR 346?"
LLM: Calls get_pr_jobs_overview → Shows 20 passed, 1 failed, 95% success rate
```

### Investigating Test Failures (High-Level + Structured Data)
```
User: "Why did the e2e tests fail in PR 346?"
LLM: 1. Calls find_junit_files → Finds "gpu-operator-e2e/gpu_suite_test_junit.xml"
     2. Calls get_junit_results → Gets parsed test failures
     3. Shows: "Test 'ValidateGPUOperator' failed: pod nvidia-driver-daemonset not ready"
```

### Deep Dive with Must-Gather (Specialized Tools)
```
User: "What's in the GPU operator must-gather?"
LLM: 1. Calls find_must_gather_directories → Finds "gpu-operator-tests-must-gather"
     2. Calls list_must_gather_pod_logs → Lists all pod logs
     3. Calls get_must_gather_pod_log → Retrieves failing pod's log
     4. Analyzes log to find root cause
```

### Exploring Unknown Structures (Low-Level)
```
User: "Are there any custom artifacts I should look at?"
LLM: 1. Calls list_directory("pr-logs/pull/.../artifacts/") → Discovers unknown dir
     2. Calls list_directory("custom-artifacts/") → Finds interesting files
     3. Calls fetch_file("custom-artifacts/debug-report.json") → Retrieves content
```

### Combined Workflow (All Tool Types)
```
User: "Analyze the GPU operator failure in PR 346"
LLM: 1. get_pr_jobs_overview → Identifies failed job
     2. find_junit_files → Finds test results
     3. get_junit_results → Gets "pod not ready" failure
     4. find_must_gather_directories → Finds GPU must-gather
     5. search_must_gather_files("*nvidia-driver*") → Finds driver pod files
     6. get_must_gather_pod_log → Retrieves driver pod log
     7. Analysis: "Driver failed to load: incompatible kernel version"
```

## Architecture & Philosophy

This server follows MCP best practices with a hybrid tool design:

### Server Responsibilities
- **Data access**: Fetch files from GCS storage
- **Mechanical parsing**: Parse structured formats (JSON, XML)
- **Path navigation**: Handle GCS path structures
- **No opinions**: Never interpret or filter failure data

### LLM Responsibilities
- **Intelligent analysis**: Understand logs and identify root causes
- **Pattern recognition**: Spot trends and anomalies
- **Decision making**: Choose which tools to use and in what order
- **Explanation**: Communicate findings to users

### Why This Design?

**High-level tools** = Server does mechanical work (parsing, path construction)
- Saves tokens and API calls
- Encodes domain knowledge (Prow structure, OpenShift patterns)
- Makes common cases fast

**Low-level tools** = LLM has full control when needed
- No artificial limitations
- Adapts to new patterns
- Handles edge cases

**Result**: Fast for common cases, flexible for everything else.

