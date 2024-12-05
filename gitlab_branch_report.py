# Standard library imports
import argparse
import os
import sys
import webbrowser
from datetime import datetime

# Third-party imports
from dateutil import parser
import gitlab
import jinja2

def get_gitlab_connection():
    """Create a GitLab connection using personal access token."""
    # Get token from environment variable for security
    token = os.getenv('GITLAB_TOKEN')
    if not token:
        print("Error: GITLAB_TOKEN environment variable not set", flush=True)
        sys.exit(1)
    
    # Get GitLab URL, default to gitlab.com
    gitlab_url = os.getenv('GITLAB_URL', 'https://gitlab.com')
    
    try:
        return gitlab.Gitlab(gitlab_url, private_token=token)
    except Exception as e:
        print(f"Error connecting to GitLab: {e}", flush=True)
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
        mr_state = None
        merged_into = None
        
        if mrs:
            mr = mrs[0]  # Get the first MR (most recent)
            mr_info = f"<A HREF='{mr.web_url}' TARGET='_blank'>!{mr.iid}</A>"
            mr_state = mr.state
            if mr.state == 'merged':
                merged_into = mr.target_branch
        
        return {
            'last_committer': last_committer,
            'last_commit_date': last_commit_date,
            'is_protected': is_protected,
            'merged_into': merged_into,
            'merge_request': mr_info,
            'mr_state': mr_state
        }
    except gitlab.exceptions.GitlabError as e:
        print(f"Error getting branch details: {e}", flush=True)
        return None

def get_details_of_all_branches_of_project(project):

    branch_data = []

    # Get all branches
    try:
        branches = project.branches.list(all=True)
    except gitlab.exceptions.GitlabError as e:
        print(f"Error getting branches of project {project.path_with_namespace}: {e}", flush=True)
        sys.exit(1)
    
    for branch in branches:
        print(f"Processing branch: {branch.name}", flush=True)
        details = get_branch_details(project, branch.name)
    
        if details:
            branch_data.append([
                f"<A HREF='{project.web_url}' TARGET='_blank'>{project.path_with_namespace}</A>",
                f"<A HREF='{project.web_url}/tree/{branch.name}' TARGET='_blank'>{branch.name}</A>",
                details['last_committer'],
                details['last_commit_date'].strftime('%Y-%m-%d %H:%M:%S'),
                'Yes' if details['is_protected'] else 'No',
                details['merged_into'] if details['merged_into'] else '',
                details['merge_request'] if details['merge_request'] else '',
                details['mr_state'] if details['mr_state'] else ''
            ])

    # Sort branch data by commit date (oldest first)
    branch_data.sort(key=lambda x: datetime.strptime(x[3], '%Y-%m-%d %H:%M:%S'))

    return branch_data

