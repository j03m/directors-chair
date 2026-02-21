"""Hume Octave TTS engine — expressive voice acting with acting instructions."""

import asyncio
import base64
import json
import os
import subprocess
from typing import Dict, Any, List, Optional, Tuple

_client = None


def _get_client():
    """Singleton Hume client. Reads HUME_API_KEY from env."""
    global _client
    if _client is None:
        from hume import HumeClient
        api_key = os.environ.get("HUME_API_KEY")
        if not api_key:
            raise RuntimeError(
                "HUME_API_KEY not set. Add it to your .env file."
            )
        _client = HumeClient(api_key=api_key)
    return _client


def design_voice(
    description: str,
    text: str,
    output_dir: Optional[str] = None,
    num_generations: int = 3,
) -> List[Tuple[str, str]]:
    """Design a voice from a text description.

    Returns list of (generation_id, preview_mp3_path) tuples.
    """
    from directors_chair.cli.utils import console
    from hume.tts import PostedUtterance

    client = _get_client()

    output_dir = output_dir or "assets/voices/_hume_previews"
    os.makedirs(output_dir, exist_ok=True)

    previews = []
    metadata = {
        "description": description,
        "sample_text": text,
        "previews": [],
    }

    with console.status("[cyan]Designing voice via Hume Octave...[/cyan]"):
        result = client.tts.synthesize_json(
            utterances=[
                PostedUtterance(
                    text=text,
                    description=description,
                )
            ],
            num_generations=num_generations,
            version="1",
        )

    for i, generation in enumerate(result.generations):
        audio_bytes = base64.b64decode(generation.audio)
        preview_path = os.path.join(output_dir, f"preview_{i + 1}.mp3")
        with open(preview_path, "wb") as f:
            f.write(audio_bytes)

        gen_id = generation.generation_id
        duration = generation.duration
        preview_meta = {
            "file": f"preview_{i + 1}.mp3",
            "generation_id": gen_id,
            "duration_secs": duration,
        }
        metadata["previews"].append(preview_meta)
        console.print(f"  [green]Preview {i + 1}: {preview_path} ({duration:.1f}s)[/green]")
        previews.append((gen_id, preview_path))

    meta_path = os.path.join(output_dir, "previews.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    console.print(f"  [dim]Metadata: {meta_path}[/dim]")

    return previews


def save_voice(
    generation_id: str,
    name: str,
) -> str:
    """Save a designed voice permanently. Returns voice name."""
    from directors_chair.cli.utils import console

    client = _get_client()

    with console.status(f"[cyan]Saving voice '{name}' to Hume...[/cyan]"):
        voice = client.tts.voices.create(
            generation_id=generation_id,
            name=name,
        )

    console.print(f"  [green]Voice saved: {name}[/green]")
    return name


def list_voices() -> List[Dict[str, Any]]:
    """List all custom voices in the Hume account."""
    client = _get_client()
    response = client.tts.voices.list()
    voices = []
    for v in response:
        voices.append({
            "name": v.name if hasattr(v, 'name') else str(v),
            "provider": "CUSTOM_VOICE",
        })
    return voices


def generate_speech(
    text: str,
    output_path: str,
    voice_name: Optional[str] = None,
    description: Optional[str] = None,
    speed: float = 1.0,
    context_generation_id: Optional[str] = None,
) -> bool:
    """Generate expressive speech with acting instructions.

    Args:
        text: The dialogue line to speak.
        output_path: Where to save the audio file.
        voice_name: Name of a saved Hume voice (custom or built-in).
        description: Acting instructions — e.g. "deadpan, telling a joke
                     he's barely keeping a straight face for". This controls
                     tone, emotion, pacing, delivery style.
        speed: Speaking rate multiplier (0.75-1.5 recommended).
        context_generation_id: Previous generation_id for voice consistency.
    """
    from directors_chair.cli.utils import console
    from hume.tts import PostedUtterance

    client = _get_client()

    # Build utterance
    utterance_kwargs = {"text": text}
    if description:
        utterance_kwargs["description"] = description
    if speed != 1.0:
        utterance_kwargs["speed"] = speed

    # Add voice if specified
    if voice_name:
        from hume.tts import PostedUtteranceVoiceWithName
        utterance_kwargs["voice"] = PostedUtteranceVoiceWithName(name=voice_name)

    utterance = PostedUtterance(**utterance_kwargs)

    # Build synthesis kwargs
    synth_kwargs = {
        "utterances": [utterance],
        "version": "1",
    }

    # Add context for voice consistency across lines
    if context_generation_id:
        from hume.tts import PostedContextWithGenerationId
        synth_kwargs["context"] = PostedContextWithGenerationId(
            generation_id=context_generation_id
        )

    desc_label = f" [{description[:50]}...]" if description else ""
    with console.status(f"[cyan]Generating speech via Hume Octave{desc_label}...[/cyan]"):
        result = client.tts.synthesize_json(**synth_kwargs)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    generation = result.generations[0]
    audio_bytes = base64.b64decode(generation.audio)
    with open(output_path, "wb") as f:
        f.write(audio_bytes)

    size_kb = len(audio_bytes) // 1024
    duration = generation.duration
    gen_id = generation.generation_id
    console.print(f"  [green]Speech saved: {output_path} ({size_kb}KB, {duration:.1f}s)[/green]")
    console.print(f"  [dim]generation_id: {gen_id}[/dim]")

    # Save metadata alongside audio
    meta_path = output_path.rsplit('.', 1)[0] + '_meta.json'
    with open(meta_path, "w") as f:
        json.dump({
            "text": text,
            "voice_name": voice_name,
            "description": description,
            "speed": speed,
            "generation_id": gen_id,
            "duration": duration,
        }, f, indent=2)

    return True


def generate_dialogue(
    lines: List[Dict[str, Any]],
    output_dir: str,
) -> List[str]:
    """Generate multiple dialogue lines with acting instructions.

    Each line dict should have:
        - text: The dialogue line
        - character: Character name (maps to voice)
        - direction: Acting instruction (e.g. "deadpan, amused")
        - voice_name: Optional Hume voice name override
        - speed: Optional speed override

    Returns list of output audio file paths.
    """
    from directors_chair.cli.utils import console

    os.makedirs(output_dir, exist_ok=True)
    paths = []

    for i, line in enumerate(lines):
        text = line["text"]
        character = line.get("character", f"character_{i}")
        direction = line.get("direction", None)
        voice_name = line.get("voice_name", None)
        speed = line.get("speed", 1.0)

        output_path = os.path.join(output_dir, f"line_{i:03d}_{character}.mp3")
        console.print(f"\n[bold]Line {i + 1}: {character}[/bold]")
        console.print(f"  [dim]\"{text}\"[/dim]")
        if direction:
            console.print(f"  [dim]Direction: {direction}[/dim]")

        generate_speech(
            text=text,
            output_path=output_path,
            voice_name=voice_name,
            description=direction,
            speed=speed,
        )
        paths.append(output_path)

    console.print(f"\n[green]Generated {len(paths)} dialogue lines in {output_dir}[/green]")
    return paths


def play_audio(path: str):
    """Play audio via macOS afplay. Blocks until done."""
    try:
        subprocess.run(["afplay", path], check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
