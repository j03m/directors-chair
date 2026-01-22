import sys
from directors_chair.cli.utils import console
from directors_chair.cli import main_menu

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[red]Exiting...[/red]")
        sys.exit(0)

