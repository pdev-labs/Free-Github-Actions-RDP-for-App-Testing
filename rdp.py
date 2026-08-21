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

import json
import os

def load_profile():
    if os.path.exists("profiles.json"):
        with open("profiles.json", "r") as f:
            profiles = json.load(f)
        if profiles:
            choices = [Choice("new", "Create New")] + [Choice(k, f"Load Profile: {k}") for k in profiles.keys()]
            choice = inquirer.select(
                message="Load a saved profile or create a new one?",
                choices=choices
            ).execute()
            if choice != "new":
                return profiles[choice]
    return None

def save_profile(data):
    profiles = {}
    if os.path.exists("profiles.json"):
        with open("profiles.json", "r") as f:
            profiles = json.load(f)
    
    name = inquirer.text(
        message="Enter a name to save this configuration (or press Enter to skip):"
    ).execute().strip()
    
    if name:
        profiles[name] = data
        with open("profiles.json", "w") as f:
            json.dump(profiles, f, indent=4)
        print(f"[+] Profile '{name}' saved successfully!")


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
        Set-Service -Name Audiosrv -StartupType 'Automatic'
        Start-Service Audiosrv
        reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows NT\\Terminal Services" /v fAllowAudioPlayback /t REG_DWORD /d 1 /f
        reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server\\WinStations\\RDP-Tcp" /v fDisableAudioCapture /t REG_DWORD /d 0 /f
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
            echo "Connect using this address: ${URL#tcp://}"
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
        if [[ "$APP_CHOICE" == *"5"* ]]; then
            PKG_APT="$PKG_APT nmap wireshark tshark metasploit-framework"
            PKG_PACMAN="$PKG_PACMAN nmap wireshark-cli metasploit"
            PKG_DNF="$PKG_DNF nmap wireshark metasploit"
        fi
        if [[ "$APP_CHOICE" == *"6"* ]]; then
            PKG_APT="$PKG_APT nodejs npm python3-pip docker.io apt-transport-https software-properties-common"
            PKG_PACMAN="$PKG_PACMAN nodejs npm python-pip docker code"
            PKG_DNF="$PKG_DNF nodejs npm python3-pip docker"
        fi
        if [[ "$APP_CHOICE" == *"7"* ]]; then
            PKG_APT="$PKG_APT default-jdk"
            PKG_PACMAN="$PKG_PACMAN jdk-openjdk"
            PKG_DNF="$PKG_DNF java-latest-openjdk"
        fi

        echo "Detecting package manager and installing packages..."
        if command -v apt-get >/dev/null; then
            apt-get update
            apt-get install -y sudo openssh-server openssh-client passwd curl wget gpg $PKG_APT
            if [[ "$APP_CHOICE" == *"6"* ]]; then
                wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg
                install -D -o root -g root -m 644 packages.microsoft.gpg /etc/apt/keyrings/packages.microsoft.gpg
                sh -c 'echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list'
                rm -f packages.microsoft.gpg
                apt-get update && apt-get install -y code
            fi
            if [[ "$APP_CHOICE" == *"7"* ]]; then
                add-apt-repository ppa:maarten-fonville/android-studio -y
                apt-get update && apt-get install -y android-studio
            fi
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

                # Compile and install pulseaudio-module-xrdp for audio redirection
                echo "Installing PulseAudio and XRDP audio modules..."
                apt-get install -y pulseaudio pulseaudio-utils build-essential dpkg-dev libpulse-dev git autoconf libtool
                cd /tmp
                git clone https://github.com/neutrinolabs/pulseaudio-module-xrdp.git
                cd pulseaudio-module-xrdp
                ./bootstrap && ./configure PULSE_DIR=/usr/src/pulseaudio
                make && make install
                cd /
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

                # Compile and install pulseaudio-module-xrdp for audio redirection
                echo "Installing PulseAudio and XRDP audio modules..."
                apt-get install -y pulseaudio pulseaudio-utils build-essential dpkg-dev libpulse-dev git autoconf libtool
                cd /tmp
                git clone https://github.com/neutrinolabs/pulseaudio-module-xrdp.git
                cd pulseaudio-module-xrdp
                ./bootstrap && ./configure PULSE_DIR=/usr/src/pulseaudio
                make && make install
                cd /
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
                pacman -Syu --noconfirm dbus base-devel pulseaudio
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

                # Compile and install pulseaudio-module-xrdp for audio redirection
                echo "Installing PulseAudio and XRDP audio modules..."
                apt-get install -y pulseaudio pulseaudio-utils build-essential dpkg-dev libpulse-dev git autoconf libtool
                cd /tmp
                git clone https://github.com/neutrinolabs/pulseaudio-module-xrdp.git
                cd pulseaudio-module-xrdp
                ./bootstrap && ./configure PULSE_DIR=/usr/src/pulseaudio
                make && make install
                cd /
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


