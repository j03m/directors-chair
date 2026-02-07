# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Directors-Chair is an interactive CLI console for AI image generation and LoRA training, built for Apple Silicon Macs. It uses Flux models (via mflux/MLX) for generation and supports both local and cloud-based (Fal.ai) LoRA training.

## Running the Application

```bash
# Main entry point (loads .env automatically)
python scripts/chair.py

# Alternative
python -m directors_chair.cli
```

## Installation

```bash
python -m pip install -e .
# or
pip install -r requirements.txt
```

## Environment Variables (.env)

Required environment variables:
- `FAL_KEY` — Fal.ai API key (for cloud LoRA training)
- `HF_TOKEN` — Hugging Face token (for gated model downloads)
- `ACCELERATE_USE_MPS_DEVICE=True` — Enable Apple Silicon MPS
- `HF_HOME=./models` — Local model cache directory

## Architecture

**Source layout:** `src/directors_chair/` with these modules:

- **cli/** — Interactive menu system using Rich + Questionary. `__init__.py` is the main menu router; each command lives in `cli/commands/` (system, models, generation, training).
- **generation/** — Image generation engine. `engine.py` defines `BaseGenerator` and `ZImageTurboGenerator`. `factory.py` implements a factory with singleton caching keyed by model token + LoRA paths.
- **training/** — Pluggable training engine system. `manager.py` provides `TrainingManager` abstraction; `engines/base.py` defines the `BaseTrainingEngine` ABC; `engines/mflux_engine.py` is the local Apple Silicon implementation. Designed for future engine backends (e.g., Nvidia DGX).
- **assets/** — Model download management via Hugging Face Hub.
- **config/** — JSON config loader/saver for `config/config.json`.

**Key scripts:**
- `scripts/chair.py` — Main entry point (thin wrapper)
- `scripts/train_lora.py` — Standalone cloud-based LoRA training via Fal.ai API

## Configuration System

`config/config.json` drives model IDs, directory paths, training defaults, and **themes**. Themes are named generation presets with prompt files, trigger words, generator selection, LoRA references, and generation parameters (steps, guidance, aspect ratio).

Generated images output to `assets/training_data/{trigger}_{name}/` with `.png`, `.txt` (caption), and `.json` (metadata) per image.

Trained LoRAs save to `assets/loras/` and get registered in config.json.

## Key Patterns

- **Factory + singleton cache** for generators — avoids reloading large models
- **ABC-based engine abstraction** for training — swap implementations without CLI changes
- **Module-level singleton** for TrainingManager via `get_training_manager()`
- **Let errors crash** — deliberate choice to avoid try/except in core logic for debugging visibility; subprocess calls use `check_call()` to raise on failure
- **Configuration-driven** — themes, model IDs, and defaults all externalized to JSON

## No Test/Lint Infrastructure

There is currently no test suite, linter, or formatter configured. The project is at v0.1.0 with manual testing via the CLI.
