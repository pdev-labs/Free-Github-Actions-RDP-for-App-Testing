# 🐛 Troubleshooting Guide

Welcome to the troubleshooting guide! If you are facing issues deploying or connecting to your cloud desktop, check the table below for known issues and their solutions.

| Issue | Cause & Solution |
| :--- | :--- |
| **"User does not exist or cannot authenticate"** | (Linux RDP) Ensure you typed the password exactly as `ThePassword123!`. |
| **Pinggy connection drops after 60 mins** | The free tier of Pinggy has a strict 60-minute session limit per tunnel. (Our framework now automatically bypasses this by generating a new URL every 57 minutes!) |
| **Workflow Dispatch HTTP 422 Error** | The `gh` CLI was unable to trigger the workflow automatically. Go to your GitHub Repo -> Actions -> Run Workflow manually. |
| **"unknown terminal type" on SSH login** | This script forces `TERM=xterm-256color`. If it persists, type `export TERM=xterm-256color` in the remote terminal. |
| **Aria2c download seems stuck** | In GitHub Actions, `aria2c` disables live progress bars. Check the initial ETA. |
| **No Audio on Windows Server** | Ensure you are using the latest version of this script, which automatically injects Registry overrides to bypass Windows Server Group Policy restrictions on audio. |

If your issue is not listed here, please [open an issue](https://github.com/pdev-labs/Free-Github-Actions-RDP-for-App-Testing/issues) on the main repository!