import re

# Previous duplicate block removed.

def inject_tunnel_logic(template, tunnel, ngrok_token, port, os_choice='linux', de_choice='xfce'):
    if tunnel == "pinggy":
        template = re.sub(
            r"([ \t]+)(ssh -T -p 443 -R0:localhost:[0-9]+ -o StrictHostKeyChecking=no.*&)", 
            r"\1while true; do\n\1    \2\n\1    SSH_PID=$!", 
            template
        )
        popup_cmd = ""
        if de_choice != 'cli':
            if os_choice == 'windows':
                popup_cmd = "powershell.exe -EncodedCommand CgAkAGMAbwBkAGUAIAA9ACAAQAAiAAoAdQBzAGkAbgBnACAAUwB5AHMAdABlAG0AOwAKAHUAcwBpAG4AZwAgAFMAeQBzAHQAZQBtAC4AUgB1AG4AdABpAG0AZQAuAEkAbgB0AGUAcgBvAHAAUwBlAHIAdgBpAGMAZQBzADsACgBwAHUAYgBsAGkAYwAgAGMAbABhAHMAcwAgAFcAVABTACAAewAKACAAIAAgACAAWwBEAGwAbABJAG0AcABvAHIAdAAoACIAdwB0AHMAYQBwAGkAMwAyAC4AZABsAGwAIgAsACAAUwBlAHQATABhAHMAdABFAHIAcgBvAHIAIAA9ACAAdAByAHUAZQApAF0ACgAgACAAIAAgAHAAdQBiAGwAaQBjACAAcwB0AGEAdABpAGMAIABlAHgAdABlAHIAbgAgAGIAbwBvAGwAIABXAFQAUwBTAGUAbgBkAE0AZQBzAHMAYQBnAGUAKABJAG4AdABQAHQAcgAgAGgAUwBlAHIAdgBlAHIALAAgAGkAbgB0ACAAUwBlAHMAcwBpAG8AbgBJAGQALAAgAHMAdAByAGkAbgBnACAAcABUAGkAdABsAGUALAAgAGkAbgB0ACAAVABpAHQAbABlAEwAZQBuAGcAdABoACwAIABzAHQAcgBpAG4AZwAgAHAATQBlAHMAcwBhAGcAZQAsACAAaQBuAHQAIABNAGUAcwBzAGEAZwBlAEwAZQBuAGcAdABoACwAIABpAG4AdAAgAFMAdAB5AGwAZQAsACAAaQBuAHQAIABUAGkAbQBlAG8AdQB0ACwAIABvAHUAdAAgAGkAbgB0ACAAcABSAGUAcwBwAG8AbgBzAGUALAAgAGIAbwBvAGwAIABiAFcAYQBpAHQAKQA7AAoAfQAKACIAQAAKAEEAZABkAC0AVAB5AHAAZQAgAC0AVAB5AHAAZQBEAGUAZgBpAG4AaQB0AGkAbwBuACAAJABjAG8AZABlAAoACgAkAHQAaQB0AGwAZQAgAD0AIAAiAFAAaQBuAGcAZwB5ACAARAByAG8AcAAgAFcAYQByAG4AaQBuAGcAIgAKACQAbQBzAGcAIAA9ACAAIgBXAEEAUgBOAEkATgBHADoAIABUAHUAbgBuAGUAbAAgAGQAcgBvAHAAcABpAG4AZwAgAGkAbgAgADIAIABtAGkAbgBzACEAIABHAGUAdAAgAG4AZQB3ACAAVQBSAEwAIABmAHIAbwBtACAARwBpAHQASAB1AGIAIABBAGMAdABpAG8AbgBzAC4AIABUAGgAaQBzACAAcABvAHAAdQBwACAAdwBpAGwAbAAgAGEAdQB0AG8ALQBjAGwAbwBzAGUALgAiAAoAJAB0AGkAdABsAGUATABlAG4AIAA9ACAAJAB0AGkAdABsAGUALgBMAGUAbgBnAHQAaAAKACQAbQBzAGcATABlAG4AIAA9ACAAJABtAHMAZwAuAEwAZQBuAGcAdABoAAoACgAkAHQAaQBtAGUAbwB1AHQAIAA9ACAAKABHAGUAdAAtAEQAYQB0AGUAKQAuAEEAZABkAFMAZQBjAG8AbgBkAHMAKAAxADIAMAApAAoAdwBoAGkAbABlACAAKAAoAEcAZQB0AC0ARABhAHQAZQApACAALQBsAHQAIAAkAHQAaQBtAGUAbwB1AHQAKQAgAHsACgAgACAAIAAgAGYAbwByACAAKAAkAGkAPQAxADsAIAAkAGkAIAAtAGwAZQAgADEAMAA7ACAAJABpACsAKwApACAAewAKACAAIAAgACAAIAAgACAAIAAkAHIAZQBzAHAAIAA9ACAAMAAKACAAIAAgACAAIAAgACAAIABbAHYAbwBpAGQAXQBbAFcAVABTAF0AOgA6AFcAVABTAFMAZQBuAGQATQBlAHMAcwBhAGcAZQAoAFsASQBuAHQAUAB0AHIAXQA6ADoAWgBlAHIAbwAsACAAJABpACwAIAAkAHQAaQB0AGwAZQAsACAAJAB0AGkAdABsAGUATABlAG4ALAAgACQAbQBzAGcALAAgACQAbQBzAGcATABlAG4ALAAgADIANgAyADEAOQAyACwAIAAxADAALAAgAFsAcgBlAGYAXQAkAHIAZQBzAHAALAAgACQAdAByAHUAZQApAAoAIAAgACAAIAB9AAoAfQAKAA== || true"
            elif os_choice == 'macos':
                popup_cmd = "osascript -e 'display notification \"Tunnel dropping in 2 mins! Get new URL from GitHub Actions. This popup will auto-close.\" with title \"Pinggy Drop Warning (2 Mins)\"' || true"
            elif os_choice == 'linux' or os_choice == 'custom_iso':
                popup_cmd = "notify-send \"Pinggy Drop Warning\" \"Tunnel dropping in 2 mins! Get new URL from GitHub Actions. This popup will auto-close.\" || true"
                
        warning_block = f'''sleep 3300
            echo "[$(date)] 55 minutes reached. Firing OS warning popup..."
            ( {popup_cmd} ) &
            sleep 120
            echo "[$(date)] 57 minutes reached. Restarting Pinggy tunnel to bypass 60-min limit..."
            kill $SSH_PID'''
            
        template = template.replace("sleep 21600", warning_block)
        template = re.sub(r"(exit 1\s*fi)", r"\1\n        sleep 2\n        done\n        sleep 21600", template)
        return template
        
    if tunnel == "ngrok":
        if os_choice == 'windows':
            ngrok_cmd = f'''wget -q https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip
        unzip -q ngrok-v3-stable-windows-amd64.zip
        ./ngrok.exe authtoken {ngrok_token}
        ./ngrok.exe tcp {port} --log=stdout > pinggy.log 2>&1 &'''
        elif os_choice == 'macos':
            ngrok_cmd = f'''wget -q https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-darwin-amd64.zip
        unzip -q ngrok-v3-stable-darwin-amd64.zip
        ./ngrok authtoken {ngrok_token}
        ./ngrok tcp {port} --log=stdout > pinggy.log 2>&1 &'''
        else:
            ngrok_cmd = f'''wget -q https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
        tar -xf ngrok-v3-stable-linux-amd64.tgz
        ./ngrok authtoken {ngrok_token}
        ./ngrok tcp {port} --log=stdout > pinggy.log 2>&1 &'''
        
        template = re.sub(r"ssh -T -p 443 -R0:localhost:[0-9]+ -o StrictHostKeyChecking=no.*&", ngrok_cmd, template)
        template = re.sub(r'URL=\$\(grep -o "tcp://\.\*" .* \| head -n 1\)', "URL=$(curl -s localhost:4040/api/tunnels | grep -o '\"public_url\":\"tcp://[^\"]*' | grep -o 'tcp://.*' | head -n 1)", template)
        template = template.replace("Pinggy free tier is limited to 60 minutes", "Ngrok tunnel will persist for up to 6 hours")
        template = template.replace("Pinggy tunnel", "Ngrok tunnel")
        return template

    if tunnel == "cloudflare":
        if os_choice == 'windows':
            cf_cmd = f'''wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
        ./cloudflared-windows-amd64.exe tunnel --url tcp://localhost:{port} > cloudflared.log 2>&1 &'''
        elif os_choice == 'macos':
            cf_cmd = f'''brew install cloudflare/cloudflare/cloudflared
        cloudflared tunnel --url tcp://localhost:{port} > cloudflared.log 2>&1 &'''
        else:
            cf_cmd = f'''wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
        chmod +x cloudflared-linux-amd64
        ./cloudflared-linux-amd64 tunnel --url tcp://localhost:{port} > cloudflared.log 2>&1 &'''
        
        template = re.sub(r"ssh -T -p 443 -R0:localhost:[0-9]+ -o StrictHostKeyChecking=no.*&", cf_cmd, template)
        url_extract = r"URL=$(grep -o 'https://.*\.trycloudflare\.com' cloudflared.log | head -n 1)"
        template = re.sub(r'URL=\$\(grep -o "tcp://\.\*" .* \| head -n 1\)', url_extract, template)
        template = template.replace("Connect using this command: env TERM=xterm-256color ssh -p $PORT runneradmin@$HOST", "Connect using: cloudflared access ssh --hostname ${URL#https://}")
        template = template.replace("Connect using this address: ${URL#tcp://}", "Connect using local port forward: cloudflared access tcp --hostname ${URL#https://} --url 127.0.0.1:{port}")
        template = template.replace("Pinggy free tier is limited to 60 minutes.", "Cloudflare tunnel is infinite. Make sure you have 'cloudflared' installed locally to connect.")
        template = template.replace("Pinggy tunnel", "Cloudflare tunnel")
        template = template.replace("pinggy.log", "cloudflared.log")
        return template

    if tunnel == "tailscale":
        if os_choice == 'windows':
            ts_cmd = f'''choco install tailscale -y
        /c/Program\\ Files/Tailscale/tailscale.exe up --authkey {ngrok_token}
        IP=$(/c/Program\\ Files/Tailscale/tailscale.exe ip -4)'''
        elif os_choice == 'macos':
            ts_cmd = f'''brew install tailscale
        sudo tailscaled > tailscale.log 2>&1 &
        sleep 5
        sudo tailscale up --authkey {ngrok_token}
        IP=$(tailscale ip -4)'''
        else:
            ts_cmd = f'''curl -fsSL https://tailscale.com/install.sh | sh
        sudo tailscale up --authkey {ngrok_token}
        IP=\\$(tailscale ip -4)'''
        
        template = re.sub(r"ssh -T -p 443 -R0:localhost:[0-9]+ -o StrictHostKeyChecking=no.*&", ts_cmd, template)
        template = re.sub(r'URL=\$\(grep -o "tcp://\.\*" .* \| head -n 1\)', r"URL=$IP", template)
        template = template.replace("Connect using this command: env TERM=xterm-256color ssh -p $PORT runneradmin@$HOST", "Connect using: env TERM=xterm-256color ssh runneradmin@$URL")
        template = template.replace("Connect using this address: ${URL#tcp://}", "Connect using this address: $URL")
        template = template.replace("Pinggy free tier is limited to 60 minutes.", "Tailscale VPN tunnel is active securely.")
        template = template.replace("Pinggy tunnel", "Tailscale VPN")
        template = template.replace("pinggy.log", "tailscale_install.log")
        return template


