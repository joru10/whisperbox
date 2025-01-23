# src/utils/profile_parser.py

import os
import yaml
from yaml.scanner import ScannerError
from yaml.parser import ParserError
from ..core.config import config
from ..utils.logger import log
from ..utils.utils import get_profiles_dir


def load_profile_yaml(profile_name: str):
    """
    Load the YAML profile from 'profiles/<profile_name>.yaml'.
    Returns a dict with keys: name, prompt, actions, etc.
    Shows user-friendly error messages for YAML parsing issues.
    """
    profile_path = os.path.join("profiles", f"{profile_name}.yaml")
    if not os.path.isfile(profile_path):
        raise FileNotFoundError(f"Profile file not found: {profile_path}")

    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

    except (ScannerError, ParserError) as e:
        # Get the problematic line number and content if available
        line_num = (e.problem_mark.line + 1) if (hasattr(e, 'problem_mark') and e.problem_mark is not None) else 'unknown'
        
        log.error(f"\nThere's an issue with your profile file: {profile_name}.yaml")
        log.error(f"The YAML syntax is invalid around line {line_num}")
        log.error("\nCommon YAML syntax issues:")
        log.error("1. Incorrect indentation")
        log.error("2. Missing or extra colons (:)")
        log.error("3. Missing quotes around special characters")
        log.error("4. Extra spaces at line endings")
        log.error("\nPlease check your profile YAML file and try again.")
        raise ValueError("Invalid YAML syntax in profile file") from e
        
    except Exception as e:
        log.error(f"\nUnexpected error reading profile: {profile_name}.yaml")
        log.error(f"Error: {str(e)}")
        raise

    # Required field validation
    if not isinstance(data, dict):
        log.error(f"\nProfile {profile_name}.yaml must be a valid YAML document")
        log.error("It should start with fields like 'name:', 'prompt:', etc.")
        raise ValueError("Profile YAML must be a dictionary")

    required_fields = ["prompt"]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        log.error(f"\nProfile {profile_name}.yaml is missing required fields:")
        for field in missing_fields:
            log.error(f"- {field}")
        raise ValueError(f"Required fields missing in profile: {', '.join(missing_fields)}")

    # Optional defaults / validation
    data.setdefault("name", profile_name)
    data.setdefault("actions", [])

    if not isinstance(data["actions"], list):
        log.error(f"\nIn profile {profile_name}.yaml:")
        log.error("The 'actions' field must be a list of action items")
        log.error("Example format:")
        log.error("actions:")
        log.error("  - script: my_script")
        log.error("    config:")
        log.error("      key: value")
        raise ValueError("'actions' must be a list")

    for action in data["actions"]:
        if not isinstance(action, dict):
            log.error(f"\nIn profile {profile_name}.yaml:")
            log.error("Each action must be a dictionary with 'script' and optional 'config'")
            raise ValueError("Each action must be a dictionary")
        if "script" not in action:
            log.error(f"\nIn profile {profile_name}.yaml:")
            log.error("Each action must have a 'script' field specifying what to run")
            raise ValueError("Each action must have a 'script' field")
        # Ensure there's a 'config' field even if empty
        action.setdefault("config", {})

    return data


def get_available_profiles():
    """Return a list of available profile names."""
    profiles_dir = get_profiles_dir()
    if not profiles_dir or not os.path.exists(profiles_dir):
        return []

    profiles = []
    for file in os.listdir(profiles_dir):
        if file.endswith(".yaml") or file.endswith(".yml"):
            profiles.append(os.path.splitext(file)[0])
    return profiles
