import glob
import json
import os
import subprocess
import zipfile
from typing import Dict, Any
from rich.panel import Panel
from .base import BaseTrainingEngine
from directors_chair.config.loader import load_config

class MFluxEngine(BaseTrainingEngine):
    def train(self, 
              dataset_path: str, 
              output_name: str, 
              trigger_word: str, 
              steps: int, 
              rank: int,
              model_id: str,
              base_model_type: str) -> bool:
        
        from directors_chair.cli.utils import console

        # 0. Ensure Absolute Paths
        dataset_path = os.path.abspath(dataset_path)
        
        # 1. Setup Paths
        # We need a temporary directory for the config and to tell mflux where to save
        # Since we are in a monorepo structure, let's keep build artifacts in 'build/'
        work_dir = os.path.abspath(os.getcwd())
        output_dir = os.path.join(work_dir, "assets", "loras")
        temp_config_path = os.path.join(dataset_path, "train_config.json")
        
        # Ensure output dir exists
        os.makedirs(output_dir, exist_ok=True)

        # Resolve Model Path (Local vs HF Cache)
        # We need to map the passed 'model_id' (which is a repo ID) to our local key if possible.
        # This is tricky because we pass the ID, not the key.
        # Let's check config to find the key associated with this ID.
        app_config = load_config()
        final_model_path = model_id # Default to HF Repo ID
        
        for key, val in app_config.get("model_ids", {}).items():
            if val == model_id:
                # Found the key (e.g. "flux-schnell")
                local_candidate = os.path.join(app_config["directories"]["models"], key)
                if os.path.exists(local_candidate) and len(os.listdir(local_candidate)) > 0:
                    final_model_path = os.path.abspath(local_candidate)
                    console.print(f"[cyan]Using local model at: {final_model_path}[/cyan]")
                break

        # 2. Construct the MFlux Config
        # This structure mirrors the JSON schema expected by mflux-train
        config = {
            "model": final_model_path,
            "seed": 42,
            "steps": 20, # Denoising steps for validation image generation (not training)
            "guidance": 3.5,
            "quantize": 4, # 4-bit quantization for M3 memory constraints
            "width": 512,  # Standard flux resolution base
            "height": 512,
            "training_loop": {
                "num_epochs": steps, # MFlux often treats this as steps or epochs depending on version
                                     # Let's assume 'steps' passed in is actually epochs for simplicity 
                                     # or strictly steps. MFlux docs say 'num_epochs'. 
                "batch_size": 1
            },
            "optimizer": {
                "name": "AdamW",
                "learning_rate": 1e-4
            },
            "save": {
                "output_path": output_dir,
                "checkpoint_frequency": max(steps // 4, 1),
                "adapter_path": os.path.join(output_dir, f"{output_name}.safetensors")
            },
            "instrumentation": {
                "plot_frequency": 10,
                "generate_image_frequency": max(steps // 5, 1),
                "validation_prompt": f"{trigger_word} {output_name}"
            },
            "lora_layers": {
                "single_transformer_blocks": {
                    "block_range": {
                        "start": 0,
                        "end": 38
                    },
                    "layer_types": [
                        "attn.to_q", "attn.to_k", "attn.to_v"
                    ],
                    "lora_rank": rank
                }
            },
            "examples": {
                 "path": dataset_path,
                 # We don't list explicit images; mflux typically scans the folder
                 # if we provide the path. But the config example showed a list.
                 # Let's auto-generate the list from the folder.
                 "images": self._generate_image_list(dataset_path, trigger_word)
            }
        }

        # 3. Write Config File
        console.print(f"[grey]Writing config to {temp_config_path}...[/grey]")
        with open(temp_config_path, "w") as f:
            json.dump(config, f, indent=4)

        # 4. Run Training Command
        cmd = [
            "venv/bin/mflux-train",
            "--train-config", temp_config_path,
            "--model", final_model_path,
            "--base-model", base_model_type,
            "--quantize", "4",
            "--low-ram"
        ]

        console.print(Panel(
            f"[bold]Starting MFlux Training[/bold]\n"
            f"Target: {output_name}\n"
            f"Rank: {rank}\n"
            f"Steps/Epochs: {steps}\n"
            f"Checkpoints every {max(steps // 4, 1)} epochs\n"
            f"Validation images every {max(steps // 5, 1)} epochs\n"
            f"Loss plot: {output_dir}/loss.png",
            border_style="green"
        ))
        
        try:
            console.print("[cyan]mflux will show two progress bars:[/cyan]")
            console.print("[cyan]  1. Encoding dataset[/cyan]")
            console.print("[cyan]  2. Training epochs[/cyan]")
            console.print("[cyan]After the bars complete, saving checkpoints + validation images may take a minute.[/cyan]\n")
            subprocess.check_call(cmd)

            # mflux saves checkpoints as zips in a timestamped subdirectory.
            # Find the final checkpoint and extract the adapter safetensors.
            adapter_path = self._extract_adapter(output_dir, output_name, steps)

            console.print(f"\n[bold green]✓ Training Complete![/bold green]")
            if adapter_path:
                console.print(f"LoRA saved to: {adapter_path}")
            else:
                console.print("[yellow]Warning: Could not find adapter in checkpoints. Check output directory manually.[/yellow]")

            # Cleanup config
            os.remove(temp_config_path)
            return adapter_path is not None

        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]✗ Training Failed[/bold red]")
            console.print(f"Error code: {e.returncode}")
            return False
        except Exception as e:
             console.print(f"[bold red]✗ Unexpected Error: {e}[/bold red]")
             return False

    def _extract_adapter(self, output_dir: str, output_name: str, steps: int) -> str | None:
        """Find the final checkpoint zip mflux created and extract the adapter safetensors."""
        # mflux creates a timestamped dir like assets/loras_YYYYMMDD_HHMMSS/_checkpoints/
        parent = os.path.dirname(output_dir)
        base = os.path.basename(output_dir)
        # Find timestamped dirs matching the base name
        candidates = sorted(glob.glob(os.path.join(parent, f"{base}_*", "_checkpoints")))
        if not candidates:
            # Also check the exact output_dir in case mflux used it directly
            exact = os.path.join(output_dir, "_checkpoints")
            if os.path.isdir(exact):
                candidates = [exact]

        if not candidates:
            return None

        checkpoint_dir = candidates[-1]  # Most recent
        # Find the highest-numbered checkpoint zip
        zips = sorted(glob.glob(os.path.join(checkpoint_dir, "*_checkpoint.zip")))
        if not zips:
            return None

        final_zip = zips[-1]
        console.print(f"[cyan]Extracting adapter from {os.path.basename(final_zip)}...[/cyan]")

        adapter_dest = os.path.join(output_dir, f"{output_name}.safetensors")
        with zipfile.ZipFile(final_zip, 'r') as zf:
            # Find the adapter file inside the zip
            adapter_names = [n for n in zf.namelist() if n.endswith("_adapter.safetensors")]
            if not adapter_names:
                return None
            with zf.open(adapter_names[0]) as src, open(adapter_dest, 'wb') as dst:
                dst.write(src.read())

        return adapter_dest

    def _generate_image_list(self, dataset_path: str, trigger_word: str):
        """Scans the folder and creates the list of image/prompt pairs."""
        images = []
        for filename in sorted(os.listdir(dataset_path)):
            if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                # Look for companion text file
                base_name = os.path.splitext(filename)[0]
                txt_path = os.path.join(dataset_path, f"{base_name}.txt")
                
                prompt = trigger_word # Fallback
                if os.path.exists(txt_path):
                    with open(txt_path, 'r') as f:
                        prompt = f.read().strip()
                
                images.append({
                    "image": filename,
                    "prompt": prompt
                })
        return images
