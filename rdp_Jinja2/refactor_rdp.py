import re

with open('rdp.py', 'r') as f:
    text = f.read()

# Remove the functions we extracted
# 1. load_profile and save_profile
text = re.sub(r'def load_profile\(\):.*?return None\n', '', text, flags=re.DOTALL)
text = re.sub(r'def save_profile\(data\):.*?print\(f"\[\+\] Profile \'{name}\' saved successfully!"\)\n', '', text, flags=re.DOTALL)

# 2. generate_workflow
text = re.sub(r'def generate_workflow\([^)]+\):.*?return template\.render\(context\)\n', '', text, flags=re.DOTALL)
text = re.sub(r'import jinja2\n', '', text)

# 3. run_command, ensure_git_config, check_gh_auth
text = re.sub(r'def run_command\([^)]+\):.*?sys\.exit\(1\)\n', '', text, flags=re.DOTALL)
text = re.sub(r'def ensure_git_config\([^)]+\):.*?actions@github\.com"\], cwd=cwd\)\n', '', text, flags=re.DOTALL)
text = re.sub(r'def check_gh_auth\(\):.*?sys\.exit\(1\)\n', '', text, flags=re.DOTALL)

# Insert imports at the top
imports = """
from config import load_profile, save_profile
from engine import generate_workflow
from github_api import run_command, ensure_git_config, check_gh_auth, get_gh_user
"""
text = text.replace('import sys', 'import sys' + imports)

# Update get_gh_user in main
text = re.sub(r'gh_user = subprocess\.run\(\["gh", "api", "user", "-q", "\.login"\], capture_output=True, text=True, check=True\)\.stdout\.strip\(\)\n\s+except subprocess\.CalledProcessError:\n\s+print\("Failed to retrieve your GitHub username. Exiting."\)\n\s+sys\.exit\(1\)', 'gh_user = get_gh_user()', text)
text = re.sub(r'try:\n\s+gh_user = get_gh_user\(\)', 'gh_user = get_gh_user()', text)

with open('main.py', 'w') as f:
    f.write(text)

print("Refactored main.py created.")
