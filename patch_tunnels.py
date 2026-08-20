import re
import sys

with open("rdp.py", "r") as f:
    code = f.read()

# Make sure we only inject once
if "inject_tunnel_logic" in code:
    sys.exit(0)

tunnel_replacer = """
import re

def inject_tunnel_logic(template, tunnel, ngrok_token, port):
    if tunnel == "pinggy":
        return template
        
    if tunnel == "ngrok":
        ngrok_cmd = f\"\"\"wget -q https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
        tar -xf ngrok-v3-stable-linux-amd64.tgz
        ./ngrok authtoken {ngrok_token}
        ./ngrok tcp {port} --log=stdout > pinggy.log 2>&1 &\"\"\"
        
        template = re.sub(r"ssh -T -p 443 -R0:localhost:[0-9]+ -o StrictHostKeyChecking=no.*&", ngrok_cmd, template)
        
        # We must use proper single quotes for raw string to avoid syntax error on backslashes
        template = re.sub(r'URL=\\$\\(grep -o "tcp://\\.\\*" .* \\| head -n 1\\)', "URL=$(curl -s localhost:4040/api/tunnels | grep -o '\\"public_url\\":\\"tcp://[^\\"]*' | grep -o 'tcp://.*' | head -n 1)", template)
        
        template = template.replace("Pinggy free tier is limited to 60 minutes", "Ngrok tunnel will persist for up to 6 hours")
        template = template.replace("Pinggy tunnel", "Ngrok tunnel")
        return template
"""

# Replace generate_workflow definition
code = code.replace("def generate_workflow", tunnel_replacer + "\ndef generate_workflow")

# Replace return calls in generate_workflow
code = code.replace(
    "return WINDOWS_CLI_WORKFLOW_TEMPLATE.replace(\"{runner_image}\", version_choice)",
    "return inject_tunnel_logic(WINDOWS_CLI_WORKFLOW_TEMPLATE.replace(\"{runner_image}\", version_choice), tunnel, ngrok_token, 22)"
)
code = code.replace(
    "return WINDOWS_WORKFLOW_TEMPLATE.replace(\"{runner_image}\", version_choice)",
    "return inject_tunnel_logic(WINDOWS_WORKFLOW_TEMPLATE.replace(\"{runner_image}\", version_choice), tunnel, ngrok_token, 3389)"
)
code = code.replace(
    "return LINUX_WORKFLOW_TEMPLATE.replace(\"{distro}\", version_choice).replace(\"{architecture}\", architecture).replace(\"{qemu_setup}\", qemu).replace(\"{de_choice}\", de_choice).replace(\"{app_choice_str}\", app_choice_str)",
    "port = 22 if de_choice == 'cli' else 3389\n        return inject_tunnel_logic(LINUX_WORKFLOW_TEMPLATE.replace(\"{distro}\", version_choice).replace(\"{architecture}\", architecture).replace(\"{qemu_setup}\", qemu).replace(\"{de_choice}\", de_choice).replace(\"{app_choice_str}\", app_choice_str), tunnel, ngrok_token, port)"
)
code = code.replace(
    "return MACOS_CLI_WORKFLOW_TEMPLATE.replace(\"{runner_image}\", version_choice).replace(\"{pub_key}\", pub_key)",
    "return inject_tunnel_logic(MACOS_CLI_WORKFLOW_TEMPLATE.replace(\"{runner_image}\", version_choice).replace(\"{pub_key}\", pub_key), tunnel, ngrok_token, 22)"
)
code = code.replace(
    "return MACOS_WORKFLOW_TEMPLATE.replace(\"{runner_image}\", version_choice)",
    "return inject_tunnel_logic(MACOS_WORKFLOW_TEMPLATE.replace(\"{runner_image}\", version_choice), tunnel, ngrok_token, 5900)"
)
code = code.replace(
    "return CUSTOM_ISO_WORKFLOW_TEMPLATE.replace(\"{download_logic}\", custom_download_logic)",
    "return inject_tunnel_logic(CUSTOM_ISO_WORKFLOW_TEMPLATE.replace(\"{download_logic}\", custom_download_logic), tunnel, ngrok_token, 5900)"
)

with open("rdp.py", "w") as f:
    f.write(code)
print("Patch success")
