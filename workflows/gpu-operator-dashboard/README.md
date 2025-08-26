# GPU Operator Dashboard Workflow

This workflow generates a HTML dashboard showing NVIDIA GPU Operator test results across different operator versions and OpenShift versions. It fetches test data from CI systems and creates visual reports for tracking test status over time.

## Overview

The dashboard workflow:
- Fetches test results from Google Cloud Storage based on pull request data
- Merges new results with existing baseline data
- Generates HTML dashboard reports
- Automatically deploys updates to GitHub Pages

## Usage

### Prerequisites

```bash
pip install -r requirements.txt
```

**Important:** Before running fetch_ci_data.py, create the baseline data file and initialize it with an empty JSON object if it doesn't exist:
```bash
echo '{}' > data.json
```

### Fetch CI Data

```bash
# Process a specific PR
python fetch_ci_data.py --pr_number "123" --baseline_data_filepath data.json --merged_data_filepath data.json

# Process all closed PRs - limited to 100 most recent (default)
python fetch_ci_data.py --pr_number "all" --baseline_data_filepath data.json --merged_data_filepath data.json
```

### Generate Dashboard

```bash
python generate_ci_dashboard.py --dashboard_data_filepath data.json --dashboard_html_filepath dashboard.html
```

### Running Tests

Execute the test suite from the workflow directory:
```bash
# From the gpu-operator-dashboard/ directory
python -m unittest discover tests -p "test*.py"

# Or run tests individually
python -m unittest tests.test_generate_data
python -m unittest tests.test_generate_ui
```

The test suite includes:
- `test_generate_data.py` - Tests for data extraction and merging logic
- `test_generate_ui.py` - Tests for the HTML generation logic

## GitHub Actions Integration

- **Automatic**: Processes merged pull requests to update the dashboard with new test results and deploys to GitHub Pages
- **Manual**: Can be triggered manually via GitHub Actions workflow dispatch
