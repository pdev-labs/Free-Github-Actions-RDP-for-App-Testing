import ast
import re

with open("rdp.py", "r") as f:
    source = f.read()

source = source[:source.find("def start_p2p_server")]

tree = ast.parse(source)

templates = {}
for node in tree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id.endswith("_WORKFLOW_TEMPLATE"):
                if isinstance(node.value, ast.Constant):
                    templates[target.id] = node.value.value

print(f"Extracted {len(templates)} templates using AST.")

tunnel_pinggy = """{% if tunnel == 'pinggy' %}
        while true; do
            ssh -T -p 443 -R0:localhost:{{ port }} -o StrictHostKeyChecking=no tcp@a.pinggy.io > pinggy.log 2>&1 &
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
        cloudflared tunnel --url tcp://localhost:{{ port }} > pinggy.log 2>&1 &
        sleep 21600
{% elif tunnel == 'tailscale' %}
        curl -fsSL https://tailscale.com/install.sh | sh
        sudo tailscale up --authkey={{ ngrok_token }} --hostname=github-actions-runner
        sleep 21600
{% endif %}""".replace('\\', '\\\\')

tunnel_pinggy_windows = """{% if tunnel == 'pinggy' %}
        while true; do
            ssh -T -p 443 -R0:localhost:{{ port }} -o StrictHostKeyChecking=no tcp@a.pinggy.io > pinggy.log 2>&1 &
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
            ssh -T -p 443 -R0:localhost:{{ port }} -o StrictHostKeyChecking=no tcp@a.pinggy.io > pinggy.log 2>&1 &
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

def convert_to_jinja(text, os_type):
    text = re.sub(r'\{([A-Za-z0-9_]+)\}', r'{{ \1 }}', text)
    if os_type == "windows":
        text = re.sub(r'ssh -T -p 443 -R0:localhost:\d+ -o StrictHostKeyChecking=no.*?\n\s*sleep 21600', tunnel_pinggy_windows, text, flags=re.DOTALL)
    elif os_type == "macos":
        text = re.sub(r'ssh -T -p 443 -R0:localhost:\d+ -o StrictHostKeyChecking=no.*?\n\s*sleep 21600', tunnel_pinggy_macos, text, flags=re.DOTALL)
    else:
        text = re.sub(r'ssh -T -p 443 -R0:localhost:\d+ -o StrictHostKeyChecking=no.*?\n\s*sleep 21600', tunnel_pinggy, text, flags=re.DOTALL)
        
    if "linux" in os_type:
        text = text.replace("{{ qemu_setup }}", "{% if architecture != 'amd64' %}\\n    - name: Set up QEMU for multi-arch support\\n      uses: docker/setup-qemu-action@v3{% endif %}")
        
    return text

for name, tpl in templates.items():
    os_type = "linux"
    if "WINDOWS" in name: os_type = "windows"
    if "MACOS" in name: os_type = "macos"
    
    filename = name.replace("_WORKFLOW_TEMPLATE", "").lower() + ".yml.j2"
    with open(f"rdp_Jinja2/templates/{filename}", "w") as f:
        f.write(convert_to_jinja(tpl, os_type))

print("Templates written to rdp_Jinja2/templates successfully.")
