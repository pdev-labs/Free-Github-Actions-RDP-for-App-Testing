import rdp

print("=== WINDOWS ===")
out = rdp.generate_workflow('windows', 'windows-latest', de_choice='gui', tunnel='pinggy')
import re
match = re.search(r'sleep 3300.*?kill \$SSH_PID', out, re.DOTALL)
if match:
    print(match.group(0))

print("\n=== MACOS ===")
out = rdp.generate_workflow('macos', 'macos-latest', de_choice='gui', tunnel='pinggy')
match = re.search(r'sleep 3300.*?kill \$SSH_PID', out, re.DOTALL)
if match:
    print(match.group(0))

print("\n=== LINUX ===")
out = rdp.generate_workflow('linux', 'ubuntu:latest', de_choice='gui', tunnel='pinggy')
match = re.search(r'sleep 3300.*?kill \$SSH_PID', out, re.DOTALL)
if match:
    print(match.group(0))
