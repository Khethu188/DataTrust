
#!/usr/bin/env python3
"""Add Docker to Windows PATH permanently."""

import subprocess
import winreg

docker_path = r"C:\Users\USER\AppData\Local\Programs\DockerDesktop\resources\bin"

# Read current user PATH
key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_ALL_ACCESS)
try:
    current_path, _ = winreg.QueryValueEx(key, "Path")
except FileNotFoundError:
    current_path = ""

# Check if already added
if docker_path.lower() not in current_path.lower():
    new_path = current_path.rstrip(";") + ";" + docker_path
    winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
    print(f"Docker path added successfully!")
    print(f"Added: {docker_path}")
else:
    print("Docker path already exists in PATH.")

winreg.CloseKey(key)

# Notify Windows of the change
subprocess.run(
    ['powershell', '-Command',
     '[Environment]::SetEnvironmentVariable("Path",[Environment]::GetEnvironmentVariable("Path","User"),"User")'],
    capture_output=True
)

print("\nClose this Command Prompt and open a NEW one, then run:")
print("  docker --version")

