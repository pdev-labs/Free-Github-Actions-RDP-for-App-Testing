# GitHub Actions RDP Provisioner

> [!WARNING]
> **EDUCATIONAL AND TESTING PURPOSES ONLY**
> This script and the resulting environments are strictly intended for educational, CI/CD debugging, and temporary testing purposes. 
> Do **NOT** use this tool to mine cryptocurrency, host illegal content, perform denial-of-service attacks, or violate GitHub's Terms of Service. Doing so will likely result in an immediate and permanent ban of your GitHub account. You are solely responsible for how you use this tool.

A powerful Python script that automates the provisioning of fully interactive, GUI-enabled Desktop environments (Linux, Windows, and macOS) directly inside GitHub Actions runners. It utilizes [Pinggy](https://pinggy.io/) to securely tunnel the RDP/VNC connection out of the isolated GitHub environment to your local machine.

## Features
- **Multi-OS Support**: Provision environments across Linux, Windows, and macOS.
- **Extensive Linux Distributions**: Choose from Ubuntu, Debian, Kali Linux, Arch Linux, Fedora, Linux Mint, and Manjaro.
- **Desktop Environments**: Instantly spin up XFCE, GNOME, KDE, i3wm, or run in headless CLI mode.
- **Pre-installed Tooling**: Select from curated lists of tools (Browsers, Editors, Docker, Network Tools) to be pre-installed upon boot.
- **Automatic PAM Patching**: Bypasses strict Docker container PAM (Pluggable Authentication Module) restrictions so that `xrdp` authentication works flawlessly out-of-the-box.
- **Multi-Architecture**: Automatically utilizes QEMU to emulate `arm64` environments if requested.

## Prerequisites
- Python 3.x
- [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated (`gh auth login`).
- `git` installed.

## Usage
1. Ensure you are logged into your GitHub account via the CLI:
   ```bash
   gh auth status
   ```
   If not, authenticate with:
   ```bash
   gh auth login
   ```

2. Run the generator script:
   ```bash
   python rdp.py
   ```

3. Follow the interactive prompts to select your target OS, distribution, architecture, desktop environment, and extra applications.

4. The script will automatically generate the GitHub Actions workflow (`.github/workflows/rdp.yml`), initialize a repository, and push the code to your GitHub account.

5. Go to your GitHub repository -> **Actions** tab, and open the running workflow. Wait for the `Start Pinggy tunnel` step to execute, and copy your connection URL.

6. Connect using your favorite RDP Client (for Linux/Windows) or VNC Client (for macOS). The default credentials will be printed in the workflow logs (e.g., `runner` / `ThePassword123!`).

## Technical Details (Linux PAM Fixes)
GitHub Actions Linux runners execute jobs inside isolated Docker containers (`--privileged` is not always sufficient depending on the daemon). This causes severe issues with `xrdp-sesman` because standard Linux distributions expect kernel audit modules (`pam_loginuid.so`), `systemd-logind`, or direct `/etc/shadow` access, which are stripped from Docker base images.

This script forcefully patches the PAM configuration inside the container by:
- Disabling `pam_loginuid.so`.
- Hardcoding a minimal `pam_unix.so` authentication flow for `xrdp-sesman`.
- Explicitly installing the `passwd` package and unlocking the user account.
- Adding `xrdp` to the `shadow` group to allow hash verification.
- Enabling `AllowRootLogin=true` as a fallback.

## License
This project is licensed under the **GNU General Public License v3.0** (GPLv3). See the `LICENSE` file for full details.
