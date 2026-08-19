# GitHub Actions RDP Provisioner

> [!WARNING]
> **EDUCATIONAL AND TESTING PURPOSES ONLY**
> This script and the resulting environments are strictly intended for educational, CI/CD debugging, and temporary testing purposes. 
> Do **NOT** use this tool to mine cryptocurrency, host illegal content, perform denial-of-service attacks, or violate GitHub's Terms of Service. Doing so will likely result in an immediate and permanent ban of your GitHub account. You are solely responsible for how you use this tool.

A powerful Python script that automates the provisioning of fully interactive, GUI-enabled Desktop environments (Linux, Windows, and macOS) directly inside GitHub Actions runners. It utilizes [Pinggy](https://pinggy.io/) to securely tunnel the RDP/VNC connection out of the isolated GitHub environment to your local machine.

## 🚀 Features
- **Multi-OS Support**: Provision environments across Linux, Windows, and macOS.
- **Extensive Linux Distributions**: Choose from Ubuntu, Debian, Kali Linux, Arch Linux, Fedora, Linux Mint, and Manjaro.
- **Desktop Environments**: Instantly spin up XFCE, GNOME, KDE, i3wm, or run in headless CLI mode.
- **Custom ISO Booting (QEMU Nested Virtualization)**: Boot **ANY** operating system (like PearOS, Windows PE, custom Linux spins) from an `.iso` file directly inside the GitHub Action! Supports file splitting for large files >2GB, Peer-to-Peer streaming, and direct URL downloading.
- **Pre-installed Tooling**: Select from curated lists of tools (Browsers, Editors, Docker, Network Tools) to be pre-installed upon boot.
- **Automatic PAM Patching**: Bypasses strict Docker container PAM (Pluggable Authentication Module) restrictions so that `xrdp` authentication works flawlessly out-of-the-box.
- **Multi-Architecture**: Automatically utilizes QEMU to emulate `arm64` environments if requested.

---

## 📖 Step-by-Step Usage Guide

### 1. Prerequisites
Before running the script, ensure you have the following installed:
- Python 3.x
- [GitHub CLI (`gh`)](https://cli.github.com/)
- `git`

You must authenticate the GitHub CLI with your account:
```bash
gh auth login
```

### 2. Standard OS Provisioning (Linux, Windows, macOS)
If you want to quickly test a standard operating system:
1. **Run the generator script:**
   ```bash
   python rdp.py
   ```
2. **Name your Workspace:** Enter a name for the repository that will be created on your GitHub account (e.g., `my-rdp-testing`).
3. **Select OS & Distro:** Choose `linux`, `windows`, or `macos`. If you select Linux, you'll be prompted to pick a specific distribution and architecture (`amd64` or `arm64`).
4. **Customize the Desktop Environment:** Choose between XFCE, GNOME, KDE, i3wm, or stock.
5. **Add Apps:** Optionally pre-install Docker, Nmap, build tools, or web browsers by entering a comma-separated list of numbers.
6. **Connect:** The script will push the workflow to GitHub and trigger it. Open the provided repository URL, navigate to the **Actions** tab, and click the running workflow. Wait for the `Start Pinggy tunnel` step to output your RDP/VNC connection URL and credentials!

### 3. Custom ISO Testing Guide
The `custom_iso` feature allows you to bypass the standard operating systems and boot your own custom `.iso` file using QEMU nested virtualization inside the GitHub Action runner.

1. **Select `custom_iso`**: When prompted for the OS, type `custom_iso`.
2. **Choose the ISO Source**:
   - **Direct Download URL**: If the `.iso` is hosted online (e.g., `https://example.com/pearos.iso`), select option `2` and provide the URL. The GitHub Action will use its ultra-fast datacenter gigabit internet to download it directly!
   - **Local File**: If the `.iso` is on your local hard drive, select option `1` and enter the absolute path (e.g., `/home/user/Downloads/my_os.iso`).
3. **Choose a Transfer Method (If using a Local File)**:
   - **Method 1: GitHub Releases (Cloud)**: The script will automatically upload your ISO to a hidden GitHub Release on your repository. If the file is larger than the 2GB GitHub limit, the script will intelligently split it into 1.9GB chunks, upload them, and the GitHub Action will automatically merge them back together before booting. This method is completely autonomous.
   - **Method 2: Peer-to-Peer (Local Stream)**: The script will start a temporary web server on your local machine and open a secure Pinggy tunnel. The GitHub Action will pull the ISO directly from your computer's hard drive! *Note: You must keep your terminal open during the boot phase for this to work.*
4. **Connect via VNC**: Unlike the standard environments that use RDP, the Custom ISO feature exposes the native QEMU VNC server. Check your GitHub Action logs for the Pinggy VNC URL and connect using any standard VNC client. You will see the native BIOS/UEFI boot screen and can proceed with the OS installation just like a real machine!

---

## 🛠️ Technical Details (Linux PAM Fixes)
GitHub Actions Linux runners execute jobs inside isolated Docker containers (`--privileged` is not always sufficient depending on the daemon). This causes severe issues with `xrdp-sesman` because standard Linux distributions expect kernel audit modules (`pam_loginuid.so`), `systemd-logind`, or direct `/etc/shadow` access, which are stripped from Docker base images.

This script forcefully patches the PAM configuration inside the container by:
- Disabling `pam_loginuid.so`.
- Hardcoding a minimal `pam_unix.so` authentication flow for `xrdp-sesman`.
- Explicitly installing the `passwd` package and unlocking the user account.
- Adding `xrdp` to the `shadow` group to allow hash verification.
- Enabling `AllowRootLogin=true` as a fallback.

## ⚖️ License
This project is licensed under the **GNU General Public License v3.0** (GPLv3). See the `LICENSE` file for full details.
