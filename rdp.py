import os
import argparse
import sys
import shutil
import subprocess
import time
import re

WINDOWS_WORKFLOW_TEMPLATE = """name: Windows RDP
on: workflow_dispatch
jobs:
  build:
    runs-on: {runner_image}
    timeout-minutes: 9999
    steps:
    - name: Enable RDP Access
      run: |
        Set-ItemProperty -Path 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server' -name "fDenyTSConnections" -value 0
        Enable-NetFirewallRule -DisplayGroup "Remote Desktop"
        Set-ItemProperty -Path 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server\\WinStations\\RDP-Tcp' -name "UserAuthentication" -value 1
        net user runneradmin ThePassword123!
    - name: Start Pinggy tunnel and get connection URL
      shell: bash
      run: |
        ssh -T -p 443 -R0:localhost:3389 -o StrictHostKeyChecking=no -o ServerAliveInterval=30 tcp@a.pinggy.io < /dev/null > pinggy.log 2>&1 &
        sleep 15
        URL=$(grep -o "tcp://.*" pinggy.log | head -n 1)
        if [ ! -z "$URL" ]; then
            echo "==========================================================="
            echo "RDP is Ready!"
            echo "Connect using this address: $URL"
            echo "Username: runneradmin"
            echo "Password: ThePassword123!"
            echo "Note: Pinggy free tier is limited to 60 minutes."
            echo "==========================================================="
            sleep 21600
        else
            echo "Error: Pinggy failed to start. See logs below."
            echo "--- Pinggy Logs ---"
            cat pinggy.log
            exit 1
        fi

"""

