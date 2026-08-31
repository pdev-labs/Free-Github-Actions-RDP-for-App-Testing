import asyncio

async def async_poll_logs(base_dir, repo_name, gh_user, password, console):
    try:
        with console.status("[bold cyan]Fetching logs from GitHub Actions (waiting for runner to boot)...[/bold cyan]") as status:
            run_id = None
            for _ in range(15):
                proc = await asyncio.create_subprocess_exec(
                    "gh", "run", "list", "-w", "rdp.yml", "-L", "1", "--json", "databaseId", "-q", ".[0].databaseId",
                    cwd=base_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                out = stdout.decode().strip()
                if out and out != "null":
                    run_id = out
                    break
                await asyncio.sleep(4)
            
            if run_id:
                url_found = False
                for _ in range(40): # 40 * 5 = 200 seconds
                    proc = await asyncio.create_subprocess_exec(
                        "gh", "run", "view", run_id, "--log",
                        cwd=base_dir,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await proc.communicate()
                    logs = stdout.decode()
                    if "Connect using" in logs:
                        url_found = True
                        address = ""
                        user = ""
                        for line in logs.split('\n'):
                            if "Connect using" in line:
                                address = line.strip()
                            elif "Username:" in line:
                                user = line.split("Username:")[1].strip()
                        
                        console.print("\n[bold green]🎉 Your Cloud Desktop is Ready![/bold green]")
                        console.print(f"[bold cyan]URL/Command:[/bold cyan] [bold white]{address}[/bold white]")
                        if user:
                            console.print(f"[bold cyan]Username:[/bold cyan] [bold white]{user}[/bold white]")
                        console.print(f"[bold cyan]Password:[/bold cyan] [bold white]{password}[/bold white]")
                        break
                    await asyncio.sleep(5)
                    
                if not url_found:
                    console.print("[bold red]Timeout waiting for tunnel details in logs. Please check the GitHub Actions UI manually.[/bold red]")
                    console.print(f"Workflow URL: https://github.com/{gh_user}/{repo_name}/actions/workflows/rdp.yml")
            else:
                console.print("[bold red]Could not find active Workflow Run ID. Please check the GitHub Actions UI manually.[/bold red]")
                console.print(f"Workflow URL: https://github.com/{gh_user}/{repo_name}/actions/workflows/rdp.yml")
    except Exception as e:
        console.print(f"[dim]Could not automatically fetch logs: {e}[/dim]")
