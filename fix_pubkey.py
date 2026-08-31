import re

with open('rdp.py', 'r') as f:
    content = f.read()

# Add pub_key injection to Linux setup.sh
linux_pubkey_injection = r"""
        mkdir -p ~/.ssh
        echo "{pub_key}" >> ~/.ssh/authorized_keys
        chmod 700 ~/.ssh
        chmod 600 ~/.ssh/authorized_keys
"""
content = content.replace("useradd -m -G sudo -s /bin/bash $USER || true", "useradd -m -G sudo -s /bin/bash $USER || true" + linux_pubkey_injection)

# Add it to the generate_workflow call for linux
content = content.replace('template = LINUX_WORKFLOW_TEMPLATE_P.replace("{runner_image}", runner_image)', 'template = LINUX_WORKFLOW_TEMPLATE_P.replace("{runner_image}", runner_image).replace("{pub_key}", pub_key)')


with open('rdp.py', 'w') as f:
    f.write(content)
