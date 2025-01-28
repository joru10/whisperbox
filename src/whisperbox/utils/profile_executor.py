# src/utils/profile_executor.py
import os
import importlib.util
from ..utils.utils import get_app_dir


def run_profile_actions(profile_data, processed_text):
    """
    Loop through each action in the profile and run it.
    This is reusable in both CLI and GUI flows if needed.
    """
    for action_obj in profile_data["actions"]:
        script_name = action_obj["script"]
        script_config = action_obj.get("config", {})
        run_action_script(script_name, processed_text, script_config)


def run_action_script(script_name: str, artifact: str, action_config: dict):
    """
    Dynamically import a script from the app's scripts directory.
    Expects the script to define 'run_action(artifact, action_config)'.
    """
    scripts_dir = get_app_dir() / "scripts"
    script_path = os.path.join(scripts_dir, f"{script_name}.py")
    if not os.path.isfile(script_path):
        raise FileNotFoundError(f"Action script not found: {script_path}")

    spec = importlib.util.spec_from_file_location(script_name, script_path)
    if spec is None:
        raise ImportError(f"Could not load module spec for {script_path}")
    script_module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise ImportError(f"Could not load module loader for {script_path}")
    spec.loader.exec_module(script_module)

    if not hasattr(script_module, "run_action"):
        raise AttributeError(
            f"Script '{script_name}' must define a function 'run_action(artifact, action_config)'"
        )

    # Call the user-provided function
    return script_module.run_action(artifact, action_config)
