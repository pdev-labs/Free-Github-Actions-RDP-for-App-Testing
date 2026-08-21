# Troubleshooting Guide

Welcome to the comprehensive troubleshooting guide for the Free GitHub Actions RDP for App Testing framework. 
Because this framework relies on ephemeral cloud runners, nested virtualization, and reverse SSH tunneling, a few environmental quirks can occasionally occur.

This guide is broken down by category to help you quickly diagnose and resolve any issues.

---

## 1. Authentication & Login Issues

### "User does not exist or cannot authenticate" (Linux RDP)
**Cause:** The XRDP server running inside the GitHub Actions Docker container failed to verify your credentials against the shadow password file due to strict PAM (Pluggable Authentication Module) restrictions.
**Solution:**
1. Ensure you typed the password exactly as `ThePassword123!` (case-sensitive).
2. If the issue persists, the automatic PAM patching script may have failed to execute. Check the GitHub Actions logs for the step named `Patch PAM and Shadow Group` to verify it ran successfully.
3. Try restarting the session or switching to a different Desktop Environment (e.g., from GNOME to XFCE).

### "Permission denied (publickey)" (macOS CLI/SSH)
**Cause:** Apple's SecureToken system blocked the creation of the user password via `sysadminctl`.
**Solution:**
1. The script bypasses this by generating an ED25519 SSH key pair and injecting it directly into `authorized_keys`.
2. Do not attempt to use a password to log into the macOS SSH session. Instead, use the exact SSH command provided in the terminal output or Actions logs (which includes the `-i` flag pointing to your newly generated private key).

---

## 2. Connectivity & Tunneling Issues

### Pinggy Connection Drops Exactly After 60 Minutes
**Cause:** The free tier of Pinggy has a strict 60-minute session limit per tunnel.
**Solution:**
Our framework now includes a completely automated bypass system! 
1. The script will automatically trigger a native UI warning directly onto your cloud desktop at the 55-minute mark.
2. At the 57-minute mark, the script autonomously kills the active Pinggy tunnel and immediately restarts a brand-new one.
3. Your session remains 100% active in the background. Simply go back to your GitHub Actions run logs, fetch the newly generated URL, and reconnect to resume your work instantly.

### Black Screen or "Connection Refused" Upon Reconnecting
**Cause:** The VNC or RDP server process may have crashed, or you are attempting to connect to a stale Pinggy URL.
**Solution:**
1. Verify that you are using the most recent Pinggy URL. If the 57-minute bypass just executed, the old URL is permanently dead. You must retrieve the new URL from the Actions logs.
2. If you are using Windows, ensure you are using a standard RDP client (like Microsoft Remote Desktop). VNC clients will not work for the Windows OS choice.
3. If you are using Linux or macOS, ensure your VNC client supports high-color depth and dynamic resolution. We recommend RealVNC Viewer or TigerVNC.

---

## 3. Audio & Video Redirection

### No Audio on Windows Server
**Cause:** GitHub Actions Windows runners utilize Windows Server 2022. By default, Windows Server enforces a Group Policy that aggressively bans audio playback and microphone capture over RDP to save bandwidth.
**Solution:**
This framework automatically injects Registry overrides (`fAllowAudioPlayback` and `fDisableAudioCapture`) to bypass these group policies and force the `Audiosrv` to start.
1. If audio still fails, ensure your local RDP client is configured to "Play on this computer".
2. Open the "Remote Desktop Connection" app on your local PC -> Show Options -> Local Resources -> Remote audio -> Settings -> Select "Play on this computer".

### Audio Stuttering on Linux
**Cause:** The Linux environment compiles the `pulseaudio-module-xrdp` bridge on the fly. High CPU usage on the cloud runner can cause buffer underruns.
**Solution:**
1. Lower your RDP client's color depth setting from 32-bit to 16-bit to free up bandwidth.
2. Restart the pulseaudio daemon inside the cloud runner via terminal: `pulseaudio -k && pulseaudio --start`.

---

## 4. Custom ISO & Virtualization

### Aria2c ISO Download Seems Stuck
**Cause:** GitHub Actions suppresses continuous terminal output to prevent log flooding. Because `aria2c` relies on live progress bars, the output may appear frozen.
**Solution:** 
Do not cancel the job. Check the initial ETA printed before the output paused. Gigabit download speeds mean most ISOs (2GB - 4GB) will finish downloading silently in under 60 seconds.

### ISO Fails to Boot (Stuck at UEFI/BIOS Screen)
**Cause:** The ISO lacks proper UEFI boot loaders, or requires specific ACPI AC/Battery flags not supported by the headless QEMU engine.
**Solution:**
1. Ensure the ISO is an `amd64`/`x86_64` architecture (ARM ISOs cannot be natively booted via QEMU on GitHub's x64 runners without extreme performance degradation).
2. For legacy operating systems, you may need to manually edit the `rdp.py` script to remove the `-bios /usr/share/ovmf/OVMF.fd` flag to force Legacy BIOS mode instead of UEFI.

---

## 5. Deployment Errors

### Workflow Dispatch HTTP 422 Error
**Cause:** The GitHub CLI (`gh`) was unable to trigger the workflow automatically, usually because the workflow file hasn't been indexed by GitHub's backend yet, or due to a lack of `workflow` scope permissions.
**Solution:**
1. Navigate directly to your GitHub Repository in your web browser.
2. Click on the **Actions** tab.
3. Select the workflow from the left sidebar.
4. Click the **Run workflow** dropdown on the right side and execute it manually.

---

## Getting More Help
If your issue is not listed here, or you believe you have discovered a new bug, please open a detailed issue on the main repository! Include the OS choice, Desktop Environment, and any relevant logs.

[Submit an Issue here](https://github.com/pdev-labs/Free-Github-Actions-RDP-for-App-Testing/issues)
