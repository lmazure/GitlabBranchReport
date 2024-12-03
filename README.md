# GitLab Branch Report

This script generates a comprehensive report of all branches across all projects within a GitLab group.

## Features

For each branch, the report includes:
- Last commit author
- Last commit date
- Protection status
- Merge status (if merged, which branch it was merged into)
- Associated Merge Request (if any)

## Requirements

- Python 3.6+
- GitLab access token with appropriate permissions
- Required Python packages (install via `pip install -r requirements.txt`):
  - python-gitlab
  - python-dateutil
  - tabulate

## Setup

1. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   ```bash
   # Required: Your GitLab personal access token
   export GITLAB_TOKEN='your-token-here'
   
   # Optional: Your GitLab instance URL (defaults to https://gitlab.com)
   export GITLAB_URL='https://your-gitlab-instance.com'
   ```

## Usage

```bash
python gitlab_branch_report.py <group-path>
```

Where `<group-path>` is the path of your GitLab group (as it appears in the URL).

## Output

The script will generate a formatted table containing all branch information, with the following columns:
- Project
- Branch
- Last Commit Author
- Last Commit Date
- Protected Status
- Merged Into
- Merge Request

## Error Handling

The script includes error handling for:
- Missing GitLab token
- Invalid group path
- API connection issues
- Permission errors

If any errors occur, they will be displayed with appropriate error messages.
