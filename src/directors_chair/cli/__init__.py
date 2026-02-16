import sys
import questionary
from directors_chair.cli.utils import print_header, console
from directors_chair.cli.commands.generation import generate_images
from directors_chair.cli.commands.storyboard import storyboard_to_video

def main_menu():
    while True:
        print_header()

        choice = questionary.select(
            "Main Menu",
            choices=[
                "1. Generate Character",
                "2. Storyboard to Video",
                "3. Exit"
            ]
        ).ask()

        if not choice:
            sys.exit(0)

        if "1." in choice:
            generate_images()
        elif "2." in choice:
            storyboard_to_video()
        elif "3." in choice:
            console.print("Goodbye!")
            sys.exit(0)
