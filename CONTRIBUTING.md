# Contributing to GitHub Actions RDP Provisioner

First off, thank you for considering contributing to this project! It's people like you that make the open-source community such an amazing place to learn, inspire, and create.

## 🧠 How Can I Contribute?

### 1. Reporting Bugs
If you find a bug, please open an issue in the repository. Provide as much detail as possible, including:
- Your host operating system (Windows, Linux, macOS).
- The exact distribution/environment you were trying to provision.
- The logs from the GitHub Actions console.
- Steps to reproduce the behavior.

### 2. Suggesting Enhancements
We are always looking to support more Linux distributions, Desktop Environments, and tunneling providers! If you have a brilliant idea, open a Feature Request issue.

### 3. Submitting Pull Requests
If you want to contribute code directly, please follow this workflow:
1. **Fork the repository** to your own GitHub account.
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/Free-Github-Actions-RDP-for-App-Testing.git
   cd Free-Github-Actions-RDP-for-App-Testing
   ```
3. **Create a new branch** for your feature or bug fix:
   ```bash
   git checkout -b feature/your-amazing-feature
   ```
4. **Make your changes**. Test them thoroughly by running the script locally and deploying a test runner.
5. **Commit your changes** with clear, descriptive commit messages.
6. **Push the branch** to your fork:
   ```bash
   git push origin feature/your-amazing-feature
   ```
7. **Open a Pull Request** against the `main` branch of this repository.

---

## 🛠️ Local Development & Building from Source

To set up a local development environment to hack on the core engine (`rdp.py`), follow these steps:

### Prerequisites
- Python 3.8+
- Git
- GitHub CLI (`gh`) - authenticated via `gh auth login`

### Setup Environment
It is highly recommended to use a Python Virtual Environment to avoid dependency conflicts:
```bash
# 1. Create a virtual environment
python3 -m venv venv

# 2. Activate the virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
.\\venv\\Scripts\\activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Architecture Overview for Developers
- `rdp.py`: The core transpilation engine. It acts as both the CLI TUI (Terminal User Interface) and the workflow template generator.
- **Templates**: The massive multi-line string constants at the top of `rdp.py` (e.g., `LINUX_WORKFLOW_TEMPLATE`, `WINDOWS_WORKFLOW_TEMPLATE`) are the actual bash/PowerShell scripts executed by the GitHub Action runner.
- **Regex Patching**: The `inject_tunnel_logic` function dynamically patches these templates on-the-fly to support Pinggy/Ngrok injection and OS-specific GUI warnings.

When modifying the templates, **ensure that YAML indentation is strictly preserved**. GitHub Actions will instantly fail if the generated `.github/workflows/rdp.yml` contains invalid spacing.

Thank you for contributing! 🚀
