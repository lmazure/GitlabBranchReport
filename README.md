# GitLab Branch Report

This script generates a comprehensive report of all branches across all projects within a GitLab group.

## Features

For each branch, the report includes:
- Last commit author
- Last commit date
- Protection status
- Merge status (if merged, which branch it was merged into)
- Associated Merge Request (if any)

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

For all projects in a GitLab group:
```bash
python gitlab_branch_report.py <group-path>
```
where `<group-path>` is the path of your GitLab group (as it appears in the URL).

For a single project:
```bash
python gitlab_branch_report.py <mygroup/myproject>
```
where `<mygroup/myproject>` is the path of your GitLab project (as it appears in the URL).

Add the `-d` flag to open the report in a browser after generation:
```bash
python gitlab_branch_report.py <group-path> -d
```

## Output

The script will generate a formatted table containing all branch information, with the following columns:
- Project
- Branch
- Last Commit Author
- Last Commit Date
- Protected Status
- Merged Into
- Merge Request
