import os
import argparse
import sys
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

WINDOWS_CLI_WORKFLOW_TEMPLATE = r"""name: Windows SSH
on: workflow_dispatch
jobs:
  build:
    runs-on: {runner_image}
    timeout-minutes: 9999
    steps:
    - name: Enable SSH Access
      run: |
        Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
        Start-Service sshd
        Set-Service -Name sshd -StartupType 'Automatic'
        net user runneradmin ThePassword123!
    - name: Start Pinggy tunnel and get connection URL
      shell: bash
      run: |
        ssh -T -p 443 -R0:localhost:22 -o StrictHostKeyChecking=no -o ServerAliveInterval=30 tcp@a.pinggy.io < /dev/null > pinggy.log 2>&1 &
        sleep 15
        URL=$(grep -o "tcp://.*" pinggy.log | head -n 1)
        if [ ! -z "$URL" ]; then
            PORT=$(echo $URL | cut -d':' -f3)
            HOST=$(echo $URL | cut -d'/' -f3 | cut -d':' -f1)
            echo "==========================================================="
            echo "SSH is Ready!"
            echo "Connect using this command: env TERM=xterm-256color ssh -p $PORT runneradmin@$HOST"
            echo "Password: ThePassword123!"
            echo "Note: Pinggy free tier is limited to 60 minutes."
            echo "==========================================================="
            sleep 21600
        else
            echo "Error: Pinggy failed to start. See logs below."
            cat pinggy.log
            exit 1
        fi
"""

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
                echo "Connect using this command: env TERM=xterm-256color ssh $USER@$DOMAIN -p $PORT"
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

MACOS_CLI_WORKFLOW_TEMPLATE = r"""name: macOS SSH
on: workflow_dispatch
jobs:
  build:
    runs-on: {runner_image}
    timeout-minutes: 9999
    steps:
    - name: Enable SSH (Remote Login)
      run: |
        sudo systemsetup -setremotelogin on || true
        sudo dseditgroup -o edit -a $USER -t user com.apple.access_ssh || true
        mkdir -p ~/.ssh
        chmod 700 ~/.ssh
        echo "{pub_key}" > ~/.ssh/authorized_keys
        chmod 600 ~/.ssh/authorized_keys
    - name: Start Pinggy tunnel
      run: |
        ssh -T -p 443 -R0:localhost:22 -o StrictHostKeyChecking=no -o ServerAliveInterval=30 tcp@a.pinggy.io > pinggy.log 2>&1 &
        sleep 10
        URL=$(grep -o "tcp://.*" pinggy.log | head -n 1)
        if [ ! -z "$URL" ]; then
            PORT=$(echo $URL | cut -d':' -f3)
            HOST=$(echo $URL | cut -d'/' -f3 | cut -d':' -f1)
            echo "==========================================================="
            echo "SSH is Ready!"
            echo "Connect using this command: env TERM=xterm-256color ssh -i macos_runner_key -p $PORT runner@$HOST"
            echo "Note: Pinggy free tier is limited to 60 minutes."
            echo "==========================================================="
            sleep 21600
        else
            echo "Error: Pinggy failed to start. See logs below."
            cat pinggy.log
            exit 1
        fi
"""

