from rdp import generate_workflow
y = generate_workflow('linux', 'ubuntu:latest', 'amd64', 'xfce', '1', '0', '', 'pinggy', '')
y2 = y.replace('echo "==========================================================="', 'if [ ! -z "$URL" ]; then\n            if [ ! -z "$GITHUB_STEP_SUMMARY" ]; then\n                echo "### 🚀 Connection URL: $URL" >> $GITHUB_STEP_SUMMARY\n            fi\n            echo "==========================================================="', 1)
print(y2.split('echo "==========================================================="')[0][-200:])
