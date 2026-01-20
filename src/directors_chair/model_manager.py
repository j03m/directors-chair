import os
from huggingface_hub import snapshot_download
from huggingface_hub.utils import RepositoryNotFoundError, GatedRepoError, LocalEntryNotFoundError
from rich.console import Console

console = Console()

def download_model(repo_id: str, local_dir: str):
    """
    Downloads a model from Hugging Face Hub to a local directory.
    """
    console.print(f"[bold cyan]Downloading {repo_id} to {local_dir}...[/bold cyan]")
    
    try:
        snapshot_download(
            repo_id=repo_id,
            local_dir=local_dir,
            local_dir_use_symlinks=False, # Copy files so it's self-contained
            resume_download=True
        )
        console.print(f"[bold green]✓ Successfully downloaded {repo_id}[/bold green]")
        return True
    except (GatedRepoError, RepositoryNotFoundError) as e:
        console.print(f"\n[bold red]✗ Access Denied or Repo Not Found ({repo_id})[/bold red]")
        console.print("[yellow]Possible reasons:[/yellow]")
        console.print("1. You are not logged in. Run: [bold]huggingface-cli login[/bold]")
        console.print("2. The model is GATED (e.g. Flux Dev). You must accept the license at the repo URL.")
        console.print("3. The Repo ID is incorrect.")
        console.print(f"\nError details: {e}")
        return False
    except Exception as e:
        if "401" in str(e):
             console.print(f"\n[bold red]✗ Authentication Failed (401)[/bold red]")
             console.print("[yellow]Please run: [bold]huggingface-cli login[/bold] and paste a valid token.[/yellow]")
             console.print("Make sure you have access to the model if it is Gated.")
        else:
            console.print(f"[bold red]✗ Download failed: {e}[/bold red]")
        return False