LINUX_WORKFLOW_TEMPLATE = """name: Linux Desktop
on: workflow_dispatch
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 9999
    steps:{qemu_setup}
    - name: Provision Linux Desktop
      run: |
        cat << 'EOF' > setup.sh
        #!/bin/bash
        export DEBIAN_FRONTEND=noninteractive
        export USER=runner
        export PASS=ThePassword123!

        OS_ID=$(cat /etc/os-release | grep -E '^ID=' | cut -d= -f2 | tr -d '"')
        DE_CHOICE="{de_choice}"
        APP_CHOICE="{app_choice_str}"
        
        PKG_APT=""
        PKG_PACMAN=""
        PKG_DNF=""
        XSESSION_CMD=""
        
        if [ "$DE_CHOICE" == "xfce" ]; then
            PKG_APT="xfce4 xfce4-goodies"
            PKG_PACMAN="xfce4 xfce4-goodies"
            PKG_DNF="@xfce-desktop"
            XSESSION_CMD="xfce4-session"
        elif [ "$DE_CHOICE" == "gnome" ]; then
            PKG_APT="ubuntu-gnome-desktop"
            PKG_PACMAN="gnome"
            PKG_DNF="@gnome-desktop"
            XSESSION_CMD="gnome-session"
        elif [ "$DE_CHOICE" == "kde" ]; then
            PKG_APT="kde-plasma-desktop"
            PKG_PACMAN="plasma-meta"
            PKG_DNF="@kde-desktop"
            XSESSION_CMD="startplasma-x11"
        elif [ "$DE_CHOICE" == "i3" ]; then
            PKG_APT="i3"
            PKG_PACMAN="i3-wm"
            PKG_DNF="i3"
            XSESSION_CMD="i3"
        elif [ "$DE_CHOICE" == "cli" ]; then
            PKG_APT=""
            PKG_PACMAN=""
            PKG_DNF=""
            XSESSION_CMD="cli"
        elif [ "$DE_CHOICE" == "stock" ]; then
            if [ "$OS_ID" == "ubuntu" ]; then
                PKG_APT="ubuntu-desktop"
                XSESSION_CMD="gnome-session"
            elif [ "$OS_ID" == "kali" ]; then
                PKG_APT="kali-linux-default kali-desktop-xfce"
                XSESSION_CMD="xfce4-session"
            elif [ "$OS_ID" == "debian" ]; then
                PKG_APT="task-gnome-desktop"
                XSESSION_CMD="gnome-session"
            elif [ "$OS_ID" == "linuxmint" ]; then
                PKG_APT="mint-meta-cinnamon"
                XSESSION_CMD="cinnamon-session"
            elif [ "$OS_ID" == "fedora" ]; then
                PKG_DNF="@gnome-desktop"
                XSESSION_CMD="gnome-session"
            elif [ "$OS_ID" == "arch" ] || [ "$OS_ID" == "manjaro" ]; then
                PKG_PACMAN="gnome"
                XSESSION_CMD="gnome-session"
            else
                PKG_APT="xfce4 xfce4-goodies"
                PKG_PACMAN="xfce4 xfce4-goodies"
                PKG_DNF="@xfce-desktop"
                XSESSION_CMD="xfce4-session"
            fi
        fi

        if [[ "$APP_CHOICE" == *"0"* ]]; then
            PKG_APT="$PKG_APT firefox"
            PKG_PACMAN="$PKG_PACMAN firefox"
            PKG_DNF="$PKG_DNF firefox"
        fi
        if [[ "$APP_CHOICE" == *"1"* ]]; then
            PKG_APT="$PKG_APT nano vim"
            PKG_PACMAN="$PKG_PACMAN nano vim"
            PKG_DNF="$PKG_DNF nano vim"
        fi
        if [[ "$APP_CHOICE" == *"2"* ]]; then
            PKG_APT="$PKG_APT docker.io"
            PKG_PACMAN="$PKG_PACMAN docker"
            PKG_DNF="$PKG_DNF docker"
        fi
        if [[ "$APP_CHOICE" == *"3"* ]]; then
            PKG_APT="$PKG_APT nmap netcat-traditional curl wget"
            PKG_PACMAN="$PKG_PACMAN nmap gnu-netcat curl wget"
            PKG_DNF="$PKG_DNF nmap nmap-ncat curl wget"
        fi
        if [[ "$APP_CHOICE" == *"4"* ]]; then
            PKG_APT="$PKG_APT git build-essential"
            PKG_PACMAN="$PKG_PACMAN git base-devel"
            PKG_DNF="$PKG_DNF git @development-tools"
        fi

        echo "Detecting package manager and installing packages..."
        if command -v apt-get >/dev/null; then
            apt-get update
            apt-get install -y sudo openssh-server openssh-client passwd $PKG_APT
            if [ "$DE_CHOICE" != "cli" ]; then
                apt-get install -y xrdp dbus-x11 xorgxrdp
            fi
            useradd -m -s /bin/bash $USER || true
            echo "$USER:$PASS" | chpasswd
            echo "root:$PASS" | chpasswd
            usermod -U $USER || true
            usermod -aG sudo $USER
            mkdir -p /run/sshd
            sed -i 's/required pam_loginuid.so/optional pam_loginuid.so/g' /etc/pam.d/* || true
            /usr/sbin/sshd
            if [ "$DE_CHOICE" != "cli" ]; then
                # Fix XRDP authentication bugs in Docker
                groupadd tsusers || true
                groupadd shadow || true
                usermod -aG tsusers $USER
                usermod -aG ssl-cert $USER || true
                usermod -aG shadow xrdp || true
                adduser xrdp ssl-cert || true
                if [ -f /etc/xrdp/sesman.ini ]; then
                    sed -i 's/TerminalServerUsers=tsusers/#TerminalServerUsers=tsusers/g' /etc/xrdp/sesman.ini
                    sed -i 's/TerminalServerAdmins=tsadmins/#TerminalServerAdmins=tsadmins/g' /etc/xrdp/sesman.ini
                    sed -i 's/AllowRootLogin=false/AllowRootLogin=true/g' /etc/xrdp/sesman.ini
                fi
                # Force completely minimal PAM auth to bypass all Docker container restrictions
                echo "auth required pam_unix.so" > /etc/pam.d/xrdp-sesman
                echo "account required pam_unix.so" >> /etc/pam.d/xrdp-sesman
                echo "password required pam_unix.so" >> /etc/pam.d/xrdp-sesman
                echo "session required pam_unix.so" >> /etc/pam.d/xrdp-sesman
                mkdir -p /run/dbus
                dbus-daemon --system --nofork &
                /etc/init.d/xrdp start
            fi
        elif command -v pacman >/dev/null; then
            pacman -Sy --noconfirm archlinux-keyring
            pacman -Syu --noconfirm sudo openssh git pcre $PKG_PACMAN
            useradd -m -G wheel -s /bin/bash $USER || true
            echo "$USER:$PASS" | chpasswd
            echo "root:$PASS" | chpasswd
            usermod -U $USER || true
            echo "%wheel ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
            ssh-keygen -A
            sed -i 's/required pam_loginuid.so/optional pam_loginuid.so/g' /etc/pam.d/* || true
            /usr/sbin/sshd
            if [ "$DE_CHOICE" != "cli" ]; then
                # Fix XRDP authentication bugs in Docker
                groupadd tsusers || true
                groupadd shadow || true
                usermod -aG tsusers $USER
                usermod -aG shadow xrdp || true
                if [ -f /etc/xrdp/sesman.ini ]; then
                    sed -i 's/TerminalServerUsers=tsusers/#TerminalServerUsers=tsusers/g' /etc/xrdp/sesman.ini
                    sed -i 's/TerminalServerAdmins=tsadmins/#TerminalServerAdmins=tsadmins/g' /etc/xrdp/sesman.ini
                    sed -i 's/AllowRootLogin=false/AllowRootLogin=true/g' /etc/xrdp/sesman.ini
                fi
                echo "auth required pam_unix.so" > /etc/pam.d/xrdp-sesman
                echo "account required pam_unix.so" >> /etc/pam.d/xrdp-sesman
                echo "password required pam_unix.so" >> /etc/pam.d/xrdp-sesman
                echo "session required pam_unix.so" >> /etc/pam.d/xrdp-sesman
                pacman -Syu --noconfirm dbus base-devel
                mkdir -p /run/dbus
                dbus-daemon --system --nofork &
                pacman-key --recv-key 3056513887B78AEB --keyserver keyserver.ubuntu.com
                pacman-key --lsign-key 3056513887B78AEB
                pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst' 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst' --noconfirm || true
                if ! grep -q chaotic-aur /etc/pacman.conf; then
                    echo "[chaotic-aur]" >> /etc/pacman.conf
                    echo "Include = /etc/pacman.d/chaotic-mirrorlist" >> /etc/pacman.conf
                fi
                pacman -Sy --noconfirm xrdp xorgxrdp || { echo "Failed to install xrdp from chaotic-aur. Distro may not be fully compatible."; exit 1; }
                xrdp-keygen xrdp auto
                xrdp && xrdp-sesman
            fi
        elif command -v dnf >/dev/null; then
            dnf install -y sudo openssh-server openssh-clients passwd $PKG_DNF
            if [ "$DE_CHOICE" != "cli" ]; then
                dnf install -y xrdp dbus-x11 epel-release || dnf install -y xrdp dbus-x11
            fi
            useradd -m -G wheel -s /bin/bash $USER || true
            echo "$USER:$PASS" | chpasswd
            echo "root:$PASS" | chpasswd
            usermod -U $USER || true
            echo "%wheel ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
            ssh-keygen -A
            sed -i 's/required pam_loginuid.so/optional pam_loginuid.so/g' /etc/pam.d/* || true
            /usr/sbin/sshd
            if [ "$DE_CHOICE" != "cli" ]; then
                # Fix XRDP authentication bugs in Docker
                groupadd tsusers || true
                groupadd shadow || true
                usermod -aG tsusers $USER
                usermod -aG shadow xrdp || true
                if [ -f /etc/xrdp/sesman.ini ]; then
                    sed -i 's/TerminalServerUsers=tsusers/#TerminalServerUsers=tsusers/g' /etc/xrdp/sesman.ini
                    sed -i 's/TerminalServerAdmins=tsadmins/#TerminalServerAdmins=tsadmins/g' /etc/xrdp/sesman.ini
                    sed -i 's/AllowRootLogin=false/AllowRootLogin=true/g' /etc/xrdp/sesman.ini
                fi
                echo "auth required pam_unix.so" > /etc/pam.d/xrdp-sesman
                echo "account required pam_unix.so" >> /etc/pam.d/xrdp-sesman
                echo "password required pam_unix.so" >> /etc/pam.d/xrdp-sesman
                echo "session required pam_unix.so" >> /etc/pam.d/xrdp-sesman
                mkdir -p /run/dbus
                dbus-daemon --system --nofork &
                xrdp-keygen xrdp auto
                xrdp && xrdp-sesman
            fi
        else
            echo "Unsupported package manager for automated setup"
            exit 1
        fi

        if [ "$DE_CHOICE" != "cli" ]; then
            echo "$XSESSION_CMD" > /home/$USER/.xsession
            chown $USER:$USER /home/$USER/.xsession
        fi

        echo "Starting Pinggy Tunnel..."
        if [ "$DE_CHOICE" == "cli" ]; then
            ssh -T -p 443 -R0:localhost:22 -o StrictHostKeyChecking=no -o ServerAliveInterval=30 tcp@a.pinggy.io > /pinggy.log 2>&1 &
        else
            ssh -T -p 443 -R0:localhost:3389 -o StrictHostKeyChecking=no -o ServerAliveInterval=30 tcp@a.pinggy.io > /pinggy.log 2>&1 &
        fi
        
        sleep 15
        URL=$(grep -o "tcp://.*" /pinggy.log | head -n 1)
        if [ ! -z "$URL" ]; then
            echo "==========================================================="
            if [ "$DE_CHOICE" == "cli" ]; then
                echo "SSH Server is Ready!"
                PORT=$(echo $URL | awk -F':' '{print $3}')
                DOMAIN=$(echo $URL | awk -F'//' '{print $2}' | awk -F':' '{print $1}')
                echo "Connect using this command: ssh $USER@$DOMAIN -p $PORT"
            else
                echo "RDP is Ready!"
                echo "Connect using this address: ${URL#tcp://}"
                echo "Username: $USER"
            fi
            echo "Password: $PASS"
            echo "Note: Pinggy free tier is limited to 60 minutes."
            echo "==========================================================="
            sleep 21600
        else
            echo "Error: Pinggy failed to start."
            cat /pinggy.log
            exit 1
        fi
        EOF
        chmod +x setup.sh
        
        echo "Booting {distro} container on {architecture}..."
        docker run --rm --privileged --platform linux/{architecture} -v $(pwd)/setup.sh:/setup.sh {distro} /setup.sh
"""

