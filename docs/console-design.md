# Director's Chair - CLI Interaction Design

## Overview
This document outlines the design for the interactive Command Line Interface (CLI) for the **Director's Chair** project. The goal is to create a "wizard-style" experience that guides the user through setup, model management, and image generation, abstracting away complex technical details (like quantization and offloading) while offering powerful customization.

## 1. Core Principles
*   **Interactive & Guide-like:** Use menus, selection lists, and clear prompts (similar to `inquirer` or `questionary`) rather than requiring complex command-line arguments.
*   **Hardware Aware:** Automatically detect system capabilities (e.g., Apple Silicon, RAM size) to recommend the best path (e.g., Quantized Flux for 36GB Macs).
*   **Stateful:** Remember user choices (themes, default models) in a config file so they don't have to re-enter them every time.

## 2. Main Menu Structure
Upon running the main script (e.g., `python main.py` or `directors-chair`), the user sees:

```text
========================================
       🎬 DIRECTOR'S CHAIR 🎬
   AI Image Generation & Training Kit
========================================

System: Darwin (M3 Max) | RAM: 36 GB | Pytorch: MPS Available

Main Menu:
  [1] 🛠️  System Setup & Health Check
  [2] 📥 Manage Models (Download/Select)
  [3] 📸 Generate Training Images
  [4] ⚙️  Settings & Defaults
  [5] 🚪 Exit
```

## 3. Detailed Workflows

### [1] System Setup & Health Check
*   **Goal:** Ensure the environment is ready and dependencies are met.
*   **Steps:**
    1.  **Dependency Check:** Verify `diffusers`, `torch`, `transformers`, `sentencepiece`, etc.
    2.  **Hardware Audit:**
        *   Detect OS (Mac/Linux/Windows).
        *   Detect GPU (MPS/CUDA).
        *   *Crucial:* Check RAM amount.
    3.  **Optimization Recommendation:**
        *   *If Mac < 64GB RAM:* Recommend **Flux Dev (Quantized/MFLUX)**.
        *   *If High VRAM/RAM:* Recommend Standard Flux Dev.
    4.  **Hugging Face Auth:** Check if user is logged in via `huggingface-cli` (needed for restricted models like Flux Dev).

### [2] Manage Models
*   **Goal:** simplify the complex landscape of Flux versions (Dev, Schnell, Quantized).
*   **Interaction:**
    ```text
    ? Which model configuration would you like to set up?
      > Flux Dev [Standard] (High Quality, requires ~30GB+ VRAM/RAM, slow on Mac)
      > Flux Dev [Quantized 4-bit] (High Quality, Fast, Recommended for Mac 16GB-36GB)
      > Flux Schnell (Lower Quality, Very Fast)
    ```
*   **Action:**
    *   Check if model exists in `models/`.
    *   If not, trigger download script (using `huggingface_hub`).
    *   Update `config/config.json` with the selected "Active Model".

### [3] Generate Training Images
*   **Goal:** Create a dataset for LoRA training.
*   **Workflow:**
    1.  **Theme Selection:**
        ```text
        ? Load a saved Theme/Preset?
          > No, create new
          > Viking Gorilla (saved)
          > Cyberpunk Cat (saved)
        ```
    2.  **Configuration (if new):**
        *   `Subject Name` (e.g., "gorilla"):
        *   `Trigger Word` (e.g., "viking"):
        *   `Concept/Prompt` (allows loading from `prompts/*.txt` or manual entry).
        *   `Number of Images` (default: 20).
        *   `Aspect Ratio`: [1:1, Portrait, Landscape].
    3.  **Review & Run:**
        *   Display summary: "Generating 20 images of 'gorilla' using [Flux Dev 4-bit]..."
        *   **Save Theme?** "Would you like to save these settings as a theme?" -> Enter name.
    4.  **Execution:**
        *   Show progress bar.
        *   Save images to `assets/training_data/{date}_{theme}/`.

### [4] Settings
*   Toggle "Safe Mode" (NSFW filter).
*   Set default Output Directory.
*   Set default Step Count (Quality vs Speed).

## 4. Configuration Storage (`config/config.json`)
We will expand the existing config to store themes and preferences.

```json
{
  "system": {
    "default_model": "flux-dev-quantized",
    "use_cpu_offload": true
  },
  "themes": {
    "viking_gorilla": {
      "prompt_file": "prompts/viking.gorilla.txt",
      "trigger": "viking",
      "count": 50
    }
  }
}
```

## 5. Technical Stack for CLI
*   **`rich`**: For beautiful terminal output (tables, panels, progress bars).
*   **`inquirer`** or **`questionary`**: For interactive menus and selection lists.
*   **`typer`** or **`argparse`**: For handling the underlying command routing.
