#!/usr/bin/env python3
"""Directors Chair - AI Video Production CLI.

Usage:
    python scripts/chair.py                          # Interactive mode
    python scripts/chair.py storyboard --file <path> # Run storyboard autonomously
    python scripts/chair.py generate --theme <name>  # Generate character images
    python scripts/chair.py assemble --clips a,b,c --name movie  # Assemble movie
"""
import argparse
from dotenv import load_dotenv
load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="Directors Chair - AI Video Production"
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- storyboard subcommand ---
    sb = subparsers.add_parser("storyboard", help="Run storyboard pipeline (autonomous)")
    sb.add_argument("--file", required=True, help="Path to storyboard JSON file")
    sb.add_argument("--keyframes-only", action="store_true", help="Stop after keyframe generation (skip video)")

    # --- generate subcommand ---
    gen = subparsers.add_parser("generate", help="Generate character images (autonomous)")
    gen.add_argument("--theme", required=True, help="Theme name from config.json")
    gen.add_argument("--count", type=int, help="Override number of images")

    # --- assemble subcommand ---
    asm = subparsers.add_parser("assemble", help="Assemble movie from storyboard videos")
    asm.add_argument(
        "--clips", required=True,
        help="Comma-separated storyboard names in order (e.g. desert_run,desert_run_zombie)"
    )
    asm.add_argument("--name", required=True, help="Output movie name")

    args = parser.parse_args()

    if args.command is None:
        # Interactive mode — existing behavior
        from directors_chair.cli import main_menu
        main_menu()

    elif args.command == "storyboard":
        from directors_chair.cli.commands.storyboard import storyboard_to_video
        storyboard_to_video(storyboard_file=args.file, auto_mode=True, keyframes_only=getattr(args, 'keyframes_only', False))

    elif args.command == "generate":
        from directors_chair.cli.commands.generation import generate_images
        generate_images(
            theme_name=args.theme,
            auto_mode=True,
            count_override=args.count,
        )

    elif args.command == "assemble":
        from directors_chair.cli.commands.assemble import assemble_movie
        clip_names = [c.strip() for c in args.clips.split(",")]
        assemble_movie(
            clip_names=clip_names,
            movie_name=args.name,
            auto_mode=True,
        )


if __name__ == "__main__":
    main()
