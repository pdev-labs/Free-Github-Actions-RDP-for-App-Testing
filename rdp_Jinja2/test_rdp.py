import sys
import os
from engine import generate_workflow

def check_workflow(name, os_choice, version, architecture="amd64", de="xfce", tunnel="pinggy", apps=""):
    try:
        yaml = generate_workflow("testpass", False, os_choice, version, architecture, de, apps, "", "testpubkey", tunnel, "")
        
        if os_choice not in ["custom_iso", "android", "macos"] and de != "cli":
            if "testpass" not in yaml:
                print(f"FAIL: {name} - Password not injected")
                return False
                
        if tunnel == "pinggy" and "a.pinggy.io" not in yaml:
            print(f"FAIL: {name} - Pinggy not injected")
            return False
        if tunnel == "cloudflare" and "cloudflared" not in yaml:
            print(f"FAIL: {name} - Cloudflare not injected")
            return False
        
        # Test specific rules
        if os_choice == "linux" and de == "xfce" and "xfce" not in yaml.lower():
            print(f"FAIL: {name} - XFCE not found in Linux workflow")
            return False
            
        print(f"PASS: {name} (Length: {len(yaml)})")
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
    print("ALL TESTS PASSED SUCCESSFULLY!")
else:
    sys.exit(1)
