# GitHub Actions RDP & VNC Provisioner

<div align="center">
 <h3>Automated Cloud Desktop Environments inside GitHub Actions</h3>
</div>

> [!WARNING]
> **EDUCATIONAL AND TESTING PURPOSES ONLY**
> This script and the resulting environments are strictly intended for educational, CI/CD debugging, and temporary testing purposes.
> Do **NOT** use this tool to mine cryptocurrency, host illegal content, perform denial-of-service attacks, or violate GitHub's Terms of Service. Doing so will likely result in an immediate and permanent ban of your GitHub account. You are solely responsible for how you use this tool.

A powerful Python automation script that dynamically provisions fully interactive, GUI-enabled Desktop environments (Linux, Windows, macOS, and custom ISOs) directly inside GitHub Actions runners. It utilizes [Pinggy](https://pinggy.io/) to securely tunnel the RDP/VNC/SSH connection out of the isolated GitHub infrastructure directly to your local machine.

---

## Key Features
- **Multi-OS Support**: Native provisioning across Linux, Windows, and macOS host runners.
- **Modern Interactive CLI (TUI)**: Beautiful, intuitive interactive terminal menus powered by `InquirerPy` and `rich`.
- **Seamless SSH Key Injection**: Bypasses macOS SecureToken limitations by automatically generating SSH key pairs locally and injecting them securely into the cloud runner for instant, passwordless root terminal access!
- **Terminal Emulator Compatibility**: Automatically forces universal terminal formatting over SSH (`TERM=xterm-256color`), guaranteeing flawless compatibility for users running Kitty, Alacritty, or custom configurations.
- **Custom ISO Booting (QEMU Nested Virtualization)**: Boot **ANY** operating system (PearOS, Windows PE, BSD, custom Linux spins) from a raw `.iso` file inside the GitHub Action!
 - **Auto File-Splitting**: Intelligently handles ISOs larger than GitHub's 2GB limit by splitting, uploading, and merging chunks.
 - **P2P Local Streaming**: Stream an ISO directly from your local hard drive into the cloud runner without uploading it!
- **Extensive Linux Distributions**: Choose from Ubuntu, Debian, Kali Linux, Arch Linux, Fedora, Linux Mint, and Manjaro.
- **Desktop Environments**: Instantly spin up XFCE, GNOME, KDE Plasma, i3wm, or run in headless CLI-only mode.
- **Automatic PAM Patching**: Bypasses strict Docker container PAM (Pluggable Authentication Module) restrictions so that `xrdp` authentication works flawlessly out-of-the-box.
- **Config Profiles (Save & Load)**: Save your exact environment choices to `profiles.json` and deploy future workspaces instantly without clicking through menus!
- **Dual Tunneling Engine (Ngrok/Pinggy)**: Seamlessly bypass the 60-minute session limits by choosing Ngrok (6 hours). Uses a dynamic regex engine to inject your Auth Token directly into the workflow.
- **Audio Redirection**: Natively streams sound from the cloud desktop directly to your local computer (Supports Windows `Audiosrv` & Linux `pulseaudio-module-xrdp` on-the-fly compilation).
- **Multi-Architecture**: Automatically utilizes QEMU to emulate `arm64` environments for testing cross-platform compatibility.

---

## Installation Guide

This script runs on Python and requires Git and the GitHub CLI (`gh`). Below are the installation instructions for your specific host operating system.

### Linux

Choose your distribution below to see the exact commands to install dependencies, clone the repo, and start the script!

<details>
<summary><b>Debian / Ubuntu</b> (Click to expand)</summary>

```bash
sudo apt update && sudo apt install python3 python3-pip git gh -y
git clone https://github.com/pdev-labs/Free-Github-Actions-RDP-for-App-Testing.git
cd Free-Github-Actions-RDP-for-App-Testing
pip install -r requirements.txt
gh auth login
```
</details>

<details>
<summary><b>Arch Linux / Manjaro</b> (Click to expand)</summary>

```bash
sudo pacman -S python python-pip git github-cli --noconfirm
git clone https://github.com/pdev-labs/Free-Github-Actions-RDP-for-App-Testing.git
cd Free-Github-Actions-RDP-for-App-Testing
pip install -r requirements.txt
gh auth login
```
</details>

<details>
<summary><b>Fedora</b> (Click to expand)</summary>

```bash
sudo dnf install python3 python3-pip git gh -y
git clone https://github.com/pdev-labs/Free-Github-Actions-RDP-for-App-Testing.git
cd Free-Github-Actions-RDP-for-App-Testing
pip install -r requirements.txt
gh auth login
```
</details>

<details>
<summary><b>RHEL / CentOS / AlmaLinux</b> (Click to expand)</summary>

```bash
sudo yum install epel-release -y
sudo yum install python3 python3-pip git gh -y
git clone https://github.com/pdev-labs/Free-Github-Actions-RDP-for-App-Testing.git
cd Free-Github-Actions-RDP-for-App-Testing
pip install -r requirements.txt
gh auth login
```
</details>

<details>
<summary><b>openSUSE</b> (Click to expand)</summary>

```bash
sudo zypper install python3 python3-pip git gh
git clone https://github.com/pdev-labs/Free-Github-Actions-RDP-for-App-Testing.git
cd Free-Github-Actions-RDP-for-App-Testing
pip install -r requirements.txt
gh auth login
```
</details>

### macOS
```bash
# 1. Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install Dependencies
brew install python git gh

# 3. Clone the repository
git clone https://github.com/pdev-labs/Free-Github-Actions-RDP-for-App-Testing.git
cd Free-Github-Actions-RDP-for-App-Testing

# 4. Install Python requirements
pip3 install -r requirements.txt

# 5. Authenticate GitHub CLI
gh auth login
```

### Windows
```powershell
# 1. Install Winget (if not installed, available via Microsoft Store)
# 2. Install Dependencies via PowerShell (Run as Administrator)
winget install Python.Python.3.11 Git.Git GitHub.cli

# 3. Clone the repository
git clone https://github.com/pdev-labs/Free-Github-Actions-RDP-for-App-Testing.git
cd Free-Github-Actions-RDP-for-App-Testing

# 4. Install Python requirements
pip install -r requirements.txt

# 5. Authenticate GitHub CLI
gh auth login
```

### Termux (Android)
*Yes, you can deploy cloud desktops directly from your phone!*
```bash
# 1. Update and Install Dependencies
pkg update && pkg upgrade
pkg install python git gh openssh

# 2. Clone the repository
git clone https://github.com/pdev-labs/Free-Github-Actions-RDP-for-App-Testing.git
cd Free-Github-Actions-RDP-for-App-Testing

# 3. Install Python requirements
pip install -r requirements.txt

# 4. Authenticate GitHub CLI
gh auth login
```

---

## Usage Guide

Once installed and authenticated with `gh auth login`, simply launch the interactive provisioner:

```bash
python rdp.py
```

### 1. Repository Creation
The script will ask you for a repository name (e.g., `my-cloud-desktop`). It will autonomously create this private repository on your GitHub account and prepare the workflow templates.

### 2. Standard OS Provisioning (Linux, Windows, macOS)
1. Select `linux`, `windows`, or `macos`.
2. Choose your interaction mode:
  - **GUI (RDP/VNC)**: Full graphical desktop experience.
  - **CLI (SSH)**: Blazing-fast headless terminal access (ideal for macOS M1/latest or Windows PowerShell).
3. If you select Linux, choose your CPU architecture (`amd64` or `arm64`), Distribution, Desktop Environment, and pre-installed toolkits!
4. The script will push the code to your GitHub repo and trigger the workflow automatically.
5. Check your terminal output or your GitHub Actions logs for the connection credentials and `pinggy.link` URL!

### 3. Custom ISO Testing
The `custom_iso` feature bypasses standard host operating systems and boots your own `.iso` file using QEMU nested virtualization.

1. **Select `custom_iso`** from the OS menu.
2. **Choose ISO Source**:
  - **Direct Download URL**: Provide an HTTP/HTTPS link to the `.iso`. The Action will download it directly at gigabit speeds via multi-threaded `aria2c`.
  - **Local File**: Enter the path to an `.iso` file on your computer.
3. **Choose Transfer Method (Local File Only)**:
  - **Cloud Upload**: Automatically slices and uploads your ISO to a hidden GitHub Release.
  - **P2P Local Stream**: Starts a local web server and streams the ISO straight from your hard drive into the cloud! (Keep your terminal open).
4. **Connect via VNC**: Check the Actions logs for the Pinggy VNC URL and connect using RealVNC, TigerVNC, or macOS Screen Sharing.

---

## Architecture & Technical Details

### GitHub Actions Isolation & PAM Constraints
GitHub Actions Linux runners execute jobs inside isolated Docker containers. This causes severe issues with `xrdp-sesman` because standard Linux distributions expect kernel audit modules (`pam_loginuid.so`) or direct `/etc/shadow` access, which are heavily restricted.
This script forcefully patches the PAM configuration inside the runtime container, explicitly unlocks users, and adds `xrdp` to the `shadow` group to allow secure hash verification.

### macOS Authentication Bypass (Apple Silicon)
Apple has locked down headless authentication on modern architectures via System Integrity Protection (SIP) and SecureToken. This script automatically bypasses `sysadminctl` password failures by generating an ED25519 SSH key pair locally and injecting the public key into the runner's `authorized_keys`, granting you instantaneous passwordless access.

### Network Tunneling
Because GitHub Actions runners are behind strict inbound firewalls, we utilize reverse SSH tunneling via Pinggy to expose the `3389` (RDP), `22` (SSH), or `5900` (VNC) ports back to the public internet securely.

### Pinggy 60-Minute Bypass & OS Warning System
Pinggy's free tier has a hard limit of 60 minutes per tunnel. To prevent unexpected data loss, this framework incorporates a completely autonomous bypass and warning architecture:
- **The Warning**: At precisely the 55-minute mark, the script aggressively injects a native UI warning directly onto your cloud desktop (using `osascript` on macOS, `notify-send` on Linux, and a direct `wtsapi32.dll` C# payload on Windows).
- **The Bypass**: At the 57-minute mark, the script autonomously kills the active Pinggy tunnel and immediately restarts a brand-new one to bypass the 60-minute limit.
- **Session Persistence**: Because the tunnel engine is fully decoupled from the actual Desktop Environment (XFCE/GNOME/Windows), **your session remains 100% active in the background**. Any open Chrome tabs, running scripts, or downloading files will continue uninterrupted! Just check the GitHub Actions logs for the newly generated URL, reconnect, and resume exactly where you left off.

---

## Troubleshooting

Running into issues deploying your environment or connecting to the tunnel?
We have moved all known bugs and fixes to a dedicated troubleshooting guide!

 **[Read the Troubleshooting Guide here](TROUBLESHOOTING.md)**

---

## License
This project is licensed under the **GNU General Public License v3.0** (GPLv3). See the `LICENSE` file for full details.

---

## Developer Guide (Build from Source)

Want to hack on the core engine, add your own custom Linux distribution, or fix a bug?
We have a comprehensive **Local Development & Build from Source Guide**.

 **[Read the CONTRIBUTING.md Guide](CONTRIBUTING.md)** to learn how the architecture works, how to set up your local Python Virtual Environment, and how to submit Pull Requests!

---

## Feedback & Support

We are constantly improving the framework! If you encounter any bugs, have a brilliant idea for a new feature, or want to suggest improvements (like more OS distributions or desktop environments), we want to hear from you!

Please report all issues and feature requests by opening an **Issue** on the official repository:
 [Submit an Issue or Feature Request here](https://github.com/pdev-labs/Free-Github-Actions-RDP-for-App-Testing/issues)

If you'd like to contribute directly to the code, feel free to fork the repository and submit a Pull Request!
