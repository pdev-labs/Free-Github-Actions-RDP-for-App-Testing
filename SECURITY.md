# Security Policy & Threat Model

**This project provisions temporary, ephemeral remote desktop environments inside GitHub Actions.** Because these environments are publicly exposed via tunneling services to allow remote access, it is critical to understand the security model, limitations, and risks before using this tool.

---

## 🔐 1. Credential Management

### How Credentials are Generated
- **Windows & Linux (RDP/VNC):** By default, the script provisions these environments with a static, hardcoded username (`runneradmin`) and password (`ThePassword123!`). 
- **macOS (SSH):** Due to strict macOS SecureToken limitations, password authentication is bypassed entirely. Instead, the script autonomously generates a highly secure **ED25519 SSH key pair** dynamically during runtime.

### How Credentials are Transmitted
Connections made to the cloud desktop are routed through reverse tunnels (Pinggy or Ngrok). Both services wrap the connection in secure cryptographic protocols (SSH or TLS/HTTPS).

### Where Secrets are Stored
- **Short-Term Memory:** Credentials and SSH keys exist only in the volatile RAM of the GitHub Action runner.
- **No Persistent Storage:** When the runner is destroyed at the end of the session, all keys, passwords, and data are permanently wiped.

---

## 📡 2. Tunnel Security Model

To bypass GitHub's strict inbound firewalls, this tool uses reverse tunneling.
- **Pinggy**: Generates a randomized, unguessable subdomain (e.g., `udoxp-xxx.run.pinggy-free.link`) over a random high port.
- **Ngrok**: Authenticates using your personal Ngrok Auth Token to establish a static, encrypted tunnel. 

> [!WARNING]  
> **Public Exposure Risk**
> If an attacker intercepts your exact Pinggy URL/Port (or Ngrok URL) AND knows the default hardcoded password, they can gain full graphical access to your session.

---

## 📜 3. GitHub Actions Logs

### What gets printed to the logs?
For you to be able to connect to the environment, the script **must** print connection details directly to the GitHub Actions console logs. 
The logs will visibly contain:
1. The full **Pinggy / Ngrok Connection URL and Port**.
2. The **macOS SSH Private Key** (if deploying a headless macOS runner).

> [!CAUTION]  
> Anyone with "Read" access to your GitHub repository's Action Logs can view the URL and Private Key, allowing them to instantly connect to the running environment. **Always deploy this tool in a Private Repository.**

---

## ⏳ 4. Lifespan & Validity

All credentials, URLs, and environments have a strictly limited lifespan:
- **GitHub Runner Timeout:** GitHub forcibly terminates all workflows after **6 hours**.
- **Pinggy Timeout:** The free tier drops connections after **60 minutes** (though our Keepalive Engine automatically generates a new URL every 57 minutes to bypass this).
Once the workflow terminates, the credentials, SSH keys, and virtual hard drives are irrevocably destroyed.

---

## 🛑 5. What Users Should NEVER Do

This tool is strictly designed for **temporary, disposable testing**. 
Under absolutely no circumstances should you:
- ❌ Log into personal accounts (Banking, Primary Emails, Social Media).
- ❌ Clone proprietary or highly sensitive private repositories.
- ❌ Inject long-lived production secrets (AWS keys, Production API tokens) into the environment.
- ❌ Use the environment to host public-facing websites or illegal content.

---

## 🛡️ 6. Threat Model & Limitations

**Is this safe?** 
Yes, provided you understand that this is a **sandbox**. 
If a malicious actor somehow breaches your session, they are trapped inside an ephemeral Docker container or a heavily restricted GitHub Virtual Machine. They cannot escape the runner to access your local computer, nor can they persist access once the 6-hour runner timer expires.

**The biggest risk is Data Exfiltration.** If you leave a sensitive file open on the remote desktop, and a collaborator reads your Actions log to hijack the session, they can steal that file. **Treat the environment as publicly accessible.**
