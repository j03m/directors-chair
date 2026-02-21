# Kling 3.0 — Prompting & API Reference

## API Endpoints (fal.ai)

| Endpoint | Use |
|----------|-----|
| `fal-ai/kling-video/v3/pro/image-to-video` | Keyframe → animated clip (best quality) |
| `fal-ai/kling-video/v3/standard/image-to-video` | Keyframe → animated clip (cheaper) |
| `fal-ai/kling-video/v3/pro/text-to-video` | Text-only → video |
| `fal-ai/kling-video/v3/standard/text-to-video` | Text-only → video (cheaper) |
| `fal-ai/kling-video/create-voice` | Upload audio → get voice_id |
| `fal-ai/kling-video/o3/standard/image-to-video` | Legacy O3 endpoint (no native audio) |

### Pricing (per second)
- V3 Pro with voice control: $0.392/s
- V3 Pro audio off: ~$0.20/s
- V3 Standard with voice control: ~$0.25/s
- V3 Standard audio off: $0.168/s

---

## API Parameters — Image-to-Video

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `start_image_url` | string | **required** | Keyframe image URL |
| `prompt` | string | — | Single prompt. Use this OR `multi_prompt`, not both |
| `multi_prompt` | list | — | Multi-shot beats. Each: `{prompt, duration}` |
| `duration` | enum | `"5"` | `"3"` to `"15"` (string) |
| `aspect_ratio` | enum | `"16:9"` | `"16:9"`, `"9:16"`, `"1:1"` |
| `generate_audio` | bool | `true` | Native audio (dialogue + SFX + ambient) |
| `voice_ids` | list[str] | — | Max 2 voice IDs. Ref as `<<<voice_1>>>`, `<<<voice_2>>>` |
| `elements` | list | — | Character/object references. **CANNOT combine with voice_ids** |
| `end_image_url` | string | — | Final frame target. **NOT supported with multi_prompt** |
| `negative_prompt` | string | `"blur, distort, and low quality"` | |
| `cfg_scale` | float | `0.5` | Prompt adherence (higher = stricter) |
| `shot_type` | enum | `"customize"` | `"customize"` or `"intelligent"` |

### Element Schema (when NOT using voice_ids)
```python
{
    "frontal_image_url": "https://...",       # Front-facing reference (required)
    "reference_image_urls": ["https://..."],  # Additional angles (required)
}
# OR
{
    "video_url": "https://..."  # 3-8 second reference video
}
```
Reference in prompt as `@Element1`, `@Element2`, etc.

### Multi-Prompt Schema
```python
{
    "prompt": "Beat description...",
    "duration": "5"  # STRING, "3" to "15"
}
```

---

## CRITICAL CONSTRAINT: voice_ids vs elements

**You CANNOT use `voice_ids` and `elements` together.** The API returns:
> "Custom Voice IDs are not supported with Elements."

Choose one:
- **Elements** (no custom voices): Character visual consistency via reference images. Audio auto-generated with model's default voices.
- **Voice IDs** (no elements): Custom voice binding. Rely on keyframe + descriptive prompt for character identification. Describe characters explicitly by position/appearance.

---

## Create Voice

Endpoint: `fal-ai/kling-video/create-voice`

```python
handler = fal_client.submit("fal-ai/kling-video/create-voice", arguments={
    "voice_url": "https://..."  # 5-30 seconds, clean single voice
})
result = handler.get()
voice_id = result["voice_id"]  # e.g. "853965338566852685"
```

- Accepts: .mp3, .wav, .m4a, .ogg, .aac, .mp4, .mov
- Duration: 5-30 seconds
- Must be clean, single-voice audio
- Cost: $0.007 per creation
- Content policy may flag recognizable celebrity voices (pitch-shift to avoid)

---

## Prompt Structure — The Master Formula

```
[Environment + ambient audio context]

[Character A introduction + physical action]
[Character A, voice tone/emotion]: "Dialogue line"

[Character B reaction + physical action]
[Character B, voice tone/emotion]: "Response line"

[Camera direction + emotional progression]
```

### Core Principles

