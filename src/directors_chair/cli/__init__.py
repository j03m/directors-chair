import sys
import questionary
from directors_chair.cli.utils import print_header, console
from directors_chair.cli.commands.system import system_check
from directors_chair.cli.commands.models import manage_models
from directors_chair.cli.commands.generation import generate_images
from directors_chair.cli.commands.variations import generate_variations
from directors_chair.cli.commands.training_poses import generate_training_poses
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
                "3. Generate Hero Image",
                "4. Vary Hero Image (fal.ai img2img)",
                "5. Generate Training Poses (fal.ai)",
                "6. Train LoRA",
                "7. Storyboard to Video",
                "8. Exit"
            ]
        ).ask()

        if not choice:
            sys.exit(0)

        if "1." in choice:
            system_check()
        elif "2." in choice:
            manage_models()
        elif "3." in choice:
            generate_images()
        elif "4." in choice:
            generate_variations()
        elif "5." in choice:
            generate_training_poses()
        elif "6." in choice:
            train_lora_command()
        elif "7." in choice:
            storyboard_to_video()
        elif "8." in choice:
            console.print("Goodbye!")
            sys.exit(0)
