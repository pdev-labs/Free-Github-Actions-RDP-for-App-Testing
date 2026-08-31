import re
with open("rdp.py", "r") as f:
    source = f.read()

source = source[:source.find("def start_p2p_server")]
match = re.search(f"LINUX_WORKFLOW_TEMPLATE\\s*=\\s*r?\"\"\"(.*?)\"\"\"", source, re.DOTALL)

if match:
    val = match.group(1)
    print("Match length:", len(val))
    print("First 20 chars:", val[:20])
else:
    print("No match")
