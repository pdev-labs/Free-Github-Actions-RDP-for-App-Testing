import re

with open('rdp.py', 'r') as f:
    text = f.read()

# Replace the blocking logic with the async call
text = re.sub(
    r'    try:\n        with console\.status\("\[bold cyan\]Fetching logs from GitHub Actions.*?except Exception as e:\n        console\.print\(f"\[dim\]Could not automatically fetch logs: \{e\}\[\\/dim\]"\)',
    '    import asyncio\n    from poll_async import async_poll_logs\n    asyncio.run(async_poll_logs(base_dir, repo_name, gh_user, password, console))',
    text,
    flags=re.DOTALL
)

with open('rdp.py', 'w') as f:
    f.write(text)

print("Async logic injected.")
