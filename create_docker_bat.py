
#!/usr/bin/env python3
"""Create docker.bat so Docker works from any Command Prompt."""

docker_path = r"C:\Users\USER\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"

with open("docker.bat", "w") as f:
    f.write(f'@echo off\n"{docker_path}" %*\n')

print("docker.bat created!")
print("Now run: docker --version")

