# Downloading & Caching ZImageTurbo Models

## Current State: `model_manager.py`
The current `model_manager.py` contains a `download_model` function that uses `huggingface_hub.snapshot_download`. 

```python
def download_model(repo_id: str, local_dir: str):
    snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir,
        local_dir_use_symlinks=False, 
        resume_download=True
    )
```

**Key behavior:**
- It downloads the *entire* repository.
- It forces a specific `local_dir`.
- It disables symlinks (`local_dir_use_symlinks=False`), creating a self-contained copy.

## The Challenge with `mflux` / `ZImageTurbo`
`mflux` (and specifically `ZImageTurbo`) uses a `PathResolution` system that looks for models in this order:
1. **Local Path:** If you provide a direct path to a directory.
2. **Hugging Face Cache:** If you provide a repo ID (e.g., `mflux/z-image-turbo`), it looks in the standard `~/.cache/huggingface/hub/...`.

The "4 files downloading" issue occurs because `mflux`'s `TokenizerLoader` or `PathResolution` might not be finding the tokenizer files in the expected structure if we rely on partial downloads or if the cache lookup fails, triggering a fresh check/download.

## Proposed Strategy for Pre-Caching

To support pre-downloading `ZImageTurbo` models effectively so they are "just ready" when the generator starts:

1.  **Leverage HF Global Cache (Preferred for `mflux`):**
    Instead of downloading to a custom `./models/z-image-turbo` directory (which requires us to explicitly pass that path to the generator every time), we can just download into the standard Hugging Face cache.
    
    *How:* Call `snapshot_download(repo_id=...)` *without* `local_dir`.
    
    *Benefit:* `ZImageTurbo(model_name="mflux/z-image-turbo")` will automatically find it via `PathResolution` (Rule #2 `hf_cached`) without us needing to manage paths manually.

2.  **Explicit Local Path (Current `director's chair` style):**
    If we want to keep models in `./models/`, we must ensure we pass this exact path to the `ZImageTurbo` constructor.
    
    *Requirement:* We need to update `manage_models` to:
    - Allow downloading specifically for `ZImageTurbo` (which might need specific include/exclude patterns if we don't want the whole repo).
    - Or, simply download the full repo to `./models/z-image-turbo`.
    
    *Integration:* In `ZImageTurboGenerator`, we would then need to check if `./models/z-image-turbo` exists and pass `model_path="./models/z-image-turbo"` to the constructor.

## Recommendation for `manage_models`

Modify `manage_models` to support a "Cache Mode":

1.  **Add a "Pre-cache to System" option:**
    This uses `snapshot_download` to the default HF cache. This is the most compatible way with `mflux` as it is currently written.
    
    ```python
    # Pseudo-code for caching
    snapshot_download(repo_id="mflux/z-image-turbo", repo_type="model")
    ```

2.  **Filter Downloads (Optional but good):**
    `ZImageTurbo` only needs specific files (weights, config, tokenizer). We could optimize by using `allow_patterns` similar to what `ZImageWeightDefinition.get_download_patterns()` defines:
    - `vae/*.safetensors`
    - `transformer/*.safetensors`
    - `text_encoder/*.safetensors`
    - `tokenizer/*`
    - `*.json`

    This would save bandwidth compared to downloading full repos that might contain non-essential data.

## Summary
The "downloading 4 files" likely happens because the `TokenizerLoader` in `mflux` checks for specific files. If we pre-download the model into the system cache (or a known local path passed explicitly), `mflux` will find them and skip the network call.
