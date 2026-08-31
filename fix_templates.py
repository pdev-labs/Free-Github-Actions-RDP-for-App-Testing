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
        sleep 21600
{% elif tunnel == 'ngrok' %}
        {{ ngrok_cmd }}
        sleep 21600
{% elif tunnel == 'cloudflare' %}
        wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
        sudo dpkg -i cloudflared-linux-amd64.deb || true
        cloudflared tunnel --url tcp://localhost:{{ port }} > /pinggy.log 2>&1 &
        sleep 21600
{% elif tunnel == 'tailscale' %}
        curl -fsSL https://tailscale.com/install.sh | sh
        sudo tailscale up --authkey={{ ngrok_token }} --hostname=github-actions-runner
        sleep 21600
{% endif %}""".replace('\\', '\\\\')

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
        sleep 21600
{% elif tunnel == 'ngrok' %}
        {{ ngrok_cmd }}
        sleep 21600
{% elif tunnel == 'cloudflare' %}
        choco install cloudflared -y
        cloudflared tunnel --url tcp://localhost:{{ port }} > pinggy.log 2>&1 &
        sleep 21600
{% elif tunnel == 'tailscale' %}
        choco install tailscale -y
        & 'C:\\Program Files\\Tailscale\\tailscale.exe' up --authkey={{ ngrok_token }} --hostname=github-actions-runner
        sleep 21600
{% endif %}""".replace('\\', '\\\\')

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
        sleep 21600
{% elif tunnel == 'ngrok' %}
        {{ ngrok_cmd }}
        sleep 21600
{% elif tunnel == 'cloudflare' %}
        brew install cloudflare/cloudflare/cloudflared
        cloudflared tunnel --url tcp://localhost:{{ port }} > pinggy.log 2>&1 &
        sleep 21600
{% elif tunnel == 'tailscale' %}
        brew install tailscale
        sudo tailscaled &
        sleep 5
        sudo tailscale up --authkey={{ ngrok_token }} --hostname=github-actions-runner
        sleep 21600
{% endif %}""".replace('\\', '\\\\')

tpl_dir = "rdp_Jinja2/templates/"
for file in os.listdir(tpl_dir):
    with open(os.path.join(tpl_dir, file), "r") as f:
        text = f.read()

    replacement = tunnel_pinggy
    if "windows" in file:
        replacement = tunnel_pinggy_windows
    elif "macos" in file:
        replacement = tunnel_pinggy_macos
        
    text = re.sub(r'ssh -T -p 443 -R0:localhost:\{\{\s*port\s*\}\} -o StrictHostKeyChecking=no.*?\n\s*sleep 21600', replacement, text, flags=re.DOTALL)
    
    with open(os.path.join(tpl_dir, file), "w") as f:
        f.write(text)

print("Templates fixed.")
