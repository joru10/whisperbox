# scripts/copy_to_clipboard.py

import pyperclip


def run_action(artifact, action_config):
    print("=== Copy to Clipboard Action ===")
    pyperclip.copy(artifact)
    print("Content copied to clipboard!")
