import os
import random
import json
import questionary
from rich.panel import Panel
from directors_chair.config.loader import load_config, save_config, get_prompt
from directors_chair.generation import get_generator
from directors_chair.cli.utils import console

def generate_images():
    config = load_config()
    themes = config.get("themes", {})
    available_generators = list(config.get("model_ids", {}).keys())
    default_generator = config["system"].get("default_generator", "zimage-turbo")
    
    theme_choices = ["Create New Theme"] + list(themes.keys()) + ["Back"]
    
    choice = questionary.select(
        "Select Theme:",
        choices=theme_choices
    ).ask()
    
    if choice == "Back":
        return
        
    name, trigger, prompt_text, count, generator_choice, steps, guidance = "", "", "", 1, default_generator, 25, 3.5
    
    if choice == "Create New Theme":
        name = questionary.text("Character/Subject Name (e.g. 'gorilla'):").ask()
        trigger = questionary.text("Trigger Word (e.g. 'viking'):").ask()
        prompt_text = questionary.text("Prompt Concept:").ask()
        count = int(questionary.text("Number of Images:", default="20").ask())
        
        # Extended Attributes
        generator_choice = questionary.select("Select Generator:", choices=available_generators, default=default_generator).ask()
        steps = int(questionary.text("Steps:", default="25").ask())
        guidance = float(questionary.text("Guidance Scale:", default="3.5").ask())
        
        if questionary.confirm("Save this theme?").ask():
            theme_key = f"{trigger}_{name}".replace(" ", "_")
            config["themes"][theme_key] = {
                "trigger": trigger,
                "prompt_file": prompt_text,
                "count": count,
                "generator": generator_choice,
                "parameters": {
                    "steps": steps,
                    "guidance": guidance
                }
            }
            save_config(config)
            console.print(f"[green]Theme saved as {theme_key}[/green]")
            
    elif choice in themes:
        theme = themes[choice]
        console.print(f"Loaded Theme: [cyan]{choice}[/cyan]")
        name = choice.split("_")[-1] # simplistic
        trigger = theme["trigger"]
        prompt_text = get_prompt(theme["prompt_file"])
        count = theme.get("count", 20)
        generator_choice = theme.get("generator", default_generator)
        
        params = theme.get("parameters", {})
        steps = params.get("steps", 25)
        guidance = params.get("guidance", 3.5)
        
        console.print(f"Generator: {generator_choice} | Steps: {steps} | Guidance: {guidance}")
        
        # Display the full prompt construction so the user understands
        full_prompt_preview = f"{trigger} {name}, {prompt_text}"
        console.print(Panel(f"[bold]Effective Prompt:[/bold]\n{full_prompt_preview}", title="Prompt Preview", border_style="cyan"))

        # Allow override
        if not questionary.confirm(f"Generate {count} images with these settings?").ask():
             if questionary.confirm("Change settings?").ask():
                prompt_text = questionary.text("Prompt Concept:", default=prompt_text).ask()
                count = int(questionary.text("Number of Images:", default=str(count)).ask())
                generator_choice = questionary.select("Select Generator:", choices=available_generators, default=generator_choice).ask()
                steps = int(questionary.text("Steps:", default=str(steps)).ask())

    # Execution
    console.print(f"\n[bold]Plan:[/bold] Generate {count} images for '{name}' using {generator_choice}.")
    if questionary.confirm("Start Generation?").ask():
         output_dir = os.path.join(config["directories"]["training_data"], f"{trigger}_{name}")
         if not os.path.exists(output_dir):
             os.makedirs(output_dir)

         # Construct full prompt
         full_prompt = f"{trigger} {name}, {prompt_text}"

         # Instantiate Generator
         generator = get_generator(generator_choice)
         
         for i in range(count):
            current_seed = random.randint(0, 2**32 - 1)
            image = generator.generate(prompt=full_prompt, steps=steps, seed=current_seed)
            
            base_filename = os.path.join(output_dir, f"{name}-{i}")
            
            # Save Image
            image.save(f"{base_filename}.png")
            
            # Save Caption (Required for Training)
            with open(f"{base_filename}.txt", "w") as f:
                f.write(full_prompt)
                
            # Save Metadata (For Reproducibility)
            metadata = {
                "prompt": full_prompt,
                "seed": current_seed,
                "steps": steps,
                "guidance": guidance,
                "generator": generator_choice,
                "model_path": getattr(generator, "model_path", "unknown") 
            }
            with open(f"{base_filename}.json", "w") as f:
                json.dump(metadata, f, indent=4)

         console.print("[bold green]Generation Complete![/bold green]")
         console.print(f"Images saved to: {output_dir}")
         input("\nPress Enter to continue...")
