from pathlib import Path
import os
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def run_command(command: list[str], cwd: Path) -> int:
    executable = shutil.which(command[0])
    if executable is None and os.name == "nt" and command[0] == "npm":
        executable = shutil.which("npm.cmd")
    if executable is None:
        print(f"Command not found: {command[0]}")
        return 1
    command = [executable, *command[1:]]
    print(f"\n[CampRank] Running in {cwd}: {' '.join(command)}")
    completed = subprocess.run(command, cwd=cwd)
    return completed.returncode


def main() -> int:
    failures = 0

    backend_dir = ROOT / "backend"
    if backend_dir.exists():
        failures += run_command([sys.executable, "-m", "pytest"], backend_dir) != 0
    else:
        print("backend directory not found, skipping backend checks for current stage.")

    frontend_dir = ROOT / "frontend"
    if frontend_dir.exists():
        failures += run_command(["npm", "run", "build"], frontend_dir) != 0
    else:
        print("frontend directory not found, skipping frontend checks for current stage.")

    if failures:
        print("CampRank checks failed.")
        return 1

    print("\nAll CampRank checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
