import re

with open('rdp.py', 'r') as f:
    content = f.read()

# 1. SSH Key Auto Generation
# Currently it hardcodes it for macos cli at line 1173 (approx):
#     pub_key = ""
#     if os_choice == "macos" and de_choice == "cli":
#         if not os.path.exists("macos_runner_key"): ...

old_ssh_logic = """    pub_key = ""
    if os_choice == "macos" and de_choice == "cli":
        if not os.path.exists("macos_runner_key"):
            print("\\nGenerating SSH key pair for macOS CLI access...")
            subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", "macos_runner_key", "-N", "", "-q"], check=True)
        with open("macos_runner_key.pub", "r") as f:
            pub_key = f.read().strip()"""

new_ssh_logic = """    pub_key = ""
    if os_choice in ["macos", "linux", "windows"] and de_choice == "cli":
        gen_ssh = inquirer.confirm(message="Would you like to auto-generate an SSH key for connection?").execute()
        if gen_ssh:
            key_name = f"{os_choice}_runner_key"
            if not os.path.exists(key_name):
                print(f"\\nGenerating SSH key pair for {os_choice} CLI access...")
                import subprocess
                subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", key_name, "-N", "", "-q"], check=True)
            with open(f"{key_name}.pub", "r") as f:
                pub_key = f.read().strip()
            print(f"[!] You can connect using: ssh -i {key_name} ...")
        else:
            pub_key = inquirer.text(message="Enter your public SSH key:").execute().strip()
"""
if old_ssh_logic in content:
    content = content.replace(old_ssh_logic, new_ssh_logic)
else:
    print("WARNING: Old SSH logic not found exactly.")


# 2. Caching
# We need to add an enable_cache prompt somewhere around the end of the prompts, maybe near tunnel.
cache_prompt = """    enable_cache = inquirer.confirm(message="Enable GitHub Actions caching for faster boots (caches apt/brew packages)?").execute()
    
    if not loaded_profile:
        tunnel = inquirer.select("""

content = content.replace("    if not loaded_profile:\n        tunnel = inquirer.select(", cache_prompt)

# Modify generate_workflow signature to accept enable_cache
content = content.replace("def generate_workflow(password, os_choice, version_choice, architecture=\"amd64\", de_choice=\"xfce\", app_choice_str=\"\", custom_download_logic=\"\", pub_key=\"\", tunnel=\"pinggy\", ngrok_token=\"\"):",
                          "def generate_workflow(password, enable_cache, os_choice, version_choice, architecture=\"amd64\", de_choice=\"xfce\", app_choice_str=\"\", custom_download_logic=\"\", pub_key=\"\", tunnel=\"pinggy\", ngrok_token=\"\"):")

content = content.replace("workflow_yml = generate_workflow(password, os_choice", "workflow_yml = generate_workflow(password, enable_cache, os_choice")

# Inject cache logic in generate_workflow
linux_cache = r"""\n    - name: Enable APT Cache\n      if: runner.os == 'Linux'\n      uses: actions/cache@v3\n      with:\n        path: /var/cache/apt/archives\n        key: apt-${{ runner.os }}\n"""
macos_cache = r"""\n    - name: Enable Homebrew Cache\n      if: runner.os == 'macOS'\n      uses: actions/cache@v3\n      with:\n        path: ~/Library/Caches/Homebrew\n        key: brew-${{ runner.os }}\n"""

cache_injection = f"""
    cache_step = ""
    if enable_cache:
        if os_choice == 'linux':
            cache_step = '{linux_cache}'
        elif os_choice == 'macos':
            cache_step = '{macos_cache}'
            
    LINUX_WORKFLOW_TEMPLATE_P = LINUX_WORKFLOW_TEMPLATE_P.replace("steps:{{qemu_setup}}", "steps:{{qemu_setup}}" + cache_step)
    MACOS_WORKFLOW_TEMPLATE_P = MACOS_WORKFLOW_TEMPLATE_P.replace("steps:", "steps:" + cache_step)
    MACOS_CLI_WORKFLOW_TEMPLATE_P = MACOS_CLI_WORKFLOW_TEMPLATE_P.replace("steps:", "steps:" + cache_step)
"""
content = content.replace("    if os_choice == \"windows\":\n        if de_choice == \"cli\":", cache_injection + "    if os_choice == \"windows\":\n        if de_choice == \"cli\":")


with open('rdp.py', 'w') as f:
    f.write(content)

