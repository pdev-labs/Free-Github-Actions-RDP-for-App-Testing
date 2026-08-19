# GitHub Actions RDP & VNC Provisioner

<div align="center">
  <h3>Automated Cloud Desktop Environments inside GitHub Actions</h3>
</div>

> [!WARNING]
> **EDUCATIONAL AND TESTING PURPOSES ONLY**
> This script and the resulting environments are strictly intended for educational, CI/CD debugging, and temporary testing purposes. 
> Do **NOT** use this tool to mine cryptocurrency, host illegal content, perform denial-of-service attacks, or violate GitHub's Terms of Service. Doing so will likely result in an immediate and permanent ban of your GitHub account. You are solely responsible for how you use this tool.

A powerful Python automation script that dynamically provisions fully interactive, GUI-enabled Desktop environments (Linux, Windows, macOS, and custom ISOs) directly inside GitHub Actions runners. It utilizes [Pinggy](https://pinggy.io/) to securely tunnel the RDP/VNC connection out of the isolated GitHub infrastructure directly to your local machine.

---

## 🚀 Key Features
- **Multi-OS Support**: Native provisioning across Linux, Windows, and macOS host runners.
- **Custom ISO Booting (QEMU Nested Virtualization)**: Boot **ANY** operating system (like PearOS, Windows PE, BSD, or custom Linux spins) from a raw `.iso` file directly inside the GitHub Action! 
  - **Auto File-Splitting**: Intelligently handles ISOs larger than GitHub's 2GB limit by splitting, uploading, and merging chunks.
  - **P2P Local Streaming**: Stream an ISO directly from your local hard drive into the cloud runner without uploading it!
  - **Multi-Threaded Direct Links**: Supports ultra-fast multi-threaded downloading (via `aria2c`) if you provide a direct ISO link.
- **Extensive Linux Distributions**: Choose from Ubuntu, Debian, Kali Linux, Arch Linux, Fedora, Linux Mint, and Manjaro.
- **Desktop Environments**: Instantly spin up XFCE, GNOME, KDE Plasma, i3wm, or run in headless CLI-only mode.
- **Automatic PAM Patching**: Bypasses strict Docker container PAM (Pluggable Authentication Module) restrictions so that `xrdp` authentication works flawlessly out-of-the-box.
- **Multi-Architecture**: Automatically utilizes QEMU to emulate `arm64` environments for testing cross-platform compatibility.

---

## 📖 Step-by-Step Usage Guide

### 1. Initial Setup
Before running the script, ensure you have the following installed on your local machine:
- **Python 3.x**
- **[GitHub CLI (`gh`)](https://cli.github.com/)**
- **Git**

You must authenticate the GitHub CLI with your account so the script can autonomously create repositories and push workflows:
```bash
gh auth login
```

### 2. Standard OS Provisioning (Linux, Windows, macOS)
If you want to quickly test a standard operating system:
1. Run the generator script:
   ```bash
   python rdp.py
   ```
2. **Name your Workspace:** Enter a name for the repository that will be generated on your GitHub account (e.g., `my-rdp-testing`).
3. **Select OS & Distro:** Choose `linux`, `windows`, or `macos`. If you select Linux, you'll be prompted to pick a specific distribution and architecture (`amd64` or `arm64`).
4. **Customize the Desktop Environment:** Choose between XFCE, GNOME, KDE, i3wm, or stock.
5. **Connect:** The script will automatically commit, push, and trigger the workflow. Open your GitHub repository's **Actions** tab, and click the running workflow. Wait for the `Start Pinggy tunnel` step to output your connection URL!

### 3. Custom ISO Testing Guide
The `custom_iso` feature allows you to bypass the standard operating systems and boot your own custom `.iso` file using QEMU nested virtualization inside the GitHub Action runner.

1. **Select `custom_iso`**: When prompted for the OS in the script, type `custom_iso`.
2. **Choose the ISO Source**:
   - **Direct Download URL**: If the `.iso` is hosted online, select option `2` and provide the URL. The GitHub Action will use `aria2c` multi-threading to download it directly at gigabit speeds!
   - **Local File**: If the `.iso` is on your local hard drive, select option `1` and enter the absolute path on your computer.
3. **Choose a Transfer Method (If using a Local File)**:
   - **Method 1: GitHub Releases (Cloud)**: The script will automatically upload your ISO to a hidden GitHub Release on your repository. If the file is larger than the 2GB GitHub limit, the script will slice it into 1.9GB chunks, upload them, and the Action will automatically merge them back together before booting.
   - **Method 2: Peer-to-Peer (Local Stream)**: The script will start a temporary web server on your local machine and open a secure Pinggy tunnel. The GitHub Action will pull the ISO directly from your computer's hard drive! *Note: You must keep your terminal open during the boot phase for this to work.*
4. **Connect via VNC**: The Custom ISO feature exposes the native QEMU VNC server. Check your GitHub Action logs for the Pinggy VNC URL and connect using any standard VNC client (RealVNC, TigerVNC, macOS Screen Sharing). No password is required.

---

## 🏗️ Architecture & Technical Details

### GitHub Actions Isolation & PAM Constraints
GitHub Actions Linux runners execute jobs inside isolated Docker containers (`--privileged` is not always sufficient depending on the daemon). This causes severe issues with `xrdp-sesman` because standard Linux distributions expect kernel audit modules (`pam_loginuid.so`), `systemd-logind`, or direct `/etc/shadow` access, which are heavily restricted in Docker base images.

### Automated Mitigation
This script forcefully patches the PAM configuration inside the runtime container by:
- Disabling `pam_loginuid.so`.
- Hardcoding a minimal `pam_unix.so` authentication flow for `xrdp-sesman`.
- Explicitly installing the `passwd` package and unlocking the generated user account.
- Adding `xrdp` to the `shadow` group to allow secure hash verification.
- Enabling `AllowRootLogin=true` inside `sesman.ini` as a fallback mechanism.

### Network Tunneling
Because GitHub Actions runners are behind strict inbound firewalls, we utilize reverse SSH tunneling via Pinggy to expose the `3389` (RDP), `22` (SSH), or `5900` (VNC) ports back to the public internet securely.

---

## 🐛 Troubleshooting

| Issue | Cause & Solution |
| :--- | :--- |
| **"User does not exist or cannot authenticate"** | The XRDP session manager failed to read `/etc/shadow`. Ensure you typed the password exactly as `ThePassword123!` and didn't accidentally copy leading/trailing spaces. |
| **Pinggy connection drops after 60 mins** | The free tier of Pinggy has a strict 60-minute session limit. The GitHub Action will stay alive, but the tunnel will drop. |
| **Workflow Dispatch HTTP 422 Error** | If you see this in your terminal, the `gh` CLI was unable to trigger the workflow. Just go to your GitHub Repo -> Actions -> Run Workflow manually. |
| **Aria2c download seems stuck** | In GitHub Actions, `aria2c` disables live progress bars to avoid spamming logs. It is downloading! Check the ETA in the initial log message. |

---

## ⚖️ License
This project is licensed under the **GNU General Public License v3.0** (GPLv3). See the `LICENSE` file for full details.
