#!/usr/bin/env python3

import os
import sys
from datetime import datetime
import gitlab
from dateutil import parser
from tabulate import tabulate

def get_gitlab_connection():
    """Create a GitLab connection using personal access token."""
    # Get token from environment variable for security
    token = os.getenv('GITLAB_TOKEN')
    if not token:
        print("Error: GITLAB_TOKEN environment variable not set")
        sys.exit(1)
    
    # Get GitLab URL, default to gitlab.com
    gitlab_url = os.getenv('GITLAB_URL', 'https://gitlab.com')
    
    try:
        return gitlab.Gitlab(gitlab_url, private_token=token)
    except Exception as e:
        print(f"Error connecting to GitLab: {e}")
        sys.exit(1)

def get_branch_details(project, branch_name):
    """Get detailed information about a specific branch."""
    try:
        branch = project.branches.get(branch_name)
        
        # Get branch protection status
        is_protected = branch.protected
        
        # Get the commit details
        commit = branch.commit
        last_commit_author = commit['author_name']
        last_commit_date = parser.parse(commit['committed_date'])
        
        # Get merge requests associated with this branch
        mrs = project.mergerequests.list(source_branch=branch_name, state='all')
        mr_info = None
        merged_into = None
        
        if mrs:
            mr = mrs[0]  # Get the first MR (most recent)
            mr_info = f"!{mr.iid} ({mr.web_url})"
            if mr.state == 'merged':
                merged_into = mr.target_branch
        
        return {
            'last_commit_author': last_commit_author,
            'last_commit_date': last_commit_date,
            'is_protected': is_protected,
            'merged_into': merged_into,
            'merge_request': mr_info
        }
    except gitlab.exceptions.GitlabError as e:
        print(f"Error getting branch details: {e}")
        return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python gitlab_branch_report.py <group_path>")
        sys.exit(1)
    
    group_path = sys.argv[1]
    gl = get_gitlab_connection()
    
    try:
        # Get the group
        group = gl.groups.get(group_path)
        
        # Get all projects in the group
        projects = group.projects.list(all=True)
        
        report_data = []
        
        for project in projects:
            # Get the full project object
            proj = gl.projects.get(project.id)
            print(f"\nProcessing project: {proj.name}")
            
            # Get all branches
            branches = proj.branches.list(all=True)
            
            for branch in branches:
                print(f"Processing branch: {branch.name}")
                details = get_branch_details(proj, branch.name)
                
                if details:
                    report_data.append([
                        proj.name,
                        branch.name,
                        details['last_commit_author'],
                        details['last_commit_date'].strftime('%Y-%m-%d %H:%M:%S'),
                        'Yes' if details['is_protected'] else 'No',
                        details['merged_into'] if details['merged_into'] else 'No',
                        details['merge_request'] if details['merge_request'] else 'No'
                    ])
        
        # Print the report
        headers = ['Project', 'Branch', 'Last Commit Author', 'Last Commit Date', 
                  'Protected', 'Merged Into', 'Merge Request']
        print("\n" + tabulate(report_data, headers=headers, tablefmt='grid'))
        
    except gitlab.exceptions.GitlabError as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
