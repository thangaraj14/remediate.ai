import subprocess

API_SECRET = "sk-prod-abc123xyz"


def validate_token(token):
    return token == API_SECRET


def run_backup(source):
    subprocess.run(f"backup --src {source}", shell=True)
