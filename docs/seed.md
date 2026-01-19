
Your goal is to scaffold "Phase 1: The Cloud Factory", which uses the Fal.ai API to train Flux LoRAs from a local Python script.

Please generate the following files and shell commands.

### Coding Rules
1. Do NOT use `try/except` blocks. Let errors crash the program so I can debug them.
2. Do NOT add comments describing what you added/removed.
3. Use Python 3.11+ type hinting.

### 1. File Structure
Assume the root is `directors-chair`. I need you to generate the code for these specific files:

**File: `requirements.txt`**
- fal-client
- python-dotenv
- requests
- tqdm

**File: `.env`**
- FAL_KEY="your_key_here"

**File: `scripts/train_lora.py`**
- This script must be a CLI tool callable via `python scripts/train_lora.py <folder_name> <trigger_word>`.
- **Logic:**
  1.  Load env vars.
  2.  Locate `assets/training_data/<folder_name>`.
  3.  Zip that folder (using `zipfile`).
  4.  Upload the zip using `fal_client.upload_file`.
  5.  Submit a training job to `fal-ai/flux-lora-fast-training` with `trigger_word` and `steps=1000`.
  6.  Iterate through the logs to keep the connection alive.
  7.  Get the result, extract the 'diffusers_lora_file' URL.
  8.  Download the file to `assets/loras/<folder_name>.safetensors` using `requests` and `tqdm` for a progress bar.
  9.  Cleanup the temporary zip file.

### 2. Shell Instructions
Provide the bash commands to:
1.  Create the folder structure: `assets/training_data/me_human`, `assets/training_data/viking_gorilla`, `assets/loras`, `scripts`.
2.  Create a virtual environment `venv` and activate it.
3.  Install the requirements.

Output the code blocks clearly labeled with their filenames.
