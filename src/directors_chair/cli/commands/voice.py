"""Voice Design & Management — design, clone, remix, list, test voices."""

import os
import questionary
from rich.table import Table
from rich.panel import Panel
from directors_chair.config.loader import load_config, save_config
from directors_chair.cli.utils import console


def design_voice_command(char_name=None, description=None, sample_text=None, auto_mode=False):
    """Design a new voice from a text description."""
    from directors_chair.voice import design_voice, save_voice
    from directors_chair.voice.elevenlabs_engine import play_audio

    config = load_config()

    if not char_name:
        char_name = questionary.text("Character name (e.g. 'gorilla'):").ask()
        if not char_name:
            return

    if not description:
        description = questionary.text(
            "Voice description (describe the voice characteristics):"
        ).ask()
        if not description:
            return

    if not sample_text and not auto_mode:
        sample_text = questionary.text(
            "Sample text for preview (Enter for auto-generate):",
            default=""
        ).ask()

    output_dir = os.path.join("assets", "voices", char_name)

    while True:
        previews = design_voice(
            description=description,
            text=sample_text if sample_text else None,
            output_dir=output_dir,
        )

        if not previews:
            console.print("[red]No previews generated.[/red]")
            return

        if auto_mode:
            # Auto mode: pick first preview
            generated_voice_id, preview_path = previews[0]
        else:
            # Play previews
            console.print(f"\n[bold]Listen to {len(previews)} preview(s):[/bold]")
            for i, (vid, path) in enumerate(previews):
                console.print(f"\n  [cyan]Preview {i + 1}:[/cyan] {path}")
                do_play = questionary.confirm(f"Play preview {i + 1}?", default=True).ask()
                if do_play:
                    play_audio(path)

            choices = [f"Preview {i + 1}" for i in range(len(previews))]
            choices += ["Retry with different description", "Cancel"]

            pick = questionary.select("Select voice:", choices=choices).ask()

            if not pick or pick == "Cancel":
                return

            if pick == "Retry with different description":
                description = questionary.text(
                    "New voice description:", default=description
                ).ask()
                if not description:
                    return
                continue

            idx = int(pick.split(" ")[1]) - 1
            generated_voice_id, preview_path = previews[idx]

        # Save to ElevenLabs
        voice_id = save_voice(
            generated_voice_id=generated_voice_id,
            name=f"{char_name}_voice",
            description=description,
        )

        # Save to config
        if "voices" not in config:
            config["voices"] = {}
        config["voices"][char_name] = {
            "voice_id": voice_id,
            "name": f"{char_name}_voice",
            "description": description,
            "source": "designed",
        }
        save_config(config)
        console.print(f"[green]Voice '{char_name}' saved to config.[/green]")

        if not auto_mode:
            input("\nPress Enter to continue...")
        return


def clone_voice_command(char_name=None, description=None, files_str=None, remove_noise=False, auto_mode=False):
    """Clone a voice from audio recordings."""
    from directors_chair.voice import clone_voice

    config = load_config()

    if not char_name:
        char_name = questionary.text("Character name (e.g. 'cranial'):").ask()
        if not char_name:
            return

    if not description:
        description = questionary.text("Voice description:").ask()
        if not description:
            return

    if not files_str:
        files_str = questionary.text(
            "Audio file paths (comma-separated):"
        ).ask()
        if not files_str:
            return

    audio_files = [f.strip() for f in files_str.split(",")]
    for af in audio_files:
        if not os.path.exists(af):
            console.print(f"[red]File not found: {af}[/red]")
            return

    if not auto_mode and not remove_noise:
        remove_noise = questionary.confirm(
            "Remove background noise from samples?", default=False
        ).ask()

    voice_id = clone_voice(
        name=f"{char_name}_voice",
        description=description,
        audio_files=audio_files,
        remove_background_noise=remove_noise,
    )

    if "voices" not in config:
        config["voices"] = {}
    config["voices"][char_name] = {
        "voice_id": voice_id,
        "name": f"{char_name}_voice",
        "description": description,
        "source": "cloned",
    }
    save_config(config)
    console.print(f"[green]Voice '{char_name}' cloned and saved to config.[/green]")

    if not auto_mode:
        input("\nPress Enter to continue...")


