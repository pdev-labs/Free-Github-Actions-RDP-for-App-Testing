import subprocess
import sys

def run_command(cmd, cwd=None, capture_output=False):
    try:
        return subprocess.run(cmd, cwd=cwd, check=True, capture_output=capture_output)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(cmd)}")
        sys.exit(1)

def ensure_git_config(cwd):
    try:
        user_name = subprocess.run(["git", "config", "user.name"], cwd=cwd, capture_output=True, text=True).stdout.strip()
        user_email = subprocess.run(["git", "config", "user.email"], cwd=cwd, capture_output=True, text=True).stdout.strip()
        
        if not user_name:
            run_command(["git", "config", "user.name", "GitHub Actions Provisioner"], cwd=cwd)
        if not user_email:
            run_command(["git", "config", "user.email", "actions@github.com"], cwd=cwd)
    except subprocess.CalledProcessError:
        run_command(["git", "config", "user.name", "GitHub Actions Provisioner"], cwd=cwd)
        run_command(["git", "config", "user.email", "actions@github.com"], cwd=cwd)

def check_gh_auth():
    result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    if result.returncode != 0:
        print("You are not logged in with GitHub CLI (gh).")
        print("Please run 'gh auth login' to authenticate before using this script.")
        sys.exit(1)

def get_gh_user():
    try:
        return subprocess.run(["gh", "api", "user", "-q", ".login"], capture_output=True, text=True, check=True).stdout.strip()
    except subprocess.CalledProcessError:
        print("Failed to retrieve your GitHub username. Exiting.")
        sys.exit(1)
