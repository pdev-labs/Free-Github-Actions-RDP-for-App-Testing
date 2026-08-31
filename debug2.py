import re
with open("rdp.py", "r") as f:
    source = f.read()

source = source[:source.find("def start_p2p_server")]
match = re.search(f"LINUX_WORKFLOW_TEMPLATE\\s*=\\s*r?\"\"\"(.*?)\"\"\"", source, re.DOTALL)

val = match.group(1)

tunnel_pinggy = """{% if tunnel == 'pinggy' %}
        sleep 21600
{% endif %}"""

def convert_to_jinja(text, os_type):
    text = re.sub(r'\{([A-Za-z0-9_]+)\}', r'{{ \1 }}', text)
    text = re.sub(r'ssh -T -p 443 -R0:localhost:\d+ -o StrictHostKeyChecking=no.*?\n\s*sleep 21600', tunnel_pinggy, text, flags=re.DOTALL)
    if "linux" in os_type:
        text = text.replace("{{ qemu_setup }}", "{% if architecture != 'amd64' %}\\n    - name: Set up QEMU for multi-arch support\\n      uses: docker/setup-qemu-action@v3{% endif %}")
    return text

res = convert_to_jinja(val, "linux")
print("Result length:", len(res))