def remix_voice_command(char_name=None, description=None, new_name=None, auto_mode=False):
    """Remix an existing voice with a modification prompt."""
    from directors_chair.voice import remix_voice, save_voice
    from directors_chair.voice.elevenlabs_engine import play_audio

    config = load_config()
    voices = config.get("voices", {})

    if not voices:
        console.print("[yellow]No voices configured. Design or clone a voice first.[/yellow]")
        if not auto_mode:
            input("\nPress Enter to continue...")
        return

    if not char_name:
        choices = list(voices.keys()) + ["Back"]
        char_name = questionary.select("Select voice to remix:", choices=choices).ask()
        if not char_name or char_name == "Back":
            return

    if char_name not in voices:
        console.print(f"[red]Voice '{char_name}' not found in config.[/red]")
        return

    base_voice = voices[char_name]
    voice_id = base_voice["voice_id"]
    console.print(f"  [dim]Base: {base_voice.get('name', char_name)} ({voice_id[:20]}...)[/dim]")

    if not description:
        description = questionary.text("Describe the modification:").ask()
        if not description:
            return

    if not new_name:
        if not auto_mode:
            new_name = questionary.text(
                "Name for remixed voice:", default=f"{char_name}_remix"
            ).ask()
        else:
            new_name = f"{char_name}_remix"

    output_dir = os.path.join("assets", "voices", new_name)

    while True:
        previews = remix_voice(
            voice_id=voice_id,
            description=description,
            output_dir=output_dir,
        )

        if not previews:
            console.print("[red]No remix previews generated.[/red]")
            return

        if auto_mode:
            generated_voice_id, preview_path = previews[0]
        else:
            console.print(f"\n[bold]Listen to {len(previews)} remix preview(s):[/bold]")
            for i, (vid, path) in enumerate(previews):
                console.print(f"\n  [cyan]Remix {i + 1}:[/cyan] {path}")
                do_play = questionary.confirm(f"Play remix {i + 1}?", default=True).ask()
                if do_play:
                    play_audio(path)

            choices = [f"Remix {i + 1}" for i in range(len(previews))]
            choices += ["Retry with different description", "Cancel"]

            pick = questionary.select("Select remix:", choices=choices).ask()

            if not pick or pick == "Cancel":
                return

            if pick == "Retry with different description":
                description = questionary.text(
                    "New modification description:", default=description
                ).ask()
                if not description:
                    return
                continue

            idx = int(pick.split(" ")[1]) - 1
            generated_voice_id, preview_path = previews[idx]

        # Save
        saved_voice_id = save_voice(
            generated_voice_id=generated_voice_id,
            name=f"{new_name}_voice",
            description=description,
        )

        if "voices" not in config:
            config["voices"] = {}
        config["voices"][new_name] = {
            "voice_id": saved_voice_id,
            "name": f"{new_name}_voice",
            "description": description,
            "source": "remixed",
            "remixed_from": char_name,
        }
        save_config(config)
        console.print(f"[green]Remixed voice '{new_name}' saved to config.[/green]")

        if not auto_mode:
            input("\nPress Enter to continue...")
        return


def list_voices_command():
    """List all configured and remote voices."""
    from directors_chair.voice import list_voices

    config = load_config()
    local_voices = config.get("voices", {})

    if local_voices:
        table = Table(title="Configured Voices")
        table.add_column("Character", style="cyan")
        table.add_column("Voice ID", style="dim")
        table.add_column("Source", style="yellow")
        table.add_column("Description")

        for name, vdef in local_voices.items():
            table.add_row(
                name,
                vdef.get("voice_id", "")[:20] + "...",
                vdef.get("source", "unknown"),
                vdef.get("description", "")[:50],
            )
        console.print(table)
    else:
        console.print("[yellow]No local voices configured.[/yellow]")

    fetch = questionary.confirm(
        "Fetch voices from ElevenLabs account?", default=False
    ).ask()
    if fetch:
        remote = list_voices()
        table = Table(title="ElevenLabs Account Voices")
        table.add_column("Name", style="cyan")
        table.add_column("Voice ID", style="dim")
        table.add_column("Category", style="yellow")
        for v in remote:
            table.add_row(
                v["name"],
                v["voice_id"][:20] + "...",
                v.get("category", ""),
            )
        console.print(table)

    input("\nPress Enter to continue...")


def test_voice_command(char_name=None, text=None, auto_mode=False):
    """Generate a test speech sample from a configured voice."""
    from directors_chair.voice import generate_speech
    from directors_chair.voice.elevenlabs_engine import play_audio

    config = load_config()
    voices = config.get("voices", {})

    if not voices:
        console.print("[yellow]No voices configured.[/yellow]")
        if not auto_mode:
            input("\nPress Enter to continue...")
        return

    if not char_name:
        choices = list(voices.keys()) + ["Back"]
        char_name = questionary.select("Select voice to test:", choices=choices).ask()
        if not char_name or char_name == "Back":
            return

    if char_name not in voices:
        console.print(f"[red]Voice '{char_name}' not found in config.[/red]")
        return

    voice_id = voices[char_name]["voice_id"]

    if not text:
        text = questionary.text(
            "Test text:",
            default="The wasteland stretches on forever. We ride at dawn."
        ).ask()
        if not text:
            return

    output_dir = os.path.join("assets", "voices", char_name)
    output_path = os.path.join(output_dir, "test_speech.mp3")

    ok = generate_speech(voice_id=voice_id, text=text, output_path=output_path)
    if ok:
        if not auto_mode:
            do_play = questionary.confirm("Play audio?", default=True).ask()
            if do_play:
                play_audio(output_path)
        else:
            console.print(f"  [dim]Audio: {output_path}[/dim]")

    if not auto_mode:
        input("\nPress Enter to continue...")


def voice_menu():
    """Voice Design submenu."""
    while True:
        console.print(Panel("[bold]Voice Design[/bold]", border_style="cyan"))

        choice = questionary.select(
            "Select tool:",
            choices=[
                "a. Design Voice (from text prompt)",
                "b. Clone Voice (from audio recording)",
                "c. Remix Voice (mutate existing)",
                "d. List Voices",
                "e. Test Voice (TTS)",
                "f. Back",
            ]
        ).ask()

        if not choice or "f." in choice:
            return

        if "a." in choice:
            design_voice_command()
        elif "b." in choice:
            clone_voice_command()
        elif "c." in choice:
            remix_voice_command()
        elif "d." in choice:
            list_voices_command()
        elif "e." in choice:
            test_voice_command()
