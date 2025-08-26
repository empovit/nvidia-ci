# GPU Operator Versions Workflow

This workflow automates the process of checking for new versions of OpenShift and NVIDIA GPU Operator, updating version matrices, and triggering CI jobs.

## Overview

The version update automation:
- Fetches latest OpenShift release versions from the official API
- Retrieves NVIDIA GPU Operator versions from container registries
- Updates the version matrix in `versions.json`
- Generates test commands for new version combinations
- Creates pull requests with version updates

## Data Sources

- **OpenShift versions**: Retrieved from OpenShift CI release streams API
- **GPU Operator versions**: Fetched from NVIDIA Container Registry and GitHub Container Registry
- **Version matrix**: Stored in `versions.json` and updated automatically

## Running the Workflow

### Prerequisites

Install dependencies:
```console
pip install -r requirements.txt
```

### Manual Execution

Run the version update process:
```console
python update_versions.py
```

### Environment Variables

The workflow supports several environment variables:
- `GH_AUTH_TOKEN` - GitHub authentication token
- `OCP_IGNORED_VERSIONS_REGEX` - Regex to exclude specific OpenShift versions
- `VERSION_FILE_PATH` - Path to versions.json file
- `TEST_TO_TRIGGER_FILE_PATH` - Path to generated test commands file

### Running Tests

Execute the test suite from the workflow directory:

```console
# From the gpu-operator-versions/ directory
cd tests
python -m unittest discover -p "test_*.py"

# Or run all tests from the workflow root
python -m unittest discover tests -p "test_*.py"
```

## GitHub Actions Integration

- **Scheduled**: Runs nightly to check for new versions and creates pull requests when updates are detected
- **Manual**: Can be triggered manually via GitHub Actions workflow dispatch