def get_all_projects_of_group(gl, group):
    """Recursively get all projects from a group and its subgroups."""
    print(f"Getting projects from group: {group.full_path}", flush=True)
    
    projects = []
    
    # Get direct projects from this group
    try:
        groups = group.projects.list(all=True)
    except gitlab.exceptions.GitlabError as e:
        print(f"Error getting projects of group {group.full_path}: {e}", flush=True)
        sys.exit(1)
    projects.extend(groups)
    
    # Get subgroups and their projects
    try:
        subgroups = group.subgroups.list(all=True)
    except gitlab.exceptions.GitlabError as e:
        print(f"Error getting subgroups of group {group.full_path}: {e}", flush=True)
        sys.exit(1)
    for subgroup in subgroups:
        # Get the full subgroup object
        try:
            full_subgroup = gl.groups.get(subgroup.id)
        except gitlab.exceptions.GitlabError as e:
            print(f"Error getting group {subgroup.id}: {e}", flush=True)
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
            print(f"Error while getting group {path}: {e}", flush=True)
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
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }
        .container {
            width: 100%;
            margin: 0;
            background-color: white;
            padding: 20px;
            box-sizing: border-box;
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
        .age-filter {
            display: inline-flex;
            align-items: center;
            margin-right: 20px;
        }
        .age-filter input[type="number"] {
            width: 70px;
            margin: 0 8px;
            padding: 4px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        .age-filter input[type="number"]:disabled {
            background-color: #f5f5f5;
            cursor: not-allowed;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            table-layout: fixed;
        }
        th, td {
            padding: 12px;
            border-bottom: 1px solid #ddd;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        /* Column widths */
        th:nth-child(1), td:nth-child(1) { /* Project column */
            width: 30%;
            direction: rtl;
            text-align: left;
        }
        th:nth-child(2), td:nth-child(2) { /* Branch column */
            width: 25%;
            direction: ltr;
            text-align: left;
        }
        .project-cell {
            direction: rtl;
            text-align: left;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .branch-cell {
            direction: ltr;
            text-align: left;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
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
        .mr-state {
            text-transform: capitalize;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.9em;
            font-weight: 500;
        }
        .mr-state-opened {
            background-color: #2da44e;
            color: white;
        }
        .mr-state-closed {
            background-color: #cf222e;
            color: white;
        }
        .mr-state-merged {
            background-color: #8250df;
            color: white;
        }
        .date-cell {
            position: relative;
        }
        .date-cell .date-only {
            display: inline-block;
        }
        .date-cell .full-datetime {
            display: none;
            position: absolute;
            background-color: #333;
            color: white;
            padding: 2px 2px;
            font-size: smaller;
            transform: translateY(-80%);
        }
        .date-cell:hover .full-datetime {
            display: block;
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
            <label class="checkbox-label">
                <input type="checkbox" id="hideYoungBranches" checked>
                Only show branches older than
            </label>
            <span class="age-filter">
                <input type="number" id="minAge" value="90" min="1">
                days
            </span>
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
                <tr class="{{ 'protected-branch' if row[4] == 'Yes' }}" 
                    data-commit-date="{{ row[3] }}"
                    style="{{ 'display: none;' if row[4] == 'Yes' }}">
                    <td class="project-cell">{{ row[0] }}</td>
                    <td class="branch-cell">{{ row[1] }}</td>
                    <td>{{ row[2] }}</td>
                    <td class="date-cell">
                        <span class="date-only">{{ row[3].split(' ')[0] }}</span>
                        <span class="full-datetime">{{ row[3] }}</span>
                    </td>
                    <td>{{ row[4] }}</td>
                    <td>{{ row[5] }}</td>
                    <td>{{ row[6] }}</td>
                    <td>
                        {% if row[7] %}
                        <span class="mr-state mr-state-{{ row[7] }}">{{ row[7] }}</span>
                        {% endif %}
                    </td>
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
                // Re-apply age filter if it's active
                if (!hide && document.getElementById('hideYoungBranches').checked) {
                    applyAgeFilter(row);
                }
            });
        }

        // Function to check if a date is within the specified number of days
        function isWithinDays(dateStr, days) {
            const commitDate = new Date(dateStr);
            const now = new Date();
            const diffTime = Math.abs(now - commitDate);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            return diffDays >= days;
        }

        // Function to apply age filter to a single row
        function applyAgeFilter(row) {
            if (!document.getElementById('hideYoungBranches').checked) {
                row.style.display = row.classList.contains('protected-branch') && 
                                  document.getElementById('hideProtectedBranches').checked ? 
                                  'none' : '';
                return;
            }

            const minAge = parseInt(document.getElementById('minAge').value, 10);
            const commitDate = row.getAttribute('data-commit-date');
            const isProtected = row.classList.contains('protected-branch');
            const hideProtected = document.getElementById('hideProtectedBranches').checked;

            if ((isProtected && hideProtected) || !isWithinDays(commitDate, minAge)) {
                row.style.display = 'none';
            } else {
                row.style.display = '';
            }
        }

        // Function to apply age filter to all rows
        function applyAgeFilterToAll() {
            document.querySelectorAll('tbody tr').forEach(applyAgeFilter);
        }

        // Function to format date
        function formatDate(dateStr) {
            const date = new Date(dateStr);
            return {
                dateOnly: date.toISOString().split('T')[0],
                fullDateTime: date.toLocaleString()
            };
        }

        // Set up event listeners
        document.getElementById('hideProtectedBranches').addEventListener('change', function(e) {
            toggleProtectedBranches(e.target.checked);
        });

        document.getElementById('hideYoungBranches').addEventListener('change', function(e) {
            document.getElementById('minAge').disabled = !e.target.checked;
            applyAgeFilterToAll();
        });

        document.getElementById('minAge').addEventListener('input', applyAgeFilterToAll);

        // Initial setup
        toggleProtectedBranches(true);
        applyAgeFilterToAll();
    </script>
</body>
</html>
    """
    
    headers = ['Project', 'Branch', 'Last Committer', 'Last Commit Date', 
               'Protected', 'Merged Into', 'MR', 'MR State']
    
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
    output_file = 'gitlab_branch_report.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Get absolute path for the file
    abs_path = os.path.abspath(output_file)
    return abs_path

def main():
    parser = argparse.ArgumentParser(description='Generate GitLab branch report')
    parser.add_argument('path', help='Group or project path (e.g., mygroup or mygroup/myproject)')
    parser.add_argument('-d', '--display', action='store_true', help='Open the report in browser after generation')
    args = parser.parse_args()
    
    gl = get_gitlab_connection()
    
    try:
        # Get all projects (single project or all projects in group)
        all_projects = get_all_projects(gl, args.path)
        print(f"Found {len(all_projects)} projects in total", flush=True)
        
        report_data = []
        
        for project in all_projects:
            # Get the full project object
            proj = gl.projects.get(project.id)
            print(f"\nProcessing project: {proj.path_with_namespace}", flush=True)
            report_data.extend(get_details_of_all_branches_of_project(proj))

        # Generate HTML report
        output_file = generate_html_report(report_data, args.path)
        print(f"\nReport generated successfully: {output_file}", flush=True)
        
        # Only open in browser if -d flag is used
        if args.display:
            webbrowser.open('file://' + output_file)
        
    except gitlab.exceptions.GitlabError as e:
        print(f"Error: {e}", flush=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
