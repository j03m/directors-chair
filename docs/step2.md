Here are the consolidated instructions.

```markdown
You are a Senior Python Engineer acting as a project architect for "directors-chair".
I need to refactor the project to follow a `src` layout with strict separation of concerns and config-driven architecture using JSON.

Please generate the code for the following files.

### Coding Rules
1. Do NOT use `try/except` blocks. Let errors crash the program for easier debugging.
2. Do NOT add comments describing what you added/removed.
3. Use Python 3.10+ type hinting.
4. Assume the project root is the working directory.

### 1. Project Structure Rules
- **Non-executable code:** Goes in `src/directors_chair/`.
- **Executable scripts:** Go in `scripts/`.
- **Config file:** Goes in `config/`.
- **Models:** Go in `models/` (ignored by git).

### 2. Git Configuration (`.gitignore`)
Create a `.gitignore` file in the root.
- **Entries:**
  - `models/`
  - `venv/`
  - `__pycache__/`
  - `.env`
  - `*.DS_Store`
  - `assets/generated/`
  - `*.pyc`

### 3. Configuration Data (`config/config.json`)
The actual settings file.
- **Content:**
  ```json
  {
      "directories": {
          "models": "./models",
          "output": "./assets/generated",
          "training_data": "./assets/training_data"
      },
      "model_ids": {
          "flux_dev": "black-forest-labs/FLUX.1-dev",
          "flux_schnell": "black-forest-labs/FLUX.1-schnell"
      }
  }

```

### 4. Configuration Logic (`src/directors_chair/config/loader.py`)

The library code to handle configuration.

* **Libraries:** `json`, `os`.
* **Function `load_config(config_path="config/config.json")`:**
* Opens the file at `config_path`.
* Returns the dictionary.


* **Function `get_prompt(prompt_input)`:**
* If `prompt_input` is a file path (ends in `.txt` and exists), read and return content.
* Otherwise, return `prompt_input`.



### 5. Package Init (`src/directors_chair/config/__init__.py`)

* **Content:**
```python
from .loader import load_config, get_prompt

```



### 6. The Installer (`scripts/setup.py`)

Executable script to cache models.

* **Imports:** Needs to add `../src` to `sys.path` to import `directors_chair.config`.
* **Logic:**
1. Setup path: `sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))`.
2. Import `load_config` from `directors_chair.config`.
3. Load config.
4. Check `HF_TOKEN` env var. Crash if missing.
5. Use `huggingface_hub.snapshot_download`.
6. **Important:** Download to `config['directories']['models']`.
7. Download both Dev and Schnell variants.



### 7. The Generator (`scripts/generate_synthetic_data.py`)

Executable script to create training images.

* **Imports:** Add `../src` to `sys.path`.
* **Logic:**
1. Setup path & imports.
2. Load config.
3. Initialize `FluxPipeline` (Schnell, bfloat16).
4. **Critical:** Pass `cache_dir=config['directories']['models']` to `.from_pretrained`.
5. `pipe.enable_model_cpu_offload()` (for 36GB Mac support).
6. Resolve prompt using `get_prompt`.
7. Loop and save images to `training_data` dir defined in config.



### 8. Shell Instructions

Provide bash commands to:

1. Create the directory tree: `mkdir -p src/directors_chair/config config scripts models assets/training_data`.
2. Touch `src/directors_chair/__init__.py`.
3. Run setup.
4. Run the generator.


