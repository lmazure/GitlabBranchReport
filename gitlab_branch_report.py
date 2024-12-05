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
        last_committer = commit['committer_name']
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
            'last_committer': last_committer,
            'last_commit_date': last_commit_date,
            'is_protected': is_protected,
            'merged_into': merged_into,
            'merge_request': mr_info
        }
    except gitlab.exceptions.GitlabError as e:
        print(f"Error getting branch details: {e}")
        return None

def get_details_of_all_branches_of_project(project):

    branch_data = []

    # Get all branches
    try:
        branches = project.branches.list(all=True)
    except gitlab.exceptions.GitlabError as e:
        print(f"Error getting branches of project {project.path_with_namespace}: {e}")
        sys.exit(1)
    
    for branch in branches:
        print(f"Processing branch: {branch.name}")
        details = get_branch_details(project, branch.name)
    
        if details:
            branch_data.append([
                f"<A HREF='{project.web_url}' TARGET='_blank'>{project.path_with_namespace}</A>",
                f"<A HREF='{project.web_url}/tree/{branch.name}' TARGET='_blank'>{branch.name}</A>",
                details['last_committer'],
                details['last_commit_date'].strftime('%Y-%m-%d %H:%M:%S'),
                'Yes' if details['is_protected'] else 'No',
                details['merged_into'] if details['merged_into'] else '',
                details['merge_request'] if details['merge_request'] else ''
            ])

    # Sort branch data by commit date (oldest first)
    branch_data.sort(key=lambda x: datetime.strptime(x[3], '%Y-%m-%d %H:%M:%S'))

    return branch_data

def get_all_projects_of_group(gl, group):
    """Recursively get all projects from a group and its subgroups."""
    print(f"Getting projects from group: {group.full_path}")
    
    projects = []
    
    # Get direct projects from this group
    try:
        groups = group.projects.list(all=True)
    except gitlab.exceptions.GitlabError as e:
        print(f"Error getting projects of group {group.full_path}: {e}")
        sys.exit(1)
    projects.extend(groups)
    
    # Get subgroups and their projects
    try:
        subgroups = group.subgroups.list(all=True)
    except gitlab.exceptions.GitlabError as e:
        print(f"Error getting subgroups of group {group.full_path}: {e}")
        sys.exit(1)
    for subgroup in subgroups:
        # Get the full subgroup object
        try:
            full_subgroup = gl.groups.get(subgroup.id)
        except gitlab.exceptions.GitlabError as e:
            print(f"Error getting group {subgroup.id}: {e}")
            sys.exit(1)
        # Recursively get projects from subgroup
        projects.extend(get_all_projects_of_group(gl, full_subgroup))
    
    return projects

def get_all_projects(gl, path):
    try:
        # If path is a project, return it
        project = gl.projects.get(path)
        return [project]
    except gitlab.exceptions.GitlabGetError:
        # If not a project, try as group
        try:
            group = gl.groups.get(path)
        except gitlab.exceptions.GitlabGetError as e:
            print(f"Error while getting group {path}: {e}")
            sys.exit(1)
        return get_all_projects_of_group(gl, group)

def generate_html_report(report_data, path_name):
    """Generate an HTML report from the branch data."""
    template = """
<!DOCTYPE html>
<html>
<head>
    <title>GitLab Branch Report - {{ path_name }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            width: 98%;
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
        .controls {
            margin: 20px 0;
        }
        .checkbox-label {
            display: inline-flex;
            align-items: center;
            cursor: pointer;
            margin-right: 20px;
        }
        .checkbox-label input[type="checkbox"] {
            margin-right: 8px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            table-layout: auto;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .project-path {
            direction: rtl;
            text-align: left;
        }
        th {
            background-color: #4a4a4a;
            color: white;
            position: sticky;
            top: 0;
            z-index: 1;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        td:hover {
            white-space: normal;
            word-wrap: break-word;
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
        tr.protected-branch {
            /* No special styling needed, used for filtering */
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>GitLab Branch Report - {{ path_name }}</h1>
        <div class="controls">
            <label class="checkbox-label">
                <input type="checkbox" id="hideProtectedBranches" checked>
                Hide protected branches
            </label>
        </div>
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
                <tr class="{{ 'protected-branch' if row[4] == 'Yes' }}" style="{{ 'display: none;' if row[4] == 'Yes' }}">
                    <td class="project-path">{{ row[0] }}</td>
                    {% for cell in row[1:] %}
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
    <script>
        // Function to toggle protected branches visibility
        function toggleProtectedBranches(hide) {
            const protectedBranches = document.querySelectorAll('.protected-branch');
            protectedBranches.forEach(row => {
                row.style.display = hide ? 'none' : '';
            });
        }

        // Set up checkbox event listener
        document.getElementById('hideProtectedBranches').addEventListener('change', function(e) {
            toggleProtectedBranches(e.target.checked);
        });

        // Hide protected branches on page load (checkbox is checked by default)
        toggleProtectedBranches(true);
    </script>
</body>
</html>
    """
    
    headers = ['Project', 'Branch', 'Last Committer', 'Last Commit Date', 
               'Protected', 'Merged Into', 'MR']
    
    # Create Jinja2 environment and template
    env = jinja2.Environment()
    template = env.from_string(template)
    
    # Generate HTML
    html_content = template.render(
        headers=headers,
        data=report_data,
        path_name=path_name,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    
    # Write to file
    output_file = f'gitlab_branch_report_{path_name.replace("/", "_")}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Get absolute path for the file
    abs_path = os.path.abspath(output_file)
    return abs_path

def main():
    if len(sys.argv) != 2:
        print("Usage: python gitlab_branch_report.py <group-or-project-path>")
        print("Examples:")
        print("  python gitlab_branch_report.py mygroup")
        print("  python gitlab_branch_report.py mygroup/myproject")
        sys.exit(1)
    
    path = sys.argv[1]
    gl = get_gitlab_connection()
    
    try:
        # Get all projects (single project or all projects in group)
        all_projects = get_all_projects(gl, path)
        print(f"Found {len(all_projects)} projects in total")
        
        report_data = []
        
        for project in all_projects:
            # Get the full project object
            proj = gl.projects.get(project.id)
            print(f"\nProcessing project: {proj.path_with_namespace}")
            report_data.extend(get_details_of_all_branches_of_project(proj))

        # Generate HTML report and open it in browser
        output_file = generate_html_report(report_data, path)
        print(f"\nReport generated successfully: {output_file}")
        webbrowser.open('file://' + output_file)
        
    except gitlab.exceptions.GitlabError as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