def generate_workflow(os_choice, version_choice, architecture="amd64", de_choice="xfce", app_choice_str="", custom_download_logic="", pub_key="", tunnel="pinggy", ngrok_token=""):
    if os_choice == "windows":
        if de_choice == "cli":
            return inject_tunnel_logic(WINDOWS_CLI_WORKFLOW_TEMPLATE.replace("{runner_image}", version_choice), tunnel, ngrok_token, 22, os_choice, de_choice)
        else:
            return inject_tunnel_logic(WINDOWS_WORKFLOW_TEMPLATE.replace("{runner_image}", version_choice), tunnel, ngrok_token, 3389, os_choice, de_choice)
    elif os_choice == "linux":
        qemu = ""
        if architecture != "amd64":
            qemu = "\\n    - name: Set up QEMU for multi-arch support\\n      uses: docker/setup-qemu-action@v3"
        port = 22 if de_choice == "cli" else 3389
        return inject_tunnel_logic(LINUX_WORKFLOW_TEMPLATE.replace("{distro}", version_choice).replace("{architecture}", architecture).replace("{qemu_setup}", qemu).replace("{de_choice}", de_choice).replace("{app_choice_str}", app_choice_str), tunnel, ngrok_token, port, os_choice, de_choice)
    elif os_choice == "macos":
        if de_choice == "cli":
            return inject_tunnel_logic(MACOS_CLI_WORKFLOW_TEMPLATE.replace("{runner_image}", version_choice).replace("{pub_key}", pub_key), tunnel, ngrok_token, 22, os_choice, de_choice)
        else:
            return inject_tunnel_logic(MACOS_WORKFLOW_TEMPLATE.replace("{runner_image}", version_choice), tunnel, ngrok_token, 5900, os_choice, de_choice)
    elif os_choice == "custom_iso":
        return inject_tunnel_logic(CUSTOM_ISO_WORKFLOW_TEMPLATE.replace("{download_logic}", custom_download_logic), tunnel, ngrok_token, 5900, os_choice, de_choice)
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
    if os_choice == "macos" and de_choice == "cli":
        if not os.path.exists("macos_runner_key"):
            print("\nGenerating SSH key pair for macOS CLI access...")
            subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", "macos_runner_key", "-N", "", "-q"], check=True)
        with open("macos_runner_key.pub", "r") as f:
            pub_key = f.read().strip()

    workflow_yml = generate_workflow(os_choice, version_choice, architecture, de_choice, app_choice_str, custom_download_logic, pub_key, tunnel, ngrok_token)
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
