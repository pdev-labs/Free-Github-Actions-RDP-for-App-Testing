import json
import os
import yaml
from InquirerPy import inquirer
from InquirerPy.base.control import Choice

CONFIG_FILE = "config.yaml"

def load_profile():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                profiles = yaml.safe_load(f)
                if not profiles:
                    profiles = {}
        except Exception:
            profiles = {}
        
        if profiles:
            choices = [Choice("new", "🚀 Create New Environment")] + [Choice(k, f"⚡ Quick Boot: {k}") for k in profiles.keys()]
            choice = inquirer.select(
                message="Load a saved profile or create a new one?",
                choices=choices
            ).execute()
            
            if choice != "new":
                return profiles[choice]
    return None

def save_profile(data):
    profiles = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                profiles = yaml.safe_load(f)
                if not profiles:
                    profiles = {}
        except Exception:
            profiles = {}
    
    name = inquirer.text(
        message="Enter a name to save this configuration (or press Enter to skip):"
    ).execute().strip()
    
    if name:
        profiles[name] = data
        with open(CONFIG_FILE, "w") as f:
            yaml.dump(profiles, f, default_flow_style=False)
        print(f"[+] Profile '{name}' saved successfully in {CONFIG_FILE}!")