1. **Think in shots, not clips** — describe framing, subject, and motion per shot
2. **Anchor subjects early** — define characters clearly at prompt start, keep descriptions consistent
3. **Describe motion explicitly** — include BOTH subject movement AND camera behavior
4. **Use native audio intentionally** — explicitly indicate who speaks and when
5. **Lock first, then move** (i2v) — treat input image as anchor, describe evolution FROM it

---

## Dialogue Prompting

### Character Labeling (CRITICAL)
Use unique, consistent labels. Avoid pronouns.

**Good:**
```
[Character A: Black-suited Agent, raspy deep voice]: "We need to move."
[Character B: Young Scientist, nervous stammering voice]: "I—I don't think that's safe."
```

**Bad:**
```
[Agent] says something. Then, he says something else.
[Man/Woman] says...
```

### Voice Descriptor Examples
- `deep, authoritative, gravelly voice`
- `sharp, fast-paced, angry tone`
- `calm, measured, deadpan delivery`
- `nervous, stammering, breathless`
- `low growl, barely audible`
- `shouting, panicked, cracking voice`

### Action Binding — Action BEFORE Dialogue
Always describe the physical action, then the line. Don't separate them.

**Good:**
```
The warrior leans forward in his chair, squinting at the robot. [Warrior, deadpan flat voice]: "No. We fucking should not."
```

**Bad:**
```
[Warrior]: "No. We fucking should not."
The warrior is leaning forward.
```

### Temporal Markers
Use linking words to control rhythm and sequence:
- "Immediately," — fast cut / instant response
- "Pause." or "A beat of silence." — dramatic timing
- "Then," — sequential action
- "Suddenly," — surprise/interruption
- "Meanwhile," — parallel action

### Multi-Character Dialogue Example
```
A dimly lit desert campfire. Two friends slouch in beach chairs.

The human warrior on the left glances sideways at the gorilla.
[Warrior, flat deadpan voice]: "No we fucking should not. That is just bait."

The gorilla on the right snorts, barely turning his head.
[Gorilla, low rumbling amused voice]: "Stop being a little bitch. Let's go look."

A beat. They exchange a look — faint smirks, thinking the same thing.
```

### Speaker Attribution Fix
When the model confuses who's speaking, explicitly tag:
```
[Speaker: the man on the left] "Hello."
```
This prevents "audio ghosting" where voices attach to the wrong character.

---

## Voice ID Binding Without Elements

Since voice_ids and elements can't combine, bind voices to characters via descriptive prompting:

```python
prompt = '''Two friends sit in beach chairs by a desert campfire.
On the left, a human warrior in desert combat gear.
On the right, a gorilla in viking armor with a horned helmet.

The warrior on the left says <<<voice_1>>> "No we should not. That is just bait."
The gorilla on the right responds <<<voice_2>>> "Stop being a little bitch. Let's go look."
They exchange a deadpan look.'''

arguments = {
    "start_image_url": keyframe_url,
    "prompt": prompt,
    "duration": "5",
    "generate_audio": True,
    "voice_ids": [cranial_voice_id, gorilla_voice_id],
}
```

Key tips:
- Describe each character's position explicitly ("on the left", "on the right")
- Place `<<<voice_N>>>` immediately before the dialogue it belongs to
- Reference characters by their visual description, not abstract names
- The keyframe image anchors who is where — prompt must match

---

## Camera & Cinematography Language

Kling 3.0 understands professional shot language:

| Term | Meaning |
|------|---------|
| `profile shot` | Side view of subject |
| `macro close-up` | Extreme detail shot |
| `tracking shot` | Camera follows subject movement |
| `POV` | First-person perspective |
| `shot-reverse-shot` | Classic dialogue coverage |
| `3/4 tracking shot` | Camera at 45 deg ahead and to the side |
| `high-angle satellite view` | Bird's eye looking down |
| `smooth 180-degree orbit` | Camera circles subject |
| `push in` | Camera moves toward subject |
| `pull back` | Camera moves away from subject |
| `dolly zoom` | Vertigo effect |
| `handheld` | Shaky, documentary feel |
| `locked off` | Static tripod shot |
| `crane shot` | High sweeping movement |

