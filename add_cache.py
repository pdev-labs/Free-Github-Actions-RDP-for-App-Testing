import os
import re

tpl_dir = "rdp_Jinja2/templates/"
cache_linux = """{% if enable_cache %}
    - name: Cache apt packages
      uses: actions/cache@v4
      with:
        path: /var/cache/apt
        key: apt-cache-{{ runner_image }}
{% endif %}"""

cache_macos = """{% if enable_cache %}
    - name: Cache Homebrew packages
      uses: actions/cache@v4
      with:
        path: ~/Library/Caches/Homebrew
        key: brew-cache-{{ runner_image }}
{% endif %}"""

cache_windows = """{% if enable_cache %}
    - name: Cache Chocolatey packages
      uses: actions/cache@v4
      with:
        path: C:\\ProgramData\\chocolatey\\cache
        key: choco-cache-{{ runner_image }}
{% endif %}"""

for file in os.listdir(tpl_dir):
    with open(os.path.join(tpl_dir, file), "r") as f:
        text = f.read()

    # Skip if already cached
    if "uses: actions/cache@v4" in text:
        continue

    cache_block = ""
    if "linux" in file or "custom_iso" in file or "android" in file:
        cache_block = cache_linux
    elif "macos" in file:
        cache_block = cache_macos
    elif "windows" in file:
        cache_block = cache_windows
        
    if cache_block:
        # We find the line containing `steps:` or `steps:{% if architecture != 'amd64' %}`
        # Wait, linux.yml.j2 has `steps:{% if architecture ...`
        if "steps:{%" in text:
            text = text.replace("steps:{% if architecture != 'amd64' %}\\n    - name: Set up QEMU for multi-arch support\\n      uses: docker/setup-qemu-action@v3{% endif %}", "steps:\n" + cache_block + "\n{% if architecture != 'amd64' %}\n    - name: Set up QEMU for multi-arch support\n      uses: docker/setup-qemu-action@v3\n{% endif %}")
        else:
            text = text.replace("    steps:\n", "    steps:\n" + cache_block + "\n")
            
        with open(os.path.join(tpl_dir, file), "w") as f:
            f.write(text)

print("Cache logic injected.")
