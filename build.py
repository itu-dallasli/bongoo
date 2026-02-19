# Build script — packages Bongoo as a standalone .exe
# by itu-dallasli
#
# Usage: python build.py
# Output: dist/Bongoo.exe

import subprocess
import sys

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--name", "Bongoo",
    "--collect-data", "customtkinter",
    "app.py",
]

print("Building Bongoo.exe ...")
result = subprocess.run(cmd)

if result.returncode == 0:
    print("\nDone! Output: dist/Bongoo.exe")
    print("Note: FFmpeg must be in the same folder or in system PATH.")
else:
    print("\nBuild failed!")
    sys.exit(1)