MACOS_WORKFLOW_TEMPLATE = """name: macOS VNC
on: workflow_dispatch
jobs:
  build:
    runs-on: {runner_image}
    timeout-minutes: 9999
    steps:
    - name: Enable VNC (Screen Sharing)
      run: |
        sudo /System/Library/CoreServices/RemoteManagement/ARDAgent.app/Contents/Resources/kickstart -activate -configure -access -on -clientopts -setvnclegacy -vnclegacy yes -clientopts -setvncpw -vncpw ThePassword123! -restart -agent -privs -all
    - name: Start Pinggy tunnel
      run: |
        ssh -T -p 443 -R0:localhost:5900 -o StrictHostKeyChecking=no -o ServerAliveInterval=30 tcp@a.pinggy.io > pinggy.log 2>&1 &
        sleep 10
        URL=$(grep -o "tcp://.*" pinggy.log | head -n 1)
        if [ ! -z "$URL" ]; then
            echo "==========================================================="
            echo "VNC is Ready!"
            echo "Connect using this address: ${URL#tcp://}"
            echo "Password: ThePassword123!"
            echo "Note: Pinggy free tier is limited to 60 minutes."
            echo "==========================================================="
            sleep 21600
        else
            echo "Error: Pinggy failed to start. See logs below."
            echo "--- Pinggy Logs ---"
            cat pinggy.log
            exit 1
        fi
"""

