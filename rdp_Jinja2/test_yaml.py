import sys
import os
import yaml
from engine import generate_workflow

def check_workflow(name, os_choice, version, architecture="amd64", de="xfce", tunnel="pinggy", apps=""):
    try:
        yaml_content = generate_workflow("testpass", False, os_choice, version, architecture, de, apps, "", "testpubkey", tunnel, "")
        
        try:
            yaml.safe_load(yaml_content)
        except yaml.YAMLError as exc:
            print(f"FAIL YAML PARSE: {name}\n{exc}")
            return False
            
        print(f"PASS YAML: {name}")
        return True
    except Exception as e:
        print(f"FAIL: {name} - Exception: {e}")
        return False

tests = [
    ("Linux Ubuntu XFCE Pinggy", "linux", "ubuntu:latest", "amd64", "xfce", "pinggy", "0"),
    ("Linux Debian CLI Ngrok", "linux", "debian:latest", "amd64", "cli", "ngrok", ""),
    ("Linux Arch KDE Cloudflare", "linux", "archlinux:latest", "amd64", "kde", "cloudflare", "1,2"),
    ("Windows RDP Tailscale", "windows", "windows-latest", "amd64", "gui", "tailscale", ""),
    ("Windows CLI Pinggy", "windows", "windows-latest", "amd64", "cli", "pinggy", ""),
    ("macOS VNC Ngrok", "macos", "macos-13", "amd64", "gui", "ngrok", ""),
    ("macOS CLI Cloudflare", "macos", "macos-latest", "amd64", "cli", "cloudflare", ""),
    ("Custom ISO Ubuntu Pinggy", "custom_iso", "custom", "amd64", "gui", "pinggy", ""),
    ("Android x86 Tailscale", "android", "custom", "amd64", "gui", "tailscale", "")
]

success = True
for t in tests:
    res = check_workflow(*t)
    if not res: success = False

if success:
    print("ALL YAML SYNTAX TESTS PASSED SUCCESSFULLY!")
else:
    sys.exit(1)
