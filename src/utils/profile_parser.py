# src/utils/profile_parser.py

import os
import yaml


def load_profile_yaml(profile_name: str):
    """
    Load the YAML profile from 'profiles/<profile_name>.yaml'.
    Returns a dict with keys: name, prompt, actions, etc.
    Raises ValueError if required fields are missing or invalid.
    """
    profile_path = os.path.join("profiles", f"{profile_name}.yaml")
    if not os.path.isfile(profile_path):
        raise FileNotFoundError(f"Profile file not found: {profile_path}")

    with open(profile_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Required field validation
    if not isinstance(data, dict):
        raise ValueError("Profile YAML must be a dictionary")

    required_fields = ["prompt"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Required field '{field}' missing in profile")

    # Optional defaults / validation
    data.setdefault("name", profile_name)
    data.setdefault("actions", [])

    if not isinstance(data["actions"], list):
        raise ValueError("'actions' must be a list")

    for action in data["actions"]:
        if not isinstance(action, dict):
            raise ValueError("Each action must be a dictionary")
        if "script" not in action:
            raise ValueError("Each action must have a 'script' field")
        # Ensure there's a 'config' field even if empty
        action.setdefault("config", {})

    return data
