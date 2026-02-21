# Directors Chair — Production Skill Guide

## What Is Directors Chair?

Directors Chair is an AI video production pipeline that turns storyboard JSON files into short films. The pipeline is:

**Blender layout** (primitive silhouettes) → **Keyframe generation** (photorealistic stills via Gemini/Nano Banana Pro) → **Kling i2v video** (animated clips) → **ffmpeg stitch** (final film)

Everything is driven from `scripts/chair.py` and configured through storyboard JSON files in `storyboards/`.

---

## Pipeline Architecture

### Phase 1: Blender Layout Generation
- LLM (Claude CLI) generates a Blender Python script from a natural language layout description
- Blender renders headless → composition PNG with colored primitive silhouettes
- Templates in `src/directors_chair/layout/templates.py`: body builders (`large`, `regular_male`, `regular_female`) with poses (`standing`, `arms_raised`, `fighting_stance`, `fallen`, `seated`)
- Character colors assigned automatically for visual differentiation
- Output: `assets/generated/videos/{name}/layouts/layout_NNN.png`

### Phase 2: Keyframe Generation
- **Gemini / Nano Banana Pro (DEFAULT, BEST)**: `fal-ai/nano-banana-pro/edit`
  - Accepts multiple `image_urls`: composition PNG + character reference images
  - Prompt uses positional refs: `@Image1` = comp layout, `@Element1`..`@ElementN` = characters
  - Auto-translated to "image 1", "character from image 2", etc.
  - Handles 3+ characters reliably in a single pass
  - `num_images` param (1-4) for generating variants
  - Set `"keyframe_engine": "gemini"` in storyboard (this is the default)
- **Kling O3 i2i (FALLBACK)**: `fal-ai/kling-image/o3/image-to-image`
  - Uses `elements` array with `frontal_image_url` + `reference_image_urls`
  - Struggles with 3+ characters — merges or drops them
  - Set `"keyframe_engine": "kling"` in storyboard
- Output: `assets/generated/videos/{name}/keyframes/keyframe_NNN.png`

### Phase 3: Kling i2v Video Generation
- Endpoint: `fal-ai/kling-video/o3/standard/image-to-video`
- `multi_prompt`: list of `{prompt, duration}` — **duration MUST be a STRING** ("3" to "10")
- `elements` for character consistency across beats
- `end_image_url` NOT supported with `multi_prompt`
- Returns slightly different resolutions per clip (e.g., 1276x720 vs 1284x716)
- Output: `assets/generated/videos/{name}/clips/clip_NNN.mp4`

### Phase 4: ffmpeg Stitch
- **MUST re-encode** — Kling returns different resolutions per clip
- `-c copy` concat silently breaks (video freezes at cut points)
- Uses `filter_complex`: scale to 1280:720 + pad + concat + libx264 CRF 18
- Output: `assets/generated/videos/{name}/{name}.mp4`

### Assemble Command
- Joins multiple storyboard final videos into one movie
- `python scripts/chair.py assemble --clips name1,name2 --name movie`
- Output: `assets/generated/movies/{name}.mp4`

---

## Storyboard JSON Schema

```json
{
  "name": "project_name",
  "keyframe_engine": "gemini",
  "characters": {
    "char_name": {
      "reference_image": "assets/training_data/folder/image.png",
      "body_type": "large|regular_male|regular_female",
      "description": "text description for prompts"
    }
  },
  "kling_params": {
    "aspect_ratio": "16:9",
    "resolution": "2K"
  },
  "shots": [
    {
      "name": "shot_name",
      "characters": ["char1", "char2"],
      "anchor_keyframe": 0,
      "layout_prompt_file": "shot01_layout.txt",
      "keyframe_prompt_file": "shot01_keyframe.txt",
      "beats": [
        {"prompt_file": "shot01_beat.txt", "duration": "5"}
      ]
    }
  ]
}
```

### Key Schema Details
- `keyframe_engine`: `"gemini"` (default, best) or `"kling"`
- `characters` at storyboard level: defines all available characters
- `characters` at shot level: optional list of character names to scope this shot (only these get uploaded as references)
- `anchor_keyframe`: optional integer index of a previous shot whose keyframe to use as composition reference (must be < current shot index). More powerful than layouts for visual continuity.
- `keyframe_edit_prompt_file`: optional post-generation edit pass (use sparingly — see pitfalls)
- `keyframe_passes`: list of `{"characters": ["name"], "prompt_file": "..."}` for multi-pass Kling (rarely needed with Gemini)
- Prompt files are resolved relative to the JSON file's directory
- Storyboards are organized in subdirectories: `storyboards/project_name/`
- Duration must be a STRING: `"3"` to `"10"`

---

## CLI Commands

### Interactive Mode
```bash
python scripts/chair.py
```
Menu-driven: "Generate Character", "Storyboard to Video", "Clip & Keyframe Tools", "Assemble Movie"

