import re

with open('rdp.py', 'r') as f:
    content = f.read()

# Add a print statement to show the password to the user locally
print_old = '    console.print(f"\\n[bold cyan]Workflow URL:[/bold cyan] [bold underline blue]https://github.com/{gh_user}/{repo_name}/actions/workflows/rdp.yml[/bold underline blue]\\n")'
print_new = print_old + '\n    console.print(f"\\n[bold green]Generated Password:[/bold green] [bold white]{password}[/bold white]\\n")'

content = content.replace(print_old, print_new)

with open('rdp.py', 'w') as f:
    f.write(content)

