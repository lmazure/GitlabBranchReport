import os
import sys
from datetime import datetime
import gitlab
from dateutil import parser
import jinja2
import webbrowser

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
            mr_info = f"<A HREF='{mr.web_url}' TARGET='_blank'>!{mr.iid}</A>"
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

def get_all_projects(gl, group):
    """Recursively get all projects from a group and its subgroups."""
    print(f"Getting projects from group: {group.full_path}")
    
    projects = []
    
    # Get direct projects from this group
    projects.extend(group.projects.list(all=True))
    
    # Get subgroups and their projects
    subgroups = group.subgroups.list(all=True)
    for subgroup in subgroups:
        # Get the full subgroup object
        full_subgroup = gl.groups.get(subgroup.id)
        # Recursively get projects from subgroup
        projects.extend(get_all_projects(gl, full_subgroup))
    
    return projects

def generate_html_report(report_data, group_path):
    """Generate an HTML report from the branch data."""
    template = """
<!DOCTYPE html>
<html>
<head>
    <title>GitLab Branch Report - {{ group_path }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2f2f2f;
            margin-bottom: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #4a4a4a;
            color: white;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .timestamp {
            text-align: right;
            color: #666;
            font-size: 0.9em;
            margin-top: 20px;
        }
        a {
            color: #1a73e8;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>GitLab Branch Report - {{ group_path }}</h1>
        <table>
            <thead>
                <tr>
                    {% for header in headers %}
                    <th>{{ header }}</th>
                    {% endfor %}
                </tr>
            </thead>
            <tbody>
                {% for row in data %}
                <tr>
                    {% for cell in row %}
                    <td>{{ cell }}</td>
                    {% endfor %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <div class="timestamp">
            Report generated on: {{ timestamp }}
        </div>
    </div>
</body>
</html>
    """
    
    headers = ['Project', 'Branch', 'Last Commit Author', 'Last Commit Date', 
              'Protected', 'Merged Into', 'Merge Request']
    
    # Create Jinja2 environment and template
    env = jinja2.Environment()
    template = env.from_string(template)
    
    # Generate HTML
    html_content = template.render(
        headers=headers,
        data=report_data,
        group_path=group_path,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    
    # Write to file
    output_file = f'gitlab_branch_report_{group_path.replace("/", "_")}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Get absolute path for the file
    abs_path = os.path.abspath(output_file)
    return abs_path

def main():
    if len(sys.argv) != 2:
        print("Usage: python gitlab_branch_report.py <group_path>")
        sys.exit(1)
    
    group_path = sys.argv[1]
    gl = get_gitlab_connection()
    
    try:
        # Get the group
        group = gl.groups.get(group_path)
        
        # Get all projects recursively
        print("\nFetching all projects from group and subgroups...")
        all_projects = get_all_projects(gl, group)
        print(f"Found {len(all_projects)} projects in total")
        
        report_data = []
        
        for project in all_projects:
            # Get the full project object
            proj = gl.projects.get(project.id)
            print(f"\nProcessing project: {proj.path_with_namespace}")
            
            # Get all branches
            branches = proj.branches.list(all=True)
            
            for branch in branches:
                print(f"Processing branch: {branch.name}")
                details = get_branch_details(proj, branch.name)
                
                if details:
                    report_data.append([
                        f"<A HREF='{proj.web_url}' TARGET='_blank'>{proj.path_with_namespace}</A>",
                        f"<A HREF='{proj.web_url}/tree/{branch.name}' TARGET='_blank'>{branch.name}</A>",
                        details['last_commit_author'],
                        details['last_commit_date'].strftime('%Y-%m-%d %H:%M:%S'),
                        'Yes' if details['is_protected'] else 'No',
                        details['merged_into'] if details['merged_into'] else '',
                        details['merge_request'] if details['merge_request'] else ''
                    ])
        
        # Generate HTML report and open it in browser
        output_file = generate_html_report(report_data, group_path)
        print(f"\nReport generated successfully: {output_file}")
        
        # Open the report in the default web browser
        webbrowser.open('file://' + output_file)
        
    except gitlab.exceptions.GitlabError as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
