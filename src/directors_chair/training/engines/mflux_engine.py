import json
import os
import subprocess
import shutil
from typing import Dict, Any
from mflux.models.common.config.model_config import ModelConfig
from rich.panel import Panel
from .base import BaseTrainingEngine
from directors_chair.cli.utils import console
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
            "steps": 1000, # Default max, we control via 'training_loop' usually, but mflux might differ.
                           # Actually, mflux config usually uses 'training_loop' or top level keys.
                           # Based on search results, let's try a standard structure.
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
                "learning_rate": 4e-4 # Standard for LoRA
            },
            "save": {
                "output_path": output_dir,
                "checkpoint_frequency": 1000, # Don't spam checkpoints
                "adapter_path": os.path.join(output_dir, f"{output_name}.safetensors")
            },
            "lora_layers": {
                "single_transformer_blocks": {
                    "block_range": {
                        "start": 0,
                        "end": 38 # Full range
                    },
                    "layer_types": [
                        "proj_out", "proj_mlp", "attn.to_q", "attn.to_k", "attn.to_v"
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

        console.print(Panel(f"[bold]Starting MFlux Training[/bold]\nTarget: {output_name}\nRank: {rank}\nSteps/Epochs: {steps}", border_style="green"))
        
        try:
            # Run properly, streaming output to console would be ideal, 
            # but for now let's just run it and show the result.
            # We use check_call to raise error if it fails.
            subprocess.check_call(cmd)
            
            console.print(f"[bold green]✓ Training Complete![/bold green]")
            console.print(f"LoRA saved to: {config['save']['adapter_path']}")
            
            # Cleanup config
            os.remove(temp_config_path)
            return True
            
        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]✗ Training Failed[/bold red]")
            console.print(f"Error code: {e.returncode}")
            return False
        except Exception as e:
             console.print(f"[bold red]✗ Unexpected Error: {e}[/bold red]")
             return False

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
