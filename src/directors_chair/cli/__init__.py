import sys
import questionary
from directors_chair.cli.utils import print_header, console
from directors_chair.cli.commands.generation import generate_images
from directors_chair.cli.commands.storyboard import storyboard_to_video
from directors_chair.cli.commands.clip_tools import clip_tools_menu
from directors_chair.cli.commands.assemble import assemble_movie
from directors_chair.cli.commands.voice import voice_menu

def main_menu():
    while True:
        print_header()

        choice = questionary.select(
            "Main Menu",
            choices=[
                "1. Generate Character",
                "2. Storyboard to Video",
                "3. Clip & Keyframe Tools",
                "4. Assemble Movie",
                "5. Voice Design",
                "6. Exit"
            ]
        ).ask()

        if not choice:
            sys.exit(0)

        if "1." in choice:
            generate_images()
        elif "2." in choice:
            storyboard_to_video()
        elif "3." in choice:
            clip_tools_menu()
        elif "4." in choice:
            assemble_movie()
        elif "5." in choice:
            voice_menu()
        elif "6." in choice:
            console.print("Goodbye!")
            sys.exit(0)