CUSTOM_ISO_WORKFLOW_TEMPLATE = """name: Custom ISO VNC
on: workflow_dispatch
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 9999
    steps:
    - name: Free Disk Space
      run: |
        sudo rm -rf /usr/share/dotnet /usr/local/lib/android /opt/ghc /opt/hostedtoolcache/CodeQL || true
        sudo docker image prune --all --force || true
    - name: Install QEMU
      run: sudo apt-get update && sudo apt-get install -y qemu-system-x86 qemu-kvm wget curl aria2
    - name: Download ISO
      env:
        GH_TOKEN: ${{ github.token }}
      run: |
{download_logic}
    - name: Boot Custom ISO
      run: |
        sudo qemu-system-x86_64 -enable-kvm -m 6G -smp 4 -cdrom custom.iso -vnc :0 -boot d -daemonize
    - name: Start Pinggy for VNC
      run: |
        ssh -T -p 443 -R0:localhost:5900 -o StrictHostKeyChecking=no -o ServerAliveInterval=30 tcp@a.pinggy.io > pinggy.log 2>&1 &
        sleep 15
        URL=$(grep -o "tcp://.*" pinggy.log | head -n 1)
        if [ ! -z "$URL" ]; then
            echo "==========================================================="
            echo "VNC is Ready! Your Custom ISO is booting up."
            echo "Connect using this address: ${URL#tcp://}"
            echo "Note: No password is set for this VNC server."
            echo "Note: Pinggy free tier is limited to 60 minutes."
            echo "==========================================================="
            sleep 21600
        else
            echo "Error: Pinggy failed to start. See logs below."
            cat pinggy.log
            exit 1
        fi
"""

