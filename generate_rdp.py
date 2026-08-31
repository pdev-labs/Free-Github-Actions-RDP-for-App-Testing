import re

with open("rdp_Jinja2/rdp.py", "r") as f:
    source = f.read()

source = re.sub(r'def inject_tunnel_logic.*?return template', "", source, flags=re.DOTALL)

new_generate = """import jinja2
import os

def generate_workflow(password, enable_cache, os_choice, version_choice, architecture="amd64", de_choice="xfce", app_choice_str="", custom_download_logic="", pub_key="", tunnel="pinggy", ngrok_token=""):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))
    
    context = {
        "password": password,
        "enable_cache": enable_cache,
        "os_choice": os_choice,
        "runner_image": version_choice,
        "distro": version_choice,
        "architecture": architecture,
        "de_choice": de_choice,
        "app_choice_str": app_choice_str,
        "download_logic": custom_download_logic.replace("\\n", "\\n        ").replace("\\\\n", "\\\\n        "),
        "pub_key": pub_key,
        "tunnel": tunnel,
        "ngrok_token": ngrok_token,
        "port": 3389
    }

    if os_choice == "windows":
        if de_choice == "cli":
            context["port"] = 22
            template = env.get_template('windows_cli.yml.j2')
        else:
            template = env.get_template('windows.yml.j2')
    elif os_choice == "linux":
        context["port"] = 22 if de_choice == "cli" else 3389
        context["execution_logic"] = 'echo "Booting {{ distro }} container on {{ architecture }}..."\\n        docker run --rm --privileged --platform linux/{{ architecture }} -v $(pwd)/setup.sh:/setup.sh {{ distro }} /setup.sh'
        if version_choice.startswith("ubuntu:"):
            context["runner_image"] = version_choice.replace(":", "-")
            context["execution_logic"] = 'echo "Running setup directly on GitHub Actions Ubuntu Runner..."\\n        sudo bash setup.sh'
        template = env.get_template('linux.yml.j2')
    elif os_choice == "macos":
        if de_choice == "cli":
            context["port"] = 22
            template = env.get_template('macos_cli.yml.j2')
        else:
            context["port"] = 5900
            template = env.get_template('macos.yml.j2')
    elif os_choice in ["custom_iso", "android"]:
        context["port"] = 5900
        template = env.get_template('custom_iso.yml.j2')
    else:
        raise ValueError(f"Unknown OS choice: {os_choice}")
        
    return template.render(context)
"""

source = re.sub(r'def generate_workflow\(.*?\n\s+raise ValueError.*?os_choice\"\)', new_generate, source, flags=re.DOTALL)
source = re.sub(r'\n{3,}', '\n\n', source)

with open("rdp_Jinja2/rdp.py", "w") as f:
    f.write(source)

