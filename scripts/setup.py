import subprocess
import os
import sys

os.chdir("/vercel/share/v0-project")

print("Current directory:", os.getcwd())
print("Files:", os.listdir("."))

# Check if npm/pnpm are available
for cmd in ["pnpm", "npm", "npx", "node"]:
    try:
        result = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=10)
        print(f"{cmd}: {result.stdout.strip()}")
    except FileNotFoundError:
        print(f"{cmd}: NOT FOUND")
    except Exception as e:
        print(f"{cmd}: ERROR - {e}")

# Try to find node
import shutil
for name in ["node", "pnpm", "npm"]:
    path = shutil.which(name)
    print(f"which {name}: {path}")

# Check PATH
print("PATH:", os.environ.get("PATH", "N/A"))