### Autonomous Storyboard Pipeline
```bash
# Full pipeline (layout → keyframe → video → stitch)
python scripts/chair.py storyboard --file storyboards/project/project.json

# Keyframes only (skip video generation)
python scripts/chair.py storyboard --file path.json --keyframes-only

# Regenerate specific keyframes (0-indexed)
python scripts/chair.py storyboard --file path.json --regen-keyframes 2,3,4

# Regenerate ALL keyframes
python scripts/chair.py storyboard --file path.json --regen-keyframes all

# Edit pass only on existing keyframes (requires keyframe_edit_prompt_file in JSON)
python scripts/chair.py storyboard --file path.json --edit-keyframes 5,9
```

### Character Generation
```bash
python scripts/chair.py generate --theme theme_name --count 5
```

### Clip & Keyframe Tools
```bash
# Edit a clip (Kling O1 v2v — preserves motion, tweaks visuals)
python scripts/chair.py edit-clip --file path.json --clip 15 --prompt "Make the truck bright red"

# Edit a clip and save as new file (don't overwrite original)
python scripts/chair.py edit-clip --file path.json --clip 15 --prompt "Add rain" --save-as-new

# Edit a keyframe (Nano Banana Pro — modify existing keyframe image)
python scripts/chair.py edit-keyframe --file path.json --keyframe 9 --prompt "Move gorilla farther away"

# Regenerate a single clip (from existing keyframe + beats)
python scripts/chair.py regen-clip --file path.json --clip 15
```

### Assemble Movie
```bash
python scripts/chair.py assemble --clips name1,name2,name3 --name final_movie
```

---

## Keyframe Prompt Writing Guide

### Structure
```
Use @Image1 as composition reference. [Shot description]. Desaturated color palette: sandy tans, dusty greys, rusted iron.

[Main action paragraph with @Element references binding characters to spatial positions.]

[Supporting details, background, props.]

[Mood/style closing.] Photorealistic, cinematic.
```

### @Element References
- `@Image1` = the Blender composition layout (always first)
- `@Element1` = first character in the shot's `characters` list
- `@Element2` = second character, etc.
- Always describe the character inline after the @Element reference:
  `@Element1 a raider in a cracked white hockey mask with sheet metal armor`

### Best Practices
- Put most important content first in the prompt
- Bind characters to explicit spatial positions ("foreground left", "background right")
- Simple props work better than complex ones ("baseball bat" > "duct-tape wrapped hockey stick")
- For scope/vignette shots: describe in the text prompt, don't rely on Blender compositing
- When referencing a truck: "white cab-over box truck with light weathering, photorealistic, real metal, real paint, real tires"
- For weapon consistency: be specific ("AK-47 rifle", "McMillan TAC-338 bolt-action sniper rifle with scope")

### Content Filter Workarounds
- Gemini/Nano Banana will reject graphic violence in keyframe prompts (blood spray, gunshot wounds)
- Move graphic details to beat prompts instead (Kling i2v is more permissive)
- Soften keyframe descriptions: "he has been hit and is falling" instead of "blood sprays from wound"
- Add "red mist" effects via beat prompts or edit passes

---

## Keyframe Iteration Workflow

### Regen vs Edit
- **Regen** (`--regen-keyframes N`): regenerates from scratch using layout + prompt. Use when composition is wrong.
- **Edit** (`--edit-keyframes N`): modifies existing keyframe with an edit prompt. Use when composition is right but details are wrong.
- Layout references heavily influence composition — if you copy keyframe_003 as layout_005, the model will follow that visual composition more than text changes

### Keyframe Anchoring (Composition Continuity)
Use `anchor_keyframe` to reference a previous shot's keyframe as the composition reference instead of a Blender layout. This is MORE powerful than layout files for keeping visual continuity between related shots (matching lighting, style, camera feel).

```json
{
    "name": "cliff_distance",
    "anchor_keyframe": 22,
    "keyframe_prompt_file": "shot27_keyframe.txt",
    "beats": [{"prompt_file": "shot27_beat.txt", "duration": "3"}]
}
```

Rules:
- `anchor_keyframe` must reference a shot that comes BEFORE the current shot in the array (lower index)
- The anchored keyframe must already exist (from a previous pipeline run or generated earlier in the same run)
- The pipeline falls back to the Blender layout if the anchor keyframe is missing
- Best for: matching lighting/atmosphere, maintaining visual style across a sequence, shots that share the same setting

Manual alternative (still works): `cp keyframes/keyframe_003.png layouts/layout_005.png` then regen shot 5.

