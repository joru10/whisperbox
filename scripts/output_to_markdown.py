# scripts/output_to_markdown.py

import os


def run_action(artifact, action_config):
    print("=== Markdown Output Action ===")

    # Get session directory from config, fallback to current directory
    session_dir = action_config.get("session_dir", ".")
    filename = action_config.get("filename", "output.md")

    # Create full file path in session directory
    file_path = os.path.join(session_dir, filename)

    # Write content to markdown file
    with open(file_path, "w") as f:
        f.write(artifact)

    print(f"Content written to {file_path}")
