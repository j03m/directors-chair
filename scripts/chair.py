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
    sb.add_argument("--regen-keyframes", type=str, help="Comma-separated shot names, 'all' to regen everything, or 'missing' to only generate missing keyframes. e.g. 'hockey_threat,greasy_cigarette'")
    sb.add_argument("--edit-keyframes", type=str, help="Comma-separated shot names to run ONLY the edit pass on existing keyframes. e.g. 'hockey_threat,hockey_face'")

    # --- generate subcommand ---
    gen = subparsers.add_parser("generate", help="Generate character images (autonomous)")
    gen.add_argument("--theme", required=True, help="Theme name from config.json")
    gen.add_argument("--count", type=int, help="Override number of images")

    # --- edit-clip subcommand ---
    ec = subparsers.add_parser("edit-clip", help="Edit an existing video clip (v2v)")
    ec.add_argument("--file", required=True, help="Path to storyboard JSON file")
    ec.add_argument("--clip", required=True, type=str, help="Shot name of clip to edit")
    ec.add_argument("--prompt", required=True, help="Edit prompt describing desired changes")
    ec.add_argument("--save-as-new", action="store_true", help="Save as new file instead of overwriting")

    # --- edit-keyframe subcommand ---
    ek = subparsers.add_parser("edit-keyframe", help="Edit an existing keyframe image")
    ek.add_argument("--file", required=True, help="Path to storyboard JSON file")
    ek.add_argument("--keyframe", required=True, type=str, help="Shot name of keyframe to edit")
    ek.add_argument("--prompt", required=True, help="Edit prompt describing desired changes")

    # --- regen-clip subcommand ---
    rc = subparsers.add_parser("regen-clip", help="Regenerate a single video clip")
    rc.add_argument("--file", required=True, help="Path to storyboard JSON file")
    rc.add_argument("--clip", required=True, type=str, help="Shot name of clip to regenerate")

    # --- assemble subcommand ---
    asm = subparsers.add_parser("assemble", help="Assemble movie from storyboard videos")
    asm.add_argument(
        "--clips", required=True,
        help="Comma-separated storyboard names in order (e.g. desert_run,desert_run_zombie)"
    )
    asm.add_argument("--name", required=True, help="Output movie name")

    # --- voice subcommand ---
    vp = subparsers.add_parser("voice", help="Voice design and management")
    voice_sub = vp.add_subparsers(dest="voice_command")

    vd = voice_sub.add_parser("design", help="Design a voice from description")
    vd.add_argument("--name", required=True, help="Character name")
    vd.add_argument("--description", required=True, help="Voice description prompt")
    vd.add_argument("--text", help="Sample text for preview")

    vc = voice_sub.add_parser("clone", help="Clone voice from audio files")
    vc.add_argument("--name", required=True, help="Character name")
    vc.add_argument("--description", required=True, help="Voice description")
    vc.add_argument("--files", required=True, help="Comma-separated audio file paths")
    vc.add_argument("--remove-noise", action="store_true", help="Remove background noise")

    vr = voice_sub.add_parser("remix", help="Remix an existing voice")
    vr.add_argument("--name", required=True, help="Existing voice character name")
    vr.add_argument("--description", required=True, help="Modification description")
    vr.add_argument("--new-name", help="Name for remixed voice")

    voice_sub.add_parser("list", help="List configured voices")

    vt = voice_sub.add_parser("test", help="Generate test speech")
    vt.add_argument("--name", required=True, help="Voice character name")
    vt.add_argument("--text", default="The wasteland stretches on forever. We ride at dawn.", help="Text to speak")

    args = parser.parse_args()

    if args.command is None:
        # Interactive mode — existing behavior
        from directors_chair.cli import main_menu
        main_menu()

    elif args.command == "storyboard":
        from directors_chair.cli.commands.storyboard import storyboard_to_video
        regen_kf = None
        if getattr(args, 'regen_keyframes', None):
            val = args.regen_keyframes.strip()
            if val == "all":
                regen_kf = "all"
            elif val == "missing":
                regen_kf = "missing"
            else:
                regen_kf = [x.strip() for x in val.split(",")]
        edit_kf = None
        if getattr(args, 'edit_keyframes', None):
            edit_kf = [x.strip() for x in args.edit_keyframes.split(",")]
        storyboard_to_video(
            storyboard_file=args.file,
            auto_mode=True,
            keyframes_only=getattr(args, 'keyframes_only', False) or bool(regen_kf) or bool(edit_kf),
            regen_keyframes=regen_kf,
            edit_keyframes=edit_kf,
        )

    elif args.command == "generate":
        from directors_chair.cli.commands.generation import generate_images
        generate_images(
            theme_name=args.theme,
            auto_mode=True,
            count_override=args.count,
        )

    elif args.command == "edit-clip":
        from directors_chair.cli.commands.clip_tools import edit_clip_command
        edit_clip_command(
            storyboard_file=args.file,
            clip_name=args.clip,
            edit_prompt=args.prompt,
            auto_mode=True,
            save_as_new=getattr(args, 'save_as_new', False),
        )

    elif args.command == "edit-keyframe":
        from directors_chair.cli.commands.clip_tools import edit_keyframe_command
        edit_keyframe_command(
            storyboard_file=args.file,
            keyframe_name=args.keyframe,
            edit_prompt=args.prompt,
            auto_mode=True,
        )

    elif args.command == "regen-clip":
        from directors_chair.cli.commands.clip_tools import regen_clip_command
        regen_clip_command(
            storyboard_file=args.file,
            clip_name=args.clip,
            auto_mode=True,
        )

    elif args.command == "assemble":
        from directors_chair.cli.commands.assemble import assemble_movie
        clip_names = [c.strip() for c in args.clips.split(",")]
        assemble_movie(
            clip_names=clip_names,
            movie_name=args.name,
            auto_mode=True,
        )

    elif args.command == "voice":
        if not hasattr(args, 'voice_command') or args.voice_command is None:
            from directors_chair.cli.commands.voice import voice_menu
            voice_menu()
        elif args.voice_command == "design":
            from directors_chair.cli.commands.voice import design_voice_command
            design_voice_command(
                char_name=args.name,
                description=args.description,
                sample_text=getattr(args, 'text', None),
                auto_mode=True,
            )
        elif args.voice_command == "clone":
            from directors_chair.cli.commands.voice import clone_voice_command
            clone_voice_command(
                char_name=args.name,
                description=args.description,
                files_str=args.files,
                remove_noise=getattr(args, 'remove_noise', False),
                auto_mode=True,
            )
        elif args.voice_command == "remix":
            from directors_chair.cli.commands.voice import remix_voice_command
            remix_voice_command(
                char_name=args.name,
                description=args.description,
                new_name=getattr(args, 'new_name', None),
                auto_mode=True,
            )
        elif args.voice_command == "list":
            from directors_chair.cli.commands.voice import list_voices_command
            list_voices_command()
        elif args.voice_command == "test":
            from directors_chair.cli.commands.voice import test_voice_command
            test_voice_command(
                char_name=args.name,
                text=args.text,
                auto_mode=True,
            )


if __name__ == "__main__":
    main()
