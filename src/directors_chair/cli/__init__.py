import sys
import questionary
from directors_chair.cli.utils import print_header, console
from directors_chair.cli.commands.system import system_check
from directors_chair.cli.commands.models import manage_models
from directors_chair.cli.commands.generation import generate_images
from directors_chair.cli.commands.training import train_lora_command
from directors_chair.cli.commands.storyboard import storyboard_to_video

def main_menu():
    while True:
        print_header()

        choice = questionary.select(
            "Main Menu",
            choices=[
                "1. System Setup & Health Check",
                "2. Manage Models",
                "3. Generate Training Images",
                "4. Train LoRA (Create Character)",
                "5. Storyboard to Video",
                "6. Exit"
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
            train_lora_command()
        elif "5." in choice:
            storyboard_to_video()
        elif "6." in choice:
            console.print("Goodbye!")
            sys.exit(0)
