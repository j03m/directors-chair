"""ElevenLabs voice engine — design, clone, remix, TTS."""

import base64
import json
import os
import subprocess
from typing import Dict, Any, List, Optional, Tuple

_client = None


def _get_client():
    """Singleton ElevenLabs client. Reads ELEVENLABS_API_KEY from env."""
    global _client
    if _client is None:
        from elevenlabs.client import ElevenLabs
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ELEVENLABS_API_KEY not set. Add it to your .env file."
            )
        _client = ElevenLabs(api_key=api_key)
    return _client


def design_voice(
    description: str,
    text: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> List[Tuple[str, str]]:
    """Design a voice from a text description.

    Returns list of (generated_voice_id, preview_mp3_path) tuples.
    """
    from directors_chair.cli.utils import console

    client = _get_client()

    kwargs = {"voice_description": description}
    if text:
        kwargs["text"] = text
    else:
        kwargs["auto_generate_text"] = True

    with console.status("[cyan]Designing voice via ElevenLabs...[/cyan]"):
        result = client.text_to_voice.create_previews(**kwargs)

    output_dir = output_dir or "assets/voices/_previews"
    os.makedirs(output_dir, exist_ok=True)

    previews = []
    metadata = {
        "description": description,
        "sample_text": result.text,
        "previews": [],
    }
    for i, preview in enumerate(result.previews):
        audio_bytes = base64.b64decode(preview.audio_base_64)
        preview_path = os.path.join(output_dir, f"preview_{i + 1}.mp3")
        with open(preview_path, "wb") as f:
            f.write(audio_bytes)

        duration = preview.duration_secs
        preview_meta = {
            "file": f"preview_{i + 1}.mp3",
            "generated_voice_id": preview.generated_voice_id,
            "duration_secs": duration,
            "media_type": preview.media_type,
        }
        metadata["previews"].append(preview_meta)
        console.print(f"  [green]Preview {i + 1}: {preview_path} ({duration:.1f}s)[/green]")
        previews.append((preview.generated_voice_id, preview_path))

    # Save metadata
    meta_path = os.path.join(output_dir, "previews.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    console.print(f"  [dim]Metadata: {meta_path}[/dim]")

    if result.text:
        console.print(f"  [dim]Sample text: {result.text[:80]}...[/dim]")

    return previews


def clone_voice(
    name: str,
    description: str,
    audio_files: List[str],
    remove_background_noise: bool = False,
) -> str:
    """Clone a voice from audio recordings. Returns voice_id."""
    from directors_chair.cli.utils import console

    client = _get_client()

    # Open files as binary handles for the SDK
    file_handles = []
    for path in audio_files:
        file_handles.append(open(path, "rb"))

    try:
        with console.status(
            f"[cyan]Cloning voice '{name}' from {len(audio_files)} sample(s)...[/cyan]"
        ):
            result = client.voices.ivc.create(
                name=name,
                files=file_handles,
                description=description,
                remove_background_noise=remove_background_noise,
            )
    finally:
        for fh in file_handles:
            fh.close()

    voice_id = result.voice_id
    console.print(f"  [green]Voice cloned: {voice_id}[/green]")
    return voice_id


def remix_voice(
    voice_id: str,
    description: str,
    text: Optional[str] = None,
    prompt_strength: Optional[float] = None,
    output_dir: Optional[str] = None,
) -> List[Tuple[str, str]]:
    """Remix an existing voice with a modification prompt.

    Returns list of (generated_voice_id, preview_mp3_path) tuples.
    """
    from directors_chair.cli.utils import console

    client = _get_client()

    kwargs = {
        "voice_description": description,
    }
    if text:
        kwargs["text"] = text
    else:
        kwargs["auto_generate_text"] = True
    if prompt_strength is not None:
        kwargs["prompt_strength"] = prompt_strength

    with console.status("[cyan]Remixing voice via ElevenLabs...[/cyan]"):
        result = client.text_to_voice.remix(voice_id, **kwargs)

    output_dir = output_dir or "assets/voices/_previews"
    os.makedirs(output_dir, exist_ok=True)

    previews = []
    metadata = {
        "base_voice_id": voice_id,
        "description": description,
        "sample_text": result.text if hasattr(result, 'text') else None,
        "previews": [],
    }
    for i, preview in enumerate(result.previews):
        audio_bytes = base64.b64decode(preview.audio_base_64)
        preview_path = os.path.join(output_dir, f"remix_preview_{i + 1}.mp3")
        with open(preview_path, "wb") as f:
            f.write(audio_bytes)

        duration = preview.duration_secs
        preview_meta = {
            "file": f"remix_preview_{i + 1}.mp3",
            "generated_voice_id": preview.generated_voice_id,
            "duration_secs": duration,
            "media_type": preview.media_type,
        }
        metadata["previews"].append(preview_meta)
        console.print(f"  [green]Remix {i + 1}: {preview_path} ({duration:.1f}s)[/green]")
        previews.append((preview.generated_voice_id, preview_path))

    # Save metadata
    meta_path = os.path.join(output_dir, "remix_previews.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    console.print(f"  [dim]Metadata: {meta_path}[/dim]")

    return previews


def save_voice(
    generated_voice_id: str,
    name: str,
    description: str,
) -> str:
    """Save a designed/remixed voice preview permanently. Returns voice_id."""
    from directors_chair.cli.utils import console

    client = _get_client()

    with console.status(f"[cyan]Saving voice '{name}' to ElevenLabs...[/cyan]"):
        voice = client.text_to_voice.create(
            voice_name=name,
            voice_description=description,
            generated_voice_id=generated_voice_id,
        )

    console.print(f"  [green]Voice saved: {voice.voice_id}[/green]")
    return voice.voice_id


def list_voices() -> List[Dict[str, Any]]:
    """List all voices in the ElevenLabs account."""
    client = _get_client()
    response = client.voices.get_all()
    return [
        {
            "voice_id": v.voice_id,
            "name": v.name,
            "category": getattr(v, "category", ""),
        }
        for v in response.voices
    ]


def generate_speech(
    voice_id: str,
    text: str,
    output_path: str,
    model_id: str = "eleven_multilingual_v2",
) -> bool:
    """Generate speech audio. Returns True on success."""
    from directors_chair.cli.utils import console

    client = _get_client()

    with console.status("[cyan]Generating speech...[/cyan]"):
        audio_iter = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=model_id,
            output_format="mp3_44100_128",
        )

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    size = 0
    with open(output_path, "wb") as f:
        for chunk in audio_iter:
            if isinstance(chunk, bytes):
                f.write(chunk)
                size += len(chunk)

    console.print(f"  [green]Speech saved: {output_path} ({size // 1024}KB)[/green]")
    return True


def play_audio(path: str):
    """Play audio via macOS afplay. Blocks until done."""
    try:
        subprocess.run(["afplay", path], check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
