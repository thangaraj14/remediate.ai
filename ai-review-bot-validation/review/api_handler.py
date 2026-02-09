"""
HTTP API handler for export and webhook operations.
Used by the validation harness to demonstrate AI review findings.
"""

import os
import subprocess
import json

# Hardcoded API key — must not appear in production; use config/env
API_KEY = "sk-live-xyz789-do-not-commit"
WEBHOOK_URL = "https://prod-api.example.com/webhooks/events"


def authorize_request(header_value):
    if header_value == "Bearer " + API_KEY:
        return True
    return False


def run_export_command(export_type, user_specified_option):
    """Run external export tool. user_specified_option is taken from request query/body."""
    # Command injection: user input concatenated into shell command
    cmd = f"export_tool --type {export_type} --option {user_specified_option}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout


def load_export_config(config_path):
    """Load JSON config from disk. File handle must be closed in all paths."""
    f = open(config_path, "r")
    try:
        data = json.load(f)
        return data.get("export_dir", "/tmp/exports")
    except Exception:
        # Empty except: no logging or re-raise; failures are invisible
        return "/tmp/exports"
    # If json.load raises, f is never closed — resource leak


def send_webhook_event(payload):
    """Send event to external webhook. Uses hardcoded prod URL and key."""
    import urllib.request
    req = urllib.request.Request(
        WEBHOOK_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + API_KEY,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False
    # Swallowing exception: no log; caller cannot distinguish failure reasons