### Manual Edit Workflow
1. Add `"keyframe_edit_prompt_file": "shotNN_edit.txt"` to the shot in JSON
2. Write the edit prompt file
3. Run `--edit-keyframes N`
4. Remove the `keyframe_edit_prompt_file` entry when done (don't leave stale edits)

Alternatively, use the interactive UI: **Clip & Keyframe Tools → Edit Keyframe** — enter the edit prompt directly, no JSON changes needed.

### Common Fixes
- **Extra/duplicate characters**: edit prompt "Remove the extra person on the far left"
- **Wrong weapon**: edit prompt "The weapon should be [correct weapon], NOT [wrong weapon]"
- **Wrong truck style**: include "white cab-over box truck with light weathering, photorealistic" in prompts
- **Pose changes**: edit is better than regen when layout reference locks composition
- **Simplify problem shots**: if multi-character positioning keeps failing, simplify the shot (e.g., switch from wide shot with dead bodies to close-up of one character)

---

## Production Workflow Tips

### Storyboard Organization
- Separate storyboards per sequence — join final films together with `assemble`
- Only include characters needed per shot in the shot's `characters` list
- Don't replicate all characters if a shot only needs one

### Shot Ordering
- Shots render in array order from the JSON
- To reorder: swap JSON entries AND rename corresponding keyframe/layout/clip files
- File naming is 0-indexed: `keyframe_000.png`, `layout_000.png`, `clip_000.mp4`

### Resume Behavior
- Pipeline checks if output files exist before regenerating
- To force regen: delete the file or use `--regen-keyframes`
- This means you can stop and resume at any point

### Auto Edit Passes — Pitfall
- `keyframe_edit_prompt_file` entries auto-apply on EVERY regen
- Stale edit prompts from previous iterations can ruin good keyframes
- Best practice: do NOT leave `keyframe_edit_prompt_file` in JSON permanently
- Add it temporarily when you need a manual edit, then remove it

---

## File Layout

```
directors-chair/
├── scripts/chair.py                          # CLI entry point
├── src/directors_chair/
│   ├── cli/commands/storyboard.py           # 4-phase pipeline orchestration
│   ├── cli/commands/assemble.py             # Multi-storyboard assembly
│   ├── layout/
│   │   ├── generator.py                     # Claude CLI → Blender script → render
│   │   └── templates.py                     # Blender body builders, poses, helpers
│   ├── keyframe/
│   │   ├── kling.py                         # Kling O3 i2i keyframe engine
│   │   └── nano_banana.py                   # Gemini/Nano Banana Pro keyframe + edit
│   ├── video/engines/fal_kling_engine.py    # Kling O3 i2v with multi-prompt beats
│   └── storyboard/loader.py                # JSON loader + validator
├── storyboards/
│   └── project_name/
│       ├── project_name.json                # Storyboard definition
│       ├── shot01_layout.txt                # Layout prompt
│       ├── shot01_keyframe.txt              # Keyframe prompt
│       └── shot01_beat.txt                  # Video beat prompt
├── assets/
│   ├── training_data/{char_name}/           # Character reference images
│   └── generated/videos/{storyboard_name}/
│       ├── layouts/layout_NNN.png           # Blender compositions
│       ├── keyframes/keyframe_NNN.png       # Generated keyframes
│       ├── clips/clip_NNN.mp4               # Video clips
│       └── {storyboard_name}.mp4            # Final stitched film
└── config/config.json                       # App config (blender_path, directories)
```

---

## fal.ai API Patterns

```python
import fal_client

# Upload local file → URL
url = fal_client.upload_file("path/to/file.png")

# Submit async job
handler = fal_client.submit("fal-ai/endpoint", arguments={...})

# Stream progress
for event in handler.iter_events(with_logs=True):
    if isinstance(event, fal_client.InProgress) and event.logs:
        for log in event.logs:
            print(log.get('message', ''))

# Get final result
result = handler.get()
```

- fal.ai storage URLs may expire — always download a local copy
- 422 errors = content filter rejection (try softer language)
- 500 errors = server issues (retry with backoff)
- Nano Banana Pro endpoint: `fal-ai/nano-banana-pro/edit`
- Kling i2i endpoint: `fal-ai/kling-image/o3/image-to-image`
- Kling i2v endpoint: `fal-ai/kling-video/o3/standard/image-to-video`

---

## Environment Setup

Required environment variables (`.env`):
- `FAL_KEY` — fal.ai API key
- `HF_TOKEN` — Hugging Face token (optional, for model downloads)

Required software:
- Python 3.10+
- Blender (path configurable in `config/config.json` under `system.blender_path`)
- Claude Code CLI (`claude` on PATH) — for Blender script generation
- ffmpeg — for video stitching

```bash
pip install -e .  # Install directors-chair
```

---

## Audio & Dialogue — Kling 3.0 Native Audio (ACTIVE)

Kling 3.0 generates dialogue + SFX + ambient audio natively in the video model. No separate TTS/lip-sync pipeline needed.

- See **`skills/kling-3-prompting.md`** for full prompting guide, API reference, and dialogue syntax
- Key constraint: `voice_ids` and `elements` CANNOT be combined
- Voice references created via `fal-ai/kling-video/create-voice` (5-30s clean audio)
- Max 2 custom voices per clip. Use `<<<voice_1>>>` and `<<<voice_2>>>` in prompt
- Bind voices to characters via spatial description when not using elements

### MMAudio V2 (supplemental SFX)
- `fal-ai/mmaudio-v2` — video-synced audio generation
- Can layer additional SFX on top of Kling's native audio
- Cost: ~$0.001/sec
