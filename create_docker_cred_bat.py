
#!/usr/bin/env python3
"""Fix Docker credential helper error."""

import json
import os

# Fix 1: Create docker-credential-desktop.bat
docker_dir = r"C:\Users\USER\AppData\Local\Programs\DockerDesktop\resources\bin"
cred_path = os.path.join(docker_dir, "docker-credential-desktop.exe")

# Check if credential helper exists
if os.path.exists(cred_path):
    with open("docker-credential-desktop.bat", "w") as f:
        f.write(f'@echo off\n"{cred_path}" %*\n')
    print("docker-credential-desktop.bat created!")
else:
    print(f"Credential helper not found at {cred_path}")
    print("Checking for alternatives...")
    for fname in os.listdir(docker_dir):
        if "credential" in fname.lower():
            print(f"  Found: {fname}")

# Fix 2: Update Docker config to not use credential helper
config_dir = os.path.expanduser("~/.docker")
config_file = os.path.join(config_dir, "config.json")

os.makedirs(config_dir, exist_ok=True)

if os.path.exists(config_file):
    with open(config_file, "r") as f:
        config = json.load(f)
else:
    config = {}

# Remove the credential store requirement
if "credsStore" in config:
    del config["credsStore"]
    print("Removed credsStore from Docker config")

with open(config_file, "w") as f:
    json.dump(config, f, indent=2)

print("Docker config updated!")
print("\nNow run: docker compose up -d --build")

