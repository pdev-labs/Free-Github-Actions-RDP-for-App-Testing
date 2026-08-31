import os
import argparse
import sys
from config import load_profile, save_profile
from engine import generate_workflow
from github_api import run_command, ensure_git_config, check_gh_auth, get_gh_user

import shutil
import subprocess
import time
import re
import threading
import json
import socket
from http.server import SimpleHTTPRequestHandler, HTTPServer
from InquirerPy import inquirer
from InquirerPy.validator import EmptyInputValidator
from InquirerPy.base.control import Choice
from rich.console import Console
from rich.spinner import Spinner

console = Console()

import json
import os



def start_p2p_server(iso_dir, base_dir):
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    print("Starting local HTTP server for P2P streaming...")
    http_proc = subprocess.Popen([sys.executable, "-m", "http.server", str(port)], cwd=iso_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print("Opening local Pinggy tunnel for P2P...")
    pinggy_log_path = os.path.join(base_dir, "pinggy_p2p.log")
    pinggy_proc = subprocess.Popen(f"ssh -T -p 443 -R0:localhost:{port} -o StrictHostKeyChecking=no -o ServerAliveInterval=30 tcp@a.pinggy.io > {pinggy_log_path} 2>&1", shell=True)
    
    for _ in range(30):
        time.sleep(1)
        if os.path.exists(pinggy_log_path):
            with open(pinggy_log_path, "r") as f:
                content = f.read()
                match = re.search(r"https://[a-zA-Z0-9.-]+", content)
                if match:
                    return http_proc, pinggy_proc, match.group(0)
    
    print("Error: Failed to start Pinggy tunnel for P2P streaming.")
    http_proc.terminate()
    pinggy_proc.terminate()
    sys.exit(1)





def main():
    if not shutil.which("gh"):
        print("Error: GitHub CLI ('gh') is not installed. Please install it to proceed.")
        sys.exit(1)
        
    if not shutil.which("git"):
        print("Error: 'git' is not installed. Please install it to proceed.")
        sys.exit(1)

    console.print("[bold cyan]Welcome to the GitHub Actions RDP Provisioner[/bold cyan]")
    console.print("[dim]" + "-" * 50 + "[/dim]")
    
    loaded_profile = load_profile()
    if loaded_profile:
        repo_name = loaded_profile.get('repo_name', 'cloud-desktop')
        gh_user = loaded_profile.get('gh_user', '')
        os_choice = loaded_profile.get('os_choice', 'linux')
        version_choice = loaded_profile.get('version_choice', 'ubuntu:latest')
        architecture = loaded_profile.get('architecture', 'amd64')
        de_choice = loaded_profile.get('de_choice', 'xfce')
        app_choice_str = loaded_profile.get('app_choice_str', '')
        custom_download_logic = loaded_profile.get('custom_download_logic', '')
        method = loaded_profile.get('method', '')
        tag = loaded_profile.get('tag', 'v1.0')
        iso_path = loaded_profile.get('iso_path', '')
        iso_name = loaded_profile.get('iso_name', 'custom.iso')
        file_size_gb = loaded_profile.get('file_size_gb', 0)
        tunnel = loaded_profile.get('tunnel', 'pinggy')
        ngrok_token = loaded_profile.get('ngrok_token', '')
        pub_key = loaded_profile.get('pub_key', '')
    else:
        check_gh_auth()
        
        gh_user = get_gh_user()
    
        repo_name = inquirer.text(
            message="Enter a name for the GitHub repository (e.g., my-rdp-testing):",
            validate=EmptyInputValidator()
        ).execute().strip()
    
        repo_exists = False
        try:
            subprocess.run(["gh", "repo", "view", f"{gh_user}/{repo_name}"], capture_output=True, check=True)
            repo_exists = True
        except subprocess.CalledProcessError:
            pass
    
        if repo_exists:
            clean = inquirer.confirm(
                message=f"WARNING: The repository '{gh_user}/{repo_name}' already exists.\nDo you want to clean it and reuse it? This will overwrite the repo.",
                default=True
            ).execute()
            if not clean:
                print("Aborting.")
                sys.exit(1)

            cancel_runs = inquirer.confirm(
                message="Do you want to stop all currently running Actions in this repository to free up resources?",
                default=True
            ).execute()
            
            if cancel_runs:
                print("Fetching active workflows...")
                try:
                    runs_output = subprocess.run(
                        ["gh", "run", "list", "-R", f"{gh_user}/{repo_name}", "--status", "in_progress", "--json", "databaseId", "-q", ".[].databaseId"],
                        capture_output=True, text=True, check=True
                    ).stdout.strip().split("\n")
                    runs = [r for r in runs_output if r]
                    if runs:
                        for run_id in runs:
                            subprocess.run(["gh", "run", "cancel", run_id, "-R", f"{gh_user}/{repo_name}"], capture_output=True)
                        print(f"Successfully stopped {len(runs)} running workflow(s).")
                    else:
                        print("No active workflows found.")
                except subprocess.CalledProcessError:
                    print("Failed to fetch or cancel workflows. Ignoring...")
    
        os_choices = {
            "windows": ["windows-latest", "windows-2022", "windows-2019"],
            "macos": [
                Choice("macos-latest", "macos-latest (Apple Silicon - VNC Broken/Black Screen. Use CLI mode!)"),
                Choice("macos-14", "macos-14 (Apple Silicon - VNC Broken/Black Screen. Use CLI mode!)"),
                Choice("macos-13", "macos-13 (Intel - VNC Supported but Deprecating soon)")
            ],
            "linux": [
                "ubuntu:latest", "ubuntu:22.04", "ubuntu:20.04",
                "debian:latest", "debian:bullseye",
                "kalilinux/kali-rolling",
                "archlinux:latest",
                "fedora:latest", "fedora:39",
                "linuxmintd/mint21.2-amd64",
                "manjaro/base:latest"
            ],
            "android": ["Android-x86 9.0 (Stable)"],
            "custom_iso": ["Custom Local ISO (QEMU Nested Virtualization)"]
        }
        
        os_choice = inquirer.select(
            message="Which OS do you want to test on?",
            choices=[
                Choice("windows", "Windows"),
                Choice("linux", "Linux"),
                Choice("macos", "macOS"),
                Choice("android", "Android"),
                Choice("custom_iso", "Custom ISO")
            ]
        ).execute()
    
        version_choice = "latest"
        architecture = "amd64"
        de_choice = "xfce"
        app_choice_str = ""
        custom_download_logic = ""
        p2p_procs = None
    
        if os_choice not in ["custom_iso", "android"]:
            if os_choice == "macos":
                version_choice = inquirer.select(
                    message=f"Select version/distro for {os_choice}:",
                    choices=os_choices[os_choice]
                ).execute()
            else:
                version_choices = [Choice(v, v) for v in os_choices[os_choice]]
                version_choice = inquirer.select(
                    message=f"Select version/distro for {os_choice}:",
                    choices=version_choices
                ).execute()
    
            if os_choice == "linux":
                architecture = inquirer.select(
                    message="Select CPU architecture for Linux:",
                    choices=[Choice("amd64", "amd64"), Choice("arm64", "arm64")]
                ).execute()
                
                if version_choice.startswith("ubuntu"):
                    de_choices = [
                        Choice("xfce", "XFCE (Native GitHub Runner. Extremely fast)"),
                        Choice("stock", "Stock Ubuntu GNOME (QEMU Virtual Machine. VERY slow)"),
                        Choice("cli", "cli (No GUI, SSH only. Extremely fast boot)")
                    ]
                else:
                    de_choices = [
                        Choice("stock", "stock (Installs the distro's exact default GUI)"),
                        Choice("xfce", "xfce"),
                        Choice("gnome", "gnome"),
                        Choice("kde", "kde"),
                        Choice("i3", "i3"),
                        Choice("cli", "cli (No GUI, SSH only. Extremely fast boot)")
                    ]
                
                de_choice = inquirer.select(
                    message="Select Desktop Environment / Window Manager:",
                    choices=de_choices
                ).execute()
    
                if version_choice.startswith("ubuntu") and de_choice == "stock":
                    # Redirect to QEMU Custom ISO
                    os_choice = "custom_iso"
                    iso_url = "https://releases.ubuntu.com/24.04.1/ubuntu-24.04.1-desktop-amd64.iso"
                    custom_download_logic = f'''FINAL_URL=$(curl -LIs -o /dev/null -w %{{url_effective}} "{iso_url}")\nwget -O custom.iso "$FINAL_URL"'''
                    method = "url"
                    app_choice_str = ""
                else:
                    app_choices_list = [
                        Choice("0", "Web Browser (Firefox)"),
                        Choice("1", "CLI Editors (nano, vim)"),
                        Choice("2", "Containerization (Docker)"),
                        Choice("3", "Network/Security Tools (Nmap, Netcat, curl, wget)"),
                        Choice("4", "Build Tools (git, gcc, make)"),
                        Choice("5", "DevBox: Hacker (Kali Tools, Metasploit, Wireshark)"),
                        Choice("6", "DevBox: Coder (VSCode, Node.js, Python, Docker)"),
                        Choice("7", "DevBox: Android (Android Studio, SDKs)")
                    ]
                    selected_apps = inquirer.checkbox(
                        message="Select additional apps to pre-install (Space to select, Enter to confirm):",
                        choices=app_choices_list
                    ).execute()
                    app_choice_str = ",".join(selected_apps) if selected_apps else ""
    
            elif os_choice == "macos":
                de_choice = inquirer.select(
                    message="Select interaction mode for macOS:",
                    choices=[
                        Choice("gui", "VNC Desktop (GUI) - Recommended for macos-13 (Intel)"),
                        Choice("cli", "SSH Terminal Only (CLI) - Best for macos-latest (Apple Silicon)")
                    ]
                ).execute()
                
            elif os_choice == "windows":
                de_choice = inquirer.select(
                    message="Select interaction mode for Windows:",
                    choices=[
                        Choice("gui", "RDP Desktop (GUI) - Standard Windows Desktop"),
                        Choice("cli", "SSH Terminal Only (CLI) - PowerShell/CMD over SSH")
                    ]
                ).execute()
    
        elif os_choice == "android":
            android_version = inquirer.select(
                message="Select Android version to install:",
                choices=[
                    Choice("15", "Android 15 (Zenith / Bliss OS) - *Requires Custom ISO link*"),
                    Choice("14", "Android 14 (Bliss OS 16) - *Requires Custom ISO link*"),
                    Choice("13", "Android 13 (Bliss OS) - *Requires Custom ISO link*"),
                    Choice("12", "Android 12L (Bliss OS 15) - *Requires Custom ISO link*"),
                    Choice("11", "Android 11 (Bliss OS 14) - *Requires Custom ISO link*"),
                    Choice("10", "Android 10 (Bliss OS 12) - *Requires Custom ISO link*"),
                    Choice("9.0", "Android-x86 9.0 Pie (Stable & Recommended)"),
                    Choice("8.1", "Android-x86 8.1 Oreo (Legacy)"),
                    Choice("7.1", "Android-x86 7.1 Nougat (Legacy)"),
                    Choice("6.0", "Android-x86 6.0 Marshmallow (Legacy)"),
                    Choice("5.1", "Android-x86 5.1 Lollipop (Legacy)"),
                    Choice("4.4", "Android-x86 4.4 KitKat (Legacy)")
                ]
            ).execute()
            
            if android_version in ["15", "14", "13", "12", "11", "10"]:
                print(f"\\n[!] The official Android-x86 project stopped at Android 9.0.")
                print(f"[!] To run Android {android_version}, you must use community projects like Bliss OS.")
                print(f"[!] Please restart the script, select 'Custom ISO', and paste a direct download link from https://sourceforge.net/projects/blissos-x86/")
                sys.exit(0)
            
            if android_version == "9.0":
                iso_url = "https://sourceforge.net/projects/android-x86/files/Release%209.0/android-x86_64-9.0-r2.iso/download"
            elif android_version == "8.1":
                iso_url = "https://sourceforge.net/projects/android-x86/files/Release%208.1/android-x86_64-8.1-r6.iso/download"
            elif android_version == "7.1":
                iso_url = "https://sourceforge.net/projects/android-x86/files/Release%207.1/android-x86_64-7.1-r5.iso/download"
            elif android_version == "6.0":
                iso_url = "https://sourceforge.net/projects/android-x86/files/Release%206.0/android-x86_64-6.0-r3.iso/download"
            elif android_version == "5.1":
                iso_url = "https://sourceforge.net/projects/android-x86/files/Release%205.1/android-x86_64-5.1-rc1.iso/download"
            else:
                iso_url = "https://sourceforge.net/projects/android-x86/files/Release%204.4/android-x86-4.4-r5.iso/download"
                
            downloader = inquirer.select(
                message="Select the download engine for the ISO:",
                choices=[
                    Choice("aria2c", "aria2c (Multi-connection, faster)"),
                    Choice("wget", "wget (Single-connection, highly reliable)")
                ]
            ).execute()
            if downloader == "aria2c":
                connections = inquirer.text(
                    message="Enter the number of concurrent connections for aria2c (e.g., 16, 8, 4):",
                    default="16",
                    validate=lambda x: x.isdigit() and int(x) > 0
                ).execute().strip()
                custom_download_logic = f'''FINAL_URL=$(curl -LIs -o /dev/null -w %{{url_effective}} "{iso_url}")\naria2c -x {connections} -s {connections} -k 1M -o custom.iso "$FINAL_URL" || wget -O custom.iso "$FINAL_URL"'''
            else:
                custom_download_logic = f'''FINAL_URL=$(curl -LIs -o /dev/null -w %{{url_effective}} "{iso_url}")\nwget -O custom.iso "$FINAL_URL"'''
            base_dir = os.path.join(os.getcwd(), ".workspaces", repo_name)
            method = "url"
        else:
            # Custom ISO Logic
            source_choice = inquirer.select(
                message="Select Custom ISO source:",
                choices=[
                    Choice("1", "Local File (I have the ISO downloaded on my PC)"),
                    Choice("2", "Direct URL (I have an HTTP/HTTPS link to the ISO)")
                ]
            ).execute()
                
            custom_download_logic = ""
            base_dir = os.path.join(os.getcwd(), ".workspaces", repo_name)
            
            if source_choice == "2":
                iso_url = inquirer.text(
                    message="Enter the direct HTTP/HTTPS URL to the ISO file:",
                    validate=lambda x: x.startswith("http")
                ).execute().strip()
                downloader = inquirer.select(
                    message="Select the download engine for the ISO:",
                    choices=[
                        Choice("aria2c", "aria2c (Multi-connection, faster)"),
                        Choice("wget", "wget (Single-connection, highly reliable)")
                    ]
                ).execute()
                if downloader == "aria2c":
                    connections = inquirer.text(
                        message="Enter the number of concurrent connections for aria2c (e.g., 16, 8, 4):",
                        default="16",
                        validate=lambda x: x.isdigit() and int(x) > 0
                    ).execute().strip()
                    custom_download_logic = f'''FINAL_URL=$(curl -LIs -o /dev/null -w %{{url_effective}} "{iso_url}")\naria2c -x {connections} -s {connections} -k 1M -o custom.iso "$FINAL_URL" || wget -O custom.iso "$FINAL_URL"'''
                else:
                    custom_download_logic = f'''FINAL_URL=$(curl -LIs -o /dev/null -w %{{url_effective}} "{iso_url}")\nwget -O custom.iso "$FINAL_URL"'''
                method = "url"
            else:
                iso_path = inquirer.filepath(
                    message="Enter the absolute path to your local .iso file:",
                    validate=lambda x: os.path.isfile(x),
                    only_files=True
                ).execute().strip()
                
                file_size_gb = os.path.getsize(iso_path) / (1024 ** 3)
                print(f"ISO Size: {file_size_gb:.2f} GB")
                
                method = inquirer.select(
                    message="Select Transfer Method:",
                    choices=[
                        Choice("1", "GitHub Releases (Cloud) - Automatically uploads and runs autonomously."),
                        Choice("2", "Peer-to-Peer (Local Stream) - Streams directly from your PC (requires terminal to stay open).")
                    ]
                ).execute()
                    
                if not os.path.exists(base_dir):
                    os.makedirs(base_dir, exist_ok=True)
                    
                iso_name = os.path.basename(iso_path)
                iso_dir = os.path.dirname(iso_path)
    
                if method == "1":
                    tag = f"iso-{int(time.time())}"
                    if file_size_gb > 1.9:
                        custom_download_logic = f'gh release download {tag} --pattern "*"\\ncat {iso_name}.part* > custom.iso'
                        # Upload logic will happen AFTER git push
                    else:
                        custom_download_logic = f'gh release download {tag} -p "{iso_name}"\\nmv "{iso_name}" custom.iso'
                else:
                    http_proc, pinggy_proc, p2p_url = start_p2p_server(iso_dir, base_dir)
                    p2p_procs = (http_proc, pinggy_proc)
                    custom_download_logic = f'wget "{p2p_url}/{iso_name}" -O custom.iso'
    
        print("\n[1/4] Creating local directory structure...")
        base_dir = os.path.join(os.getcwd(), ".workspaces", repo_name)
        if os.path.exists(base_dir) and not (os_choice in ["custom_iso", "android"] and method == "1"):
            shutil.rmtree(base_dir)
        os.makedirs(base_dir, exist_ok=True)
            
        workflow_dir = os.path.join(base_dir, ".github", "workflows")
        os.makedirs(workflow_dir, exist_ok=True)
        
        
    enable_cache = inquirer.confirm(message="Enable GitHub Actions caching for faster boots (caches apt/brew packages)?").execute()
    
    if not loaded_profile:
        tunnel = inquirer.select(
            message="Select Tunneling Provider:",
            choices=[
                Choice("pinggy", "Pinggy (Free, No Auth, 60-min limit)"),
                Choice("ngrok", "Ngrok (Free Auth Token Required, Persistent 6-hour limit)"),
                Choice("cloudflare", "Cloudflare Tunnels (Free, No Auth, Infinite Time, Requires local cloudflared)"),
                Choice("tailscale", "Tailscale VPN (Free, Auth Key Required, Infinite Time, Secure Private Network)")
            ]
        ).execute()
        
        ngrok_token = ""
        if tunnel == "ngrok":
            ngrok_token = inquirer.secret(
                message="Enter your Ngrok Auth Token:"
            ).execute().strip()
        elif tunnel == "tailscale":
            key_choice = inquirer.select(
                message="How do you want to handle your Tailscale Auth Key?",
                choices=[
                    Choice("secret", "Set as a secure GitHub Secret (Recommended)"),
                    Choice("direct", "Inject directly into the workflow file (Less secure)")
                ]
            ).execute()
            
            ts_key = inquirer.secret(
                message="Enter your Tailscale Auth Key:"
            ).execute().strip()
            
            if key_choice == "secret":
                print("\n[+] Setting Tailscale Auth Key as a GitHub Secret...")
                try:
                    subprocess.run(["gh", "secret", "set", "TAILSCALE_AUTHKEY", "--body", ts_key], check=True)
                    ngrok_token = "${{ secrets.TAILSCALE_AUTHKEY }}"
                except subprocess.CalledProcessError:
                    print("[!] ERROR: Your GitHub token lacks permissions to set repository secrets.")
                    print("[!] Falling back to direct injection into the workflow file...")
                    ngrok_token = ts_key
            else:
                ngrok_token = ts_key
    
    pub_key = ""
    if os_choice in ["macos", "linux", "windows"] and de_choice == "cli":
        gen_ssh = inquirer.confirm(message="Would you like to auto-generate an SSH key for connection?").execute()
        if gen_ssh:
            key_name = f"{os_choice}_runner_key"
            if not os.path.exists(key_name):
                print(f"\\nGenerating SSH key pair for {os_choice} CLI access...")
                subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", key_name, "-N", "", "-q"], check=True)
            with open(f"{key_name}.pub", "r") as f:
                pub_key = f.read().strip()
            print(f"[!] You can connect using: ssh -i {key_name} ...")
        else:
            pub_key = inquirer.text(message="Enter your public SSH key:").execute().strip()

    profile_data = {
        'repo_name': repo_name,
        'gh_user': gh_user,
        'os_choice': os_choice,
        'version_choice': version_choice,
        'architecture': architecture,
        'de_choice': de_choice,
        'app_choice_str': app_choice_str,
        'custom_download_logic': custom_download_logic,
        'method': method,
        'tag': tag,
        'iso_path': iso_path,
        'iso_name': iso_name,
        'file_size_gb': file_size_gb,
        'tunnel': tunnel,
        'ngrok_token': ngrok_token,
        'pub_key': pub_key
    }
    
    if not loaded_profile:
        save_profile(profile_data)

    import secrets
    password = secrets.token_urlsafe(12)
    workflow_yml = generate_workflow(password, enable_cache, os_choice, version_choice, architecture, de_choice, app_choice_str, custom_download_logic, pub_key, tunnel, ngrok_token)
    workflow_yml = workflow_yml.replace('echo "==========================================================="', 'if [ ! -z "$GITHUB_STEP_SUMMARY" ]; then\n                echo "### 🚀 Connection URL: $URL" >> $GITHUB_STEP_SUMMARY\n            fi\n            echo "==========================================================="', 1)
    workflow_path = os.path.join(workflow_dir, "rdp.yml")
    with open(workflow_path, "w") as f:
        f.write(workflow_yml)

    console.print("[bold green][2/4] Initializing Git repository...[/bold green]")
    run_command(["git", "init"], cwd=base_dir)
    ensure_git_config(base_dir)
    run_command(["git", "branch", "-M", "main"], cwd=base_dir)
    run_command(["git", "add", "."], cwd=base_dir)
    run_command(["git", "commit", "-m", "Initial commit: Add RDP workflow"], cwd=base_dir)

    console.print("[bold green][3/4] Setting up GitHub repository...[/bold green]")
    try:
        check_repo = subprocess.run(["gh", "api", f"repos/{gh_user}/{repo_name}"], capture_output=True, text=True)
        if check_repo.returncode == 0:
            print("Force pushing to existing repository...")
            subprocess.run(["git", "remote", "add", "origin", f"https://github.com/{gh_user}/{repo_name}.git"], cwd=base_dir, capture_output=True)
            run_command(["git", "push", "-f", "origin", "main"], cwd=base_dir)
            subprocess.run(["gh", "api", "-X", "PATCH", f"repos/{gh_user}/{repo_name}", "-f", "default_branch=main"], capture_output=True)
        else:
            result = subprocess.run(["gh", "repo", "create", repo_name, "--private", "--source=.", "--remote=origin", "--push"], cwd=base_dir, capture_output=True, text=True)
            if result.returncode != 0:
                if "already exists" in result.stderr or "already exists" in result.stdout:
                    print("Force pushing to existing repository...")
                    subprocess.run(["git", "remote", "add", "origin", f"https://github.com/{gh_user}/{repo_name}.git"], cwd=base_dir, capture_output=True)
                    run_command(["git", "push", "-f", "origin", "main"], cwd=base_dir)
                    subprocess.run(["gh", "api", "-X", "PATCH", f"repos/{gh_user}/{repo_name}", "-f", "default_branch=main"], capture_output=True)
                else:
                    print(f"Error creating repository: {result.stderr.strip()}")
                    sys.exit(1)
    except Exception as e:
        print(f"Error setting up repository: {e}")
        sys.exit(1)

    # Post-push steps for Custom ISO Method 1 (GitHub Releases)
    if os_choice == "custom_iso" and method == "1":
        print("\\n[+] Creating GitHub Release for ISO upload...")
        subprocess.run(["gh", "release", "create", tag, "--title", "Custom ISO", "--notes", "Automated upload"], cwd=base_dir, check=True)
        if file_size_gb > 1.9:
            print("[+] ISO is larger than 1.9GB. Splitting file into parts (this may take a minute)...")
            subprocess.run(["split", "-b", "1900M", iso_path, f"{iso_name}.part"], cwd=base_dir, check=True)
            print("[+] Uploading split parts to GitHub Release...")
            subprocess.run(f"gh release upload {tag} {iso_name}.part*", shell=True, cwd=base_dir, check=True)
            subprocess.run(f"rm -f {iso_name}.part*", shell=True, cwd=base_dir)
        else:
            print("[+] Uploading ISO to GitHub Release...")
            subprocess.run(["gh", "release", "upload", tag, iso_path], cwd=base_dir, check=True)

    console.print("[bold green][4/4] Provisioning complete![/bold green]")
    console.print("[dim]" + "-" * 50 + "[/dim]")
    print("Next steps:")
    
    console.print(f"\n[bold cyan]Workflow URL:[/bold cyan] [bold underline blue]https://github.com/{gh_user}/{repo_name}/actions/workflows/rdp.yml[/bold underline blue]\n")
    console.print(f"\n[bold green]Generated Password:[/bold green] [bold white]{password}[/bold white]\n")
    
    print("\nTriggering the GitHub Action workflow automatically...")
    
    max_retries = 6
    for attempt in range(max_retries):
        try:
            time.sleep(5) # Wait for GitHub's backend to parse the newly pushed workflow file
            subprocess.run(["gh", "workflow", "run", "rdp.yml", "-R", f"{gh_user}/{repo_name}"], cwd=base_dir, check=True, capture_output=True)
            print("Workflow triggered successfully!")
            break
        except subprocess.CalledProcessError as e:
            if attempt < max_retries - 1:
                print(f"Waiting for GitHub API to sync workflow (Attempt {attempt + 1}/{max_retries})...")
            else:
                print("Error triggering the workflow automatically.")
                print(f"     cd {repo_name} && gh workflow run rdp.yml")
    
    console.print("[dim]" + "-" * 50 + "[/dim]")
    print("The environment is booting up now. Please allow 1-3 minutes for it to start.")
    
    try:
        with console.status("[bold cyan]Fetching logs from GitHub Actions (waiting for runner to boot)...[/bold cyan]") as status:
            run_id = None
            for _ in range(15):
                res = subprocess.run(["gh", "run", "list", "-w", "rdp.yml", "-L", "1", "--json", "databaseId", "-q", ".[0].databaseId"], cwd=base_dir, capture_output=True, text=True)
                if res.stdout.strip() and res.stdout.strip() != "null":
                    run_id = res.stdout.strip()
                    break
                time.sleep(4)
            
            if run_id:
                url_found = False
                for _ in range(40): # 40 * 5 = 200 seconds
                    log_res = subprocess.run(["gh", "run", "view", run_id, "--log"], cwd=base_dir, capture_output=True, text=True)
                    logs = log_res.stdout
                    if "Connect using" in logs:
                        url_found = True
                        address = ""
                        user = ""
                        for line in logs.split('\n'):
                            if "Connect using" in line:
                                address = line.strip()
                            elif "Username:" in line:
                                user = line.split("Username:")[1].strip()
                        
                        console.print("\n[bold green]🎉 Your Cloud Desktop is Ready![/bold green]")
                        console.print(f"[bold cyan]URL/Command:[/bold cyan] [bold white]{address}[/bold white]")
                        if user:
                            console.print(f"[bold cyan]Username:[/bold cyan] [bold white]{user}[/bold white]")
                        console.print(f"[bold cyan]Password:[/bold cyan] [bold white]{password}[/bold white]")
                        break
                    time.sleep(5)
                    
                if not url_found:
                    console.print("[bold red]Timeout waiting for tunnel details in logs. Please check the GitHub Actions UI manually.[/bold red]")
                    console.print(f"Workflow URL: https://github.com/{gh_user}/{repo_name}/actions/workflows/rdp.yml")
            else:
                console.print("[bold red]Could not find active Workflow Run ID. Please check the GitHub Actions UI manually.[/bold red]")
                console.print(f"Workflow URL: https://github.com/{gh_user}/{repo_name}/actions/workflows/rdp.yml")
    except Exception as e:
        console.print(f"[dim]Could not automatically fetch logs: {e}[/dim]")
        
    console.print("\n[bold magenta]All done![/bold magenta]")
    
    if tunnel == "pinggy":
        print(f"   * NOTE: The Pinggy free tier will disconnect after 60 minutes, but this script will auto-reconnect it.")
    elif tunnel == "ngrok":
        print(f"   * NOTE: The Ngrok tunnel will persist for up to 6 hours.")
    elif tunnel == "cloudflare":
        print(f"   * NOTE: Cloudflare tunnels are infinite. Use 'cloudflared access' locally to connect.")
    elif tunnel == "tailscale":
        print(f"   * NOTE: Tailscale VPN is active. Connect using the 100.x.x.x IP Address.")

    # Block terminal if P2P is active
    if p2p_procs:
        http_proc, pinggy_proc = p2p_procs
        print("\n" + "="*60)
        print("!!! WARNING: P2P STREAMING ACTIVE !!!")
        print("DO NOT CLOSE THIS TERMINAL.")
        print("Your local machine is currently serving the ISO file.")
        print("The GitHub Action will pull it directly from your computer.")
        print("Please keep this terminal open until the Action finishes downloading.")
        print("Press Ctrl+C to terminate the server when done.")
        print("="*60)
        try:
            http_proc.wait()
        except KeyboardInterrupt:
            print("\\nShutting down P2P server...")
            http_proc.terminate()
            pinggy_proc.terminate()

if __name__ == "__main__":
    main()
