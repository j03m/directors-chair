import sys
import questionary
from directors_chair.cli.utils import print_header, console
from directors_chair.cli.commands.system import system_check
from directors_chair.cli.commands.models import manage_models
from directors_chair.cli.commands.generation import generate_images

def main_menu():
    while True:
        print_header()
        
        choice = questionary.select(
            "Main Menu",
            choices=[
                "1. System Setup & Health Check",
                "2. Manage Models",
                "3. Generate Training Images",
                "4. Exit"
            ]
        ).ask()
        
        if not choice: # Handle cancellation (Ctrl+C)
            sys.exit(0)
            
        if "1." in choice:
            system_check()
        elif "2." in choice:
            manage_models()
        elif "3." in choice:
            generate_images()
        elif "4." in choice:
            console.print("Goodbye!")
            sys.exit(0)
