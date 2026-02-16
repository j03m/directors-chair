import os
import subprocess

from .templates import TEMPLATE_CODE, CHARACTER_COLORS, BODY_TYPE_BUILDERS


def generate_layout(layout_prompt: str, characters: dict, output_path: str) -> bool:
    """Generate a Blender layout frame using Claude Code CLI.

    Args:
        layout_prompt: Natural language description of the scene layout
        characters: Dict of character definitions with body_type, description
        output_path: Where to save the rendered PNG

    Returns:
        True if layout was generated successfully
    """
    from directors_chair.cli.utils import console

    # Ensure absolute path so Blender finds the output
    output_path = os.path.abspath(output_path)

    # Build character description for the LLM
    char_lines = []
    for i, (name, cdef) in enumerate(characters.items()):
        body_type = cdef.get("body_type", "regular_male")
        builder = BODY_TYPE_BUILDERS.get(body_type, "build_regular_male")
        color = CHARACTER_COLORS[i % len(CHARACTER_COLORS)]
        desc = cdef.get("description", name)
        char_lines.append(
            f"- {name}: body_type={body_type}, builder function={builder}(), "
            f"color={color}, description='{desc}'"
        )
    char_desc = "\n".join(char_lines)

    system_prompt = (
        "You are a Blender Python script generator. "
        "You output ONLY valid Python code. No markdown, no explanations, no commentary. "
        "Just the raw Python script that Blender can execute."
    )

    prompt = f"""Generate a complete Blender Python script.

The script MUST start by defining these exact helper functions, then use them:

{TEMPLATE_CODE}

After the helpers, add scene setup code:
1. clean_scene()
2. scene = bpy.context.scene
3. setup_render(scene)
4. add_light(scene)
5. Create materials with make_mat()
6. add_ground() with dark ground material (0.2, 0.15, 0.1, 1)
7. Place characters using build_*_figure() functions if the layout calls for them
8. setup_camera() positioned per the layout description
9. scene.frame_set(1)
10. scene.render.filepath = "{output_path}"
11. bpy.ops.render.render(write_still=True)

Characters available:
{char_desc}

Layout:
{layout_prompt}

Rules:
- Output ONLY Python code, nothing else
- If layout says no characters, skip character placement
- Use appropriate poses: standing, arms_raised, fighting_stance, fallen, seated"""

    console.print("  [dim]Generating Blender script via Claude...[/dim]")

    # Unset CLAUDECODE env var to allow nested invocation
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    result = subprocess.run(
        ["claude", "-p", prompt,
         "--append-system-prompt", system_prompt,
         "--output-format", "text"],
        capture_output=True, text=True, env=env,
    )

    if result.returncode != 0:
        console.print(f"[red]Claude CLI failed (exit {result.returncode})[/red]")
        if result.stderr:
            console.print(f"[red]{result.stderr[:500]}[/red]")
        return False

    script = result.stdout.strip()

    # Strip markdown fences if present
    if "```" in script:
        lines = script.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        script = "\n".join(lines)

    # Validate it looks like Python, not prose
    if not any(line.strip().startswith(("import ", "def ", "bpy.", "clean_scene")) for line in script.split("\n")[:20]):
        console.print("[red]Claude returned prose instead of code. Retrying...[/red]")
        # One retry with even more explicit instruction
        result = subprocess.run(
            ["claude", "-p",
             f"Output ONLY a Python script for Blender. No text. No explanation.\n\n{prompt}",
             "--append-system-prompt", "Output raw Python code only. Never output explanations.",
             "--output-format", "text"],
            capture_output=True, text=True, env=env,
        )
        if result.returncode != 0:
            return False
        script = result.stdout.strip()
        if "```" in script:
            lines = script.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            script = "\n".join(lines)

    # Save script for Blender to execute
    script_path = output_path.replace(".png", "_layout.py")
    with open(script_path, "w") as f:
        f.write(script)

    console.print(f"  [dim]Script saved: {script_path}[/dim]")
    return render_layout(script_path, output_path)


def render_layout(script_path: str, output_path: str) -> bool:
    """Run a Blender script headless and verify output."""
    from directors_chair.cli.utils import console
    from directors_chair.config.loader import load_config

    config = load_config()
    blender_path = config.get("system", {}).get(
        "blender_path",
        "/Applications/Blender.app/Contents/MacOS/Blender"
    )

    if not os.path.exists(blender_path):
        console.print(f"[red]Blender not found at: {blender_path}[/red]")
        console.print("[yellow]Set system.blender_path in config.json[/yellow]")
        return False

    console.print("  [dim]Running Blender headless...[/dim]")

    result = subprocess.run(
        [blender_path, "--background", "--python", script_path],
        capture_output=True, text=True,
    )

    if result.returncode != 0:
        console.print(f"[red]Blender failed (exit {result.returncode})[/red]")
        if result.stderr:
            for line in result.stderr.split("\n"):
                if "Error" in line or "error" in line:
                    console.print(f"  [red]{line}[/red]")
        return False

    if not os.path.exists(output_path):
        console.print(f"[red]Blender ran but output not found: {output_path}[/red]")
        return False

    size_kb = os.path.getsize(output_path) // 1024
    console.print(f"  [green]Layout rendered: {os.path.basename(output_path)} ({size_kb}KB)[/green]")
    return True