MACOS_WORKFLOW_TEMPLATE = r"""name: macOS VNC
on: workflow_dispatch
jobs:
  build:
    runs-on: {runner_image}
    timeout-minutes: 9999
    steps:
    - name: Enable VNC (Screen Sharing)
      run: |
        sudo sysadminctl -resetPasswordFor $USER -newPassword macvnc12
        sudo sqlite3 /Library/Application\ Support/com.apple.TCC/TCC.db "INSERT OR REPLACE INTO access (service, client, client_type, allowed, prompt_count, csreq, indirect_object_identifier_type, indirect_object_identifier, flags, last_modified) VALUES ('kTCCServiceScreenCapture','com.apple.RemoteDesktop.agent',0,2,4,1,NULL,'UNUSED',0,0);" || true
        sudo sqlite3 /Library/Application\ Support/com.apple.TCC/TCC.db "INSERT OR REPLACE INTO access (service, client, client_type, allowed, prompt_count, csreq, indirect_object_identifier_type, indirect_object_identifier, flags, last_modified) VALUES ('kTCCServicePostEvent','com.apple.RemoteDesktop.agent',0,2,4,1,NULL,'UNUSED',0,0);" || true
        sudo /System/Library/CoreServices/RemoteManagement/ARDAgent.app/Contents/Resources/kickstart -activate -configure -access -on -users $USER -privs -all -clientopts -setvnclegacy -vnclegacy yes
        echo "macvnc12" | perl -we 'BEGIN { @k = unpack "C*", pack "H*", "1734516E8BA8C5E2FF1C39567390ADCA"}; $_ = <>; chomp; s/^(.{8}).*/$1/; @p = unpack "C*", $_; foreach (@k) { printf "%02X", $_ ^ (shift @p || 0) }; print "\n"' | sudo tee /Library/Preferences/com.apple.VNCSettings.txt
        sudo /System/Library/CoreServices/RemoteManagement/ARDAgent.app/Contents/Resources/kickstart -restart -agent
    - name: Start Pinggy tunnel
      run: |
        ssh -T -p 443 -R0:localhost:5900 -o StrictHostKeyChecking=no -o ServerAliveInterval=30 tcp@a.pinggy.io > pinggy.log 2>&1 &
        sleep 10
        URL=$(grep -o "tcp://.*" pinggy.log | head -n 1)
        if [ ! -z "$URL" ]; then
            echo "==========================================================="
            echo "VNC is Ready!"
            echo "Connect using this address: ${URL#tcp://}"
            echo "Username: runner"
            echo "Password: macvnc12"
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

def generate_workflow(os_choice, version_choice, architecture="amd64", de_choice="xfce", app_choice_str="", custom_download_logic="", pub_key=""):
    if os_choice == "windows":
        if de_choice == "cli":
            return WINDOWS_CLI_WORKFLOW_TEMPLATE.replace("{runner_image}", version_choice)
        else:
            return WINDOWS_WORKFLOW_TEMPLATE.replace("{runner_image}", version_choice)
    elif os_choice == "linux":
        qemu = ""
        if architecture != "amd64":
            qemu = "\\n    - name: Set up QEMU for multi-arch support\\n      uses: docker/setup-qemu-action@v3"
        return LINUX_WORKFLOW_TEMPLATE.replace("{distro}", version_choice).replace("{architecture}", architecture).replace("{qemu_setup}", qemu).replace("{de_choice}", de_choice).replace("{app_choice_str}", app_choice_str)
    elif os_choice == "macos":
        if de_choice == "cli":
            return MACOS_CLI_WORKFLOW_TEMPLATE.replace("{runner_image}", version_choice).replace("{pub_key}", pub_key)
        else:
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

def main():
    if not shutil.which("gh"):
        print("Error: GitHub CLI ('gh') is not installed. Please install it to proceed.")
        sys.exit(1)
        
    if not shutil.which("git"):
        print("Error: 'git' is not installed. Please install it to proceed.")
        sys.exit(1)

    console.print("[bold cyan]Welcome to the GitHub Actions RDP Provisioner[/bold cyan]")
    console.print("[dim]" + "-" * 50 + "[/dim]")
    
    check_gh_auth()
    
    try:
        gh_user = subprocess.run(["gh", "api", "user", "-q", ".login"], capture_output=True, text=True, check=True).stdout.strip()
    except subprocess.CalledProcessError:
        print("Failed to retrieve your GitHub username. Exiting.")
        sys.exit(1)

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

    os_choices = {
        "windows": ["windows-latest", "windows-2022", "windows-2019"],
        "macos": [
            Choice("macos-latest", "macos-latest (Apple Silicon - Black Screen Warning)"),
            Choice("macos-14", "macos-14 (Apple Silicon - Black Screen Warning)"),
            Choice("macos-13", "macos-13 (Intel - VNC Supported)"),
            Choice("macos-12", "macos-12 (Intel - VNC Supported)"),
            Choice("macos-11", "macos-11 (Intel - VNC Supported)")
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
        "custom_iso": ["Custom Local ISO (QEMU Nested Virtualization)"]
    }
    
    os_choice = inquirer.select(
        message="Which OS do you want to test on?",
        choices=[
            Choice("windows", "Windows"),
            Choice("linux", "Linux"),
            Choice("macos", "macOS"),
            Choice("custom_iso", "Custom ISO")
        ]
    ).execute()

    version_choice = "latest"
    architecture = "amd64"
    de_choice = "xfce"
    app_choice_str = ""
    custom_download_logic = ""
    p2p_procs = None

    if os_choice != "custom_iso":
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

            app_choices_list = [
                Choice("0", "Web Browser (Firefox)"),
                Choice("1", "CLI Editors (nano, vim)"),
                Choice("2", "Containerization (Docker)"),
                Choice("3", "Network/Security Tools (Nmap, Netcat, curl, wget)"),
                Choice("4", "Build Tools (git, gcc, make)")
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
        base_dir = os.path.join(os.getcwd(), repo_name)
        
        if source_choice == "2":
            iso_url = inquirer.text(
                message="Enter the direct HTTP/HTTPS URL to the ISO file:",
                validate=lambda x: x.startswith("http")
            ).execute().strip()
            custom_download_logic = f'aria2c -x 16 -s 16 -k 1M -o custom.iso "{iso_url}"'
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

    print("\\n[1/4] Creating local directory structure...")
    base_dir = os.path.join(os.getcwd(), repo_name)
    if os.path.exists(base_dir) and not (os_choice == "custom_iso" and method == "1"):
        shutil.rmtree(base_dir)
    os.makedirs(base_dir, exist_ok=True)
        
    workflow_dir = os.path.join(base_dir, ".github", "workflows")
    os.makedirs(workflow_dir, exist_ok=True)
    
    pub_key = ""
    if os_choice == "macos" and de_choice == "cli":
        if not os.path.exists("macos_runner_key"):
            print("\nGenerating SSH key pair for macOS CLI access...")
            subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", "macos_runner_key", "-N", "", "-q"], check=True)
        with open("macos_runner_key.pub", "r") as f:
            pub_key = f.read().strip()

    workflow_yml = generate_workflow(os_choice, version_choice, architecture, de_choice, app_choice_str, custom_download_logic, pub_key)
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

    console.print("[bold green][4/4] Provisioning complete![/bold green]")
    console.print("[dim]" + "-" * 50 + "[/dim]")
    print("Next steps:")
    
    print(f"Repository URL: https://github.com/{gh_user}/{repo_name}/actions")
    
    print("\\nTriggering the GitHub Action workflow automatically...")
    try:
        subprocess.run(["gh", "workflow", "run", "rdp.yml", "-R", f"{gh_user}/{repo_name}"], cwd=base_dir, check=True)
        print("Workflow triggered successfully!")
    except subprocess.CalledProcessError as e:
        print("Error triggering the workflow.")
        print(f"     cd {repo_name} && gh workflow run rdp.yml")
    
    console.print("[dim]" + "-" * 50 + "[/dim]")
    console.print("[bold magenta]All done![/bold magenta]")
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