def start_p2p_server(iso_dir, base_dir):
    port = 8080
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

def generate_workflow(os_choice, version_choice, architecture="amd64", de_choice="xfce", app_choice_str="", custom_download_logic=""):
    if os_choice == "windows":
        return WINDOWS_WORKFLOW_TEMPLATE.replace("{runner_image}", version_choice)
    elif os_choice == "linux":
        qemu = ""
        if architecture != "amd64":
            qemu = "\\n    - name: Set up QEMU for multi-arch support\\n      uses: docker/setup-qemu-action@v3"
        return LINUX_WORKFLOW_TEMPLATE.replace("{distro}", version_choice).replace("{architecture}", architecture).replace("{qemu_setup}", qemu).replace("{de_choice}", de_choice).replace("{app_choice_str}", app_choice_str)
    elif os_choice == "macos":
        return MACOS_WORKFLOW_TEMPLATE.replace("{runner_image}", version_choice)
    elif os_choice == "custom_iso":
        # Format strings require matching curly braces unless escaped.
        # {download_logic} is safely replaced here without escaping issues
        # because we constructed CUSTOM_ISO_WORKFLOW_TEMPLATE cleanly.
        lines = ["        " + line for line in custom_download_logic.strip().split("\\n")]
        formatted_logic = "\\n".join(lines)
        return CUSTOM_ISO_WORKFLOW_TEMPLATE.replace("{download_logic}", formatted_logic)
    else:
        raise ValueError(f"Unknown OS choice: {os_choice}")

def run_command(cmd, cwd=None):
    try:
        subprocess.run(cmd, cwd=cwd, check=True)
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

