#!/usr/bin/env python3
from dotenv import load_dotenv
load_dotenv()

from directors_chair.cli import main_menu


if __name__ == "__main__":
    main_menu()
