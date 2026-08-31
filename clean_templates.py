import os
import re

tunnel_pinggy = """{% if tunnel == 'pinggy' %}
        while true; do
            ssh -T -p 443 -R0:localhost:{{ port }} -o StrictHostKeyChecking=no -o ServerAliveInterval=30 tcp@a.pinggy.io > /pinggy.log 2>&1 &
            SSH_PID=$!
            sleep 3300
            echo "[$(date)] 55 minutes reached. Firing OS warning popup..."
            {{ popup_cmd }}
            sleep 120
            echo "[$(date)] 57 minutes reached. Restarting Pinggy tunnel to bypass 60-min limit..."
            kill $SSH_PID
            sleep 2
        done
{% elif tunnel == 'ngrok' %}
        {{ ngrok_cmd }}
{% elif tunnel == 'cloudflare' %}
        wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
        sudo dpkg -i cloudflared-linux-amd64.deb || true
        cloudflared tunnel --url tcp://localhost:{{ port }} > /pinggy.log 2>&1 &
{% elif tunnel == 'tailscale' %}
        curl -fsSL https://tailscale.com/install.sh | sh
        sudo tailscale up --authkey={{ ngrok_token }} --hostname=github-actions-runner
{% endif %}
        sleep 21600"""

tunnel_pinggy_windows = """{% if tunnel == 'pinggy' %}
        while true; do
            ssh -T -p 443 -R0:localhost:{{ port }} -o StrictHostKeyChecking=no -o ServerAliveInterval=30 tcp@a.pinggy.io > pinggy.log 2>&1 &
            SSH_PID=$!
            sleep 3300
            echo "[$(date)] 55 minutes reached. Firing OS warning popup..."
            {{ popup_cmd }}
            sleep 120
            echo "[$(date)] 57 minutes reached. Restarting Pinggy tunnel to bypass 60-min limit..."
            kill $SSH_PID
            sleep 2
        done
{% elif tunnel == 'ngrok' %}
        {{ ngrok_cmd }}
{% elif tunnel == 'cloudflare' %}
        choco install cloudflared -y
        cloudflared tunnel --url tcp://localhost:{{ port }} > pinggy.log 2>&1 &
{% elif tunnel == 'tailscale' %}
        choco install tailscale -y
        & 'C:\\Program Files\\Tailscale\\tailscale.exe' up --authkey={{ ngrok_token }} --hostname=github-actions-runner
{% endif %}
        sleep 21600"""

tunnel_pinggy_macos = """{% if tunnel == 'pinggy' %}
        while true; do
            ssh -T -p 443 -R0:localhost:{{ port }} -o StrictHostKeyChecking=no -o ServerAliveInterval=30 tcp@a.pinggy.io > pinggy.log 2>&1 &
            SSH_PID=$!
            sleep 3300
            echo "[$(date)] 55 minutes reached. Firing OS warning popup..."
            {{ popup_cmd }}
            sleep 120
            echo "[$(date)] 57 minutes reached. Restarting Pinggy tunnel to bypass 60-min limit..."
            kill $SSH_PID
            sleep 2
        done
{% elif tunnel == 'ngrok' %}
        {{ ngrok_cmd }}
{% elif tunnel == 'cloudflare' %}
        brew install cloudflare/cloudflare/cloudflared
        cloudflared tunnel --url tcp://localhost:{{ port }} > pinggy.log 2>&1 &
{% elif tunnel == 'tailscale' %}
        brew install tailscale
        sudo tailscaled &
        sleep 5
        sudo tailscale up --authkey={{ ngrok_token }} --hostname=github-actions-runner
{% endif %}
        sleep 21600"""

tpl_dir = "rdp_Jinja2/templates/"
for file in os.listdir(tpl_dir):
    with open(os.path.join(tpl_dir, file), "r") as f:
        text = f.read()

    replacement = tunnel_pinggy
    if "windows" in file:
        replacement = tunnel_pinggy_windows
    elif "macos" in file:
        replacement = tunnel_pinggy_macos
        
    # Find the start of {% if tunnel == 'pinggy' %}
    start_idx = text.find("{% if tunnel == 'pinggy' %}")
    if start_idx == -1:
        continue
        
    # We need to find where the corrupted block ends.
    # In linux.yml.j2, it ends right before `EOF` and `chmod +x setup.sh`
    # In others, it ends right before `        else\n            echo "Error: Pinggy failed to start.` or just ends the file.
    
    # Let's use a regex to match from the first `{% if tunnel == 'pinggy' %}` all the way to `sleep 21600\n{% endif %}` or `sleep 21600`
    # Wait, the corruption includes multiple `sleep 21600\n{% endif %}` and maybe dangling `else`.
    
    # For linux.yml.j2, the block is followed by `        EOF\n        chmod +x setup.sh`
    if file == 'linux.yml.j2':
        end_idx = text.find("        EOF\n        chmod +x setup.sh")
        if end_idx != -1:
            text = text[:start_idx] + replacement + "\n" + text[end_idx:]
    else:
        # For macos, windows, custom_iso, the file ends with the tunnel logic, OR it ends with the old `else ... cat pinggy.log ... fi`
        # Let's just truncate at start_idx and append the replacement!
        text = text[:start_idx] + replacement + "\n"

    with open(os.path.join(tpl_dir, file), "w") as f:
        f.write(text)

print("Templates cleaned.")