def main():
    if not shutil.which("gh"):
        print("Error: GitHub CLI ('gh') is not installed. Please install it to proceed.")
        sys.exit(1)
        
    if not shutil.which("git"):
        print("Error: 'git' is not installed. Please install it to proceed.")
        sys.exit(1)

    print("Welcome to the GitHub Actions RDP Provisioner")
    print("-" * 50)
    
    check_gh_auth()
    
    try:
        gh_user = subprocess.run(["gh", "api", "user", "-q", ".login"], capture_output=True, text=True, check=True).stdout.strip()
    except subprocess.CalledProcessError:
        print("Failed to retrieve your GitHub username. Exiting.")
        sys.exit(1)

    repo_name = input("Enter a name for the GitHub repository (e.g., my-rdp-testing): ").strip()
    if not repo_name:
        print("Repository name cannot be empty.")
        sys.exit(1)

    repo_exists = False
    try:
        subprocess.run(["gh", "repo", "view", f"{gh_user}/{repo_name}"], capture_output=True, check=True)
        repo_exists = True
    except subprocess.CalledProcessError:
        pass

    if repo_exists:
        print(f"\\nWARNING: The repository '{gh_user}/{repo_name}' already exists.")
        choice = input("Do you want to clean it and reuse it? This will overwrite the repo. (y/n): ").strip().lower()
        if choice != 'y':
            print("Aborting.")
            sys.exit(1)

    os_choices = {
        "windows": ["windows-latest", "windows-2022", "windows-2019"],
        "macos": ["macos-latest", "macos-14", "macos-13", "macos-12", "macos-11"],
        "linux": [
            "ubuntu:latest", "ubuntu:22.04", "ubuntu:20.04",
            "debian:latest", "debian:bullseye",
            "kalilinux/kali-rolling",
            "archlinux:latest",
            "fedora:latest", "fedora:39",
            "linuxmintd/mint21.2-amd64",
            "manjaro/base:latest"
        ],
        "custom_iso": ["Custom Local ISO (QEMU Nested Virtualization)"]
    }
    
    os_choice = ""
    while os_choice not in os_choices.keys():
        os_choice = input("\\nWhich OS do you want to test on? (windows/linux/macos/custom_iso): ").lower().strip()

    version_choice = "latest"
    architecture = "amd64"
    de_choice = "xfce"
    app_choice_str = ""
    custom_download_logic = ""
    p2p_procs = None

    if os_choice != "custom_iso":
        print(f"Available versions/distros for {os_choice}:")
        for i, ver in enumerate(os_choices[os_choice], 1):
            print(f"{i}. {ver}")
        
        version_idx = -1
        while version_idx < 0 or version_idx >= len(os_choices[os_choice]):
            try:
                choice = input(f"Select version/distro (1-{len(os_choices[os_choice])}): ").strip()
                version_idx = int(choice) - 1
            except ValueError:
                pass
                
        version_choice = os_choices[os_choice][version_idx]

        if os_choice == "linux":
            arch_choices = ["amd64", "arm64"]
            print("\\nAvailable CPU architectures for Linux:")
            for i, arch in enumerate(arch_choices, 1):
                print(f"{i}. {arch}")
            
            arch_idx = -1
            while arch_idx < 0 or arch_idx >= len(arch_choices):
                try:
                    choice = input(f"Select architecture (1-{len(arch_choices)}): ").strip()
                    arch_idx = int(choice) - 1
                except ValueError:
                    pass
            architecture = arch_choices[arch_idx]
            
            de_choices = ["stock", "xfce", "gnome", "kde", "i3", "cli"]
            print("\\nAvailable Desktop Environments / Window Managers:")
            for i, de in enumerate(de_choices, 1):
                desc = ""
                if de == "stock": desc = " (Installs the distro's exact default GUI)"
                if de == "cli": desc = " (No GUI, SSH only. Extremely fast boot)"
                print(f"{i}. {de}{desc}")
                
            de_idx = -1
            while de_idx < 0 or de_idx >= len(de_choices):
                try:
                    choice = input(f"Select Desktop Environment (1-{len(de_choices)}): ").strip()
                    de_idx = int(choice) - 1
                except ValueError:
                    pass
            de_choice = de_choices[de_idx]

            app_choices_list = [
                ("Web Browser (Firefox)", "firefox"),
                ("CLI Editors (nano, vim)", "nano vim"),
                ("Containerization (Docker)", "docker.io"),
                ("Network/Security Tools (Nmap, Netcat, curl, wget)", "nmap netcat curl wget"),
                ("Build Tools (git, gcc, make)", "git build-essential")
            ]
            
            print("\\nSelect additional apps to pre-install:")
            for i, (app_desc, _) in enumerate(app_choices_list, 1):
                print(f"{i}. {app_desc}")
                
            app_input = input(f"Enter comma-separated numbers (e.g., 1,3,4) or press Enter to skip: ").strip()
            app_choice_indices = []
            if app_input:
                for part in app_input.split(','):
                    try:
                        idx = int(part.strip()) - 1
                        if 0 <= idx < len(app_choices_list):
                            app_choice_indices.append(idx)
                    except ValueError:
                        pass
            
            app_choice_str = ",".join(map(str, app_choice_indices))

    else:
        # Custom ISO Logic
        print("\\nSelect ISO Source:")
        print("1. Local File (on your computer)")
        print("2. Direct Download URL (e.g. https://example.com/os.iso)")
        source_choice = ""
        while source_choice not in ["1", "2"]:
            source_choice = input("Select source (1-2): ").strip()
            
        custom_download_logic = ""
        base_dir = os.path.join(os.getcwd(), repo_name)
        
        if source_choice == "2":
            iso_url = ""
            while not iso_url.startswith("http"):
                iso_url = input("\\nEnter the direct HTTP/HTTPS URL to the ISO file: ").strip()
            custom_download_logic = f'aria2c -x 16 -s 16 -k 1M -o custom.iso "{iso_url}"'
            method = "url"
        else:
            iso_path = ""
            while not os.path.isfile(iso_path):
                iso_path = input("\\nEnter the absolute path to your local .iso file: ").strip()
                if not os.path.isfile(iso_path):
                    print("File not found or is not a valid file. Try again.")
            
            file_size_gb = os.path.getsize(iso_path) / (1024 ** 3)
            print(f"ISO Size: {file_size_gb:.2f} GB")
            
            print("\\nSelect Transfer Method:")
            print("1. GitHub Releases (Cloud) - Automatically uploads and runs autonomously.")
            print("2. Peer-to-Peer (Local Stream) - Streams directly from your PC (requires terminal to stay open).")
            method = ""
            while method not in ["1", "2"]:
                method = input("Select method (1-2): ").strip()
                
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

    print("\\n[1/4] Creating local directory structure...")
    base_dir = os.path.join(os.getcwd(), repo_name)
    if os.path.exists(base_dir) and not (os_choice == "custom_iso" and method == "1"):
        shutil.rmtree(base_dir)
    os.makedirs(base_dir, exist_ok=True)
        
    workflow_dir = os.path.join(base_dir, ".github", "workflows")
    os.makedirs(workflow_dir, exist_ok=True)
    
    workflow_yml = generate_workflow(os_choice, version_choice, architecture, de_choice, app_choice_str, custom_download_logic)
    workflow_path = os.path.join(workflow_dir, "rdp.yml")
    with open(workflow_path, "w") as f:
        f.write(workflow_yml)

    print("[2/4] Initializing Git repository...")
    run_command(["git", "init"], cwd=base_dir)
    ensure_git_config(base_dir)
    run_command(["git", "branch", "-M", "main"], cwd=base_dir)
    run_command(["git", "add", "."], cwd=base_dir)
    run_command(["git", "commit", "-m", "Initial commit: Add RDP workflow"], cwd=base_dir)

    print("[3/4] Setting up GitHub repository...")
    try:
        check_repo = subprocess.run(["gh", "api", f"repos/{gh_user}/{repo_name}"], capture_output=True, text=True)
        if check_repo.returncode == 0:
            print("Force pushing to existing repository...")
            subprocess.run(["git", "remote", "add", "origin", f"https://github.com/{gh_user}/{repo_name}.git"], cwd=base_dir, capture_output=True)
            run_command(["git", "push", "-f", "origin", "main"], cwd=base_dir)
        else:
            result = subprocess.run(["gh", "repo", "create", repo_name, "--private", "--source=.", "--remote=origin", "--push"], cwd=base_dir, capture_output=True, text=True)
            if result.returncode != 0:
                if "already exists" in result.stderr or "already exists" in result.stdout:
                    print("Force pushing to existing repository...")
                    subprocess.run(["git", "remote", "add", "origin", f"https://github.com/{gh_user}/{repo_name}.git"], cwd=base_dir, capture_output=True)
                    run_command(["git", "push", "-f", "origin", "main"], cwd=base_dir)
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

    print("[4/4] Provisioning complete!")
    print("-" * 50)
    print("Next steps:")
    
    print(f"Repository URL: https://github.com/{gh_user}/{repo_name}/actions")
    
    print("\\nTriggering the GitHub Action workflow automatically...")
    try:
        subprocess.run(["gh", "workflow", "run", "rdp.yml", "-R", f"{gh_user}/{repo_name}"], cwd=base_dir, check=True)
        print("Workflow triggered successfully!")
    except subprocess.CalledProcessError as e:
        print("Error triggering the workflow.")
        print(f"     cd {repo_name} && gh workflow run rdp.yml")
    
    print("-" * 50)
    print("All done!")
    print("The environment is booting up now. Please allow 1-3 minutes for it to start.")
    print(f"Click the Repository URL above, go to your running workflow, and click 'Get connection URL'.")
    print(f"   - For Linux/Windows: Use an RDP client to connect.")
    print(f"   - For macOS/Custom ISO: Use a VNC client to connect.")
    print(f"   * NOTE: The Pinggy free tier will disconnect after 60 minutes.")

    # Block terminal if P2P is active
    if p2p_procs:
        http_proc, pinggy_proc = p2p_procs
        print("\\n" + "="*60)
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
