# scripts/output_to_markdown.py

import os
from whisperbox.utils.utils import get_app_dir


def run_action(artifact, action_config):
    print("=== Markdown Output Action ===")

    # Get session directory from config, if not provided use the most recent session directory
    if "session_dir" not in action_config:
        # Find most recent session directory
        data_dir = os.path.join(get_app_dir(), "data")
        sessions = [
            d
            for d in os.listdir(data_dir)
            if os.path.isdir(os.path.join(data_dir, d))
        ]
        if sessions:
            latest_session = max(sessions)  # Gets the most recent timestamp directory
            session_dir = os.path.join(data_dir, latest_session)
        else:
            session_dir = str(get_app_dir())
    else:
        session_dir = action_config["session_dir"]

    filename = action_config.get("filename", "output.md")

    # Create full file path in session directory
    file_path = os.path.join(session_dir, filename)

    # Write content to markdown file
    with open(file_path, "w") as f:
        f.write(artifact)

    print(f"Content written to {file_path}")