Describe camera movement explicitly:
```
The camera slowly pushes in on the warrior's face as he speaks,
then whip-pans to the gorilla's reaction.
```

---

## Multi-Shot / Multi-Prompt Beats

For longer sequences, use `multi_prompt` instead of `prompt`:

```python
arguments = {
    "start_image_url": keyframe_url,
    "multi_prompt": [
        {"prompt": "Beat 1 description...", "duration": "5"},
        {"prompt": "Beat 2 description...", "duration": "5"},
    ],
    "generate_audio": True,
    # voice_ids work with multi_prompt
}
```

- Up to 6 shots in a single generation
- Total duration up to 15 seconds
- Each beat can have different duration ("3" to "15")
- Characters maintain consistency across beats
- **Duration is a STRING, not an integer**
- `end_image_url` is NOT supported with `multi_prompt`

---

## Image-to-Video: Lock First, Then Move

When using a keyframe (i2v), the image is the anchor:
- Focus the prompt on what HAPPENS, not what the scene looks like
- The model preserves identity, layout, and composition from the image
- Describe the evolution: movement, dialogue, camera motion
- Don't re-describe what's already visible in the keyframe

**Good i2v prompt:**
```
The warrior turns to the gorilla. A beat of silence, then the gorilla snorts.
Camera slowly pushes in. Warm campfire light flickers across their faces.
```

**Bad i2v prompt:**
```
A warrior in combat gear and a gorilla in viking armor sit in beach chairs
by a campfire in the desert at night. There is a rusty robot nearby.
The warrior turns to the gorilla...
```
(Redundant — the keyframe already shows all this.)

---

## Duration Guide

| Duration | Best For |
|----------|----------|
| `"3"` | Quick reaction shots, single gesture |
| `"5"` | Standard dialogue exchange, one action |
| `"7"` | Extended dialogue, character walks to position |
| `"10"` | Multi-beat sequence, complex choreography |
| `"15"` | Full mini-scene, multiple actions + reactions |

Longer = more room for the model to fill. Over-describe for long durations to prevent hallucination.

---

## Ambient Audio & SFX

With `generate_audio: true`, Kling generates:
- Dialogue (with lip sync)
- Ambient sound (wind, fire crackling, room tone)
- Sound effects (footsteps, impacts, doors)

Control ambient audio in the prompt:
```
Desert wind howls softly. A campfire crackles and pops.
Distant coyote calls echo across the sand.
```

The model synthesizes audio to match the visual scene. Describe the soundscape you want.

---

## Language Support

Native audio supports:
- English (use lowercase for speech, UPPERCASE for acronyms/proper nouns)
- Chinese (Mandarin)
- Japanese
- Korean
- Spanish
- Regional dialects and accents
- Code-switching between languages mid-dialogue

Other languages auto-translate to English.

---

## Content Moderation Notes

- Kling is more permissive than Gemini for action/violence in video generation
- Strong profanity in dialogue generally works
- Graphic violence descriptions may get flagged — use implications over explicit descriptions
- Voice cloning of recognizable celebrities may be flagged — pitch-shift to avoid

---

## Common Pitfalls

1. **Round-robin dialogue**: Without explicit character binding, Kling splits dialogue across all visible characters sequentially. Fix: bind voices to positions and characters.
2. **voice_ids + elements conflict**: Can't use both. Choose voice consistency OR visual consistency.
3. **Duration as integer**: `duration: 5` fails. Must be `duration: "5"` (string).
4. **Different resolutions per clip**: Kling returns slightly different resolutions (1276x720 vs 1284x716). Must re-encode when stitching with ffmpeg.
5. **Prompt too long**: Keep under 512 chars per beat for multi_prompt. Single prompt can be longer.
6. **Pronouns cause confusion**: "He says... then he responds..." — model doesn't know which "he". Use character labels.
7. **Describing the keyframe**: In i2v mode, don't waste prompt re-describing what's in the image. Focus on action and dialogue.
