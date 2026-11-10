#!/usr/bin/env python3
"""Bootstrap and launch the local ORCHESTRA command center.

Usage:
  python3 setup.py              # install prerequisites/dependencies and launch
  python3 setup.py --check      # validate local prerequisites only
  python3 setup.py --no-install # launch without installing dependencies
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
BACKEND = ROOT / "backend"
VENV = ROOT / ".venv"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"


def run(command: list[str], *, cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess:
    print("+", " ".join(command), flush=True)
    return subprocess.run(command, cwd=cwd, check=check)


def executable(name: str) -> str | None:
    return shutil.which(name)


def detect_claude() -> str | None:
    configured = os.environ.get("CLAUDE_CLI_PATH", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate.resolve())
        found = shutil.which(configured)
        if found:
            return str(Path(found).resolve())
    found = shutil.which("claude")
    if found:
        return str(Path(found).resolve())
    home = Path.home()
    candidates = [home / ".local/bin/claude", home / ".claude/local/claude",
                  home / ".npm-global/bin/claude", Path("/opt/homebrew/bin/claude"),
                  Path("/usr/local/bin/claude")]
    nvm = home / ".nvm/versions/node"
    if nvm.is_dir():
        candidates.extend(nvm.glob("*/bin/claude"))
    for path in candidates:
        if path.is_file() and os.access(path, os.X_OK):
            return str(path.resolve())
    return None


def check_prerequisites() -> None:
    if sys.version_info < (3, 10):
        raise SystemExit("ORCHESTRA requires Python 3.10 or newer.")
    if not executable("node") or not executable("npm"):
        raise SystemExit("Node.js 20+ and npm are required. Install from https://nodejs.org/")
    node = subprocess.check_output(["node", "--version"], text=True).strip().lstrip("v")
    major = int(node.split(".")[0])
    if major < 20:
        raise SystemExit(f"Node.js 20+ is required; found {node}.")
    print(f"✓ Python {sys.version.split()[0]} | Node {node} | npm {subprocess.check_output(['npm','--version'], text=True).strip()}")


def prepare_environment() -> None:
    if not ENV_FILE.exists():
        if ENV_EXAMPLE.exists():
            shutil.copyfile(ENV_EXAMPLE, ENV_FILE)
            print("✓ Created .env from .env.example — review it before using integrations.")
    if not VENV.exists():
        run([sys.executable, "-m", "venv", str(VENV)])
    python = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    run([str(python), "-m", "pip", "install", "--upgrade", "pip"])
    run([str(python), "-m", "pip", "install", "-r", str(BACKEND / "requirements.txt")])
    if not (FRONTEND / "node_modules").exists():
        run(["npm", "install"], cwd=FRONTEND)
    else:
        print("✓ Frontend dependencies already installed")


def launch() -> None:
    python = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    env = os.environ.copy()
    env["ORCHESTRA_ENV_FILE"] = str(ENV_FILE)
    claude = detect_claude()
    if claude:
        env["CLAUDE_CLI_PATH"] = claude
    backend = subprocess.Popen(
        [str(python), "-m", "uvicorn", "orchestra_api.main:app", "--host", "127.0.0.1",
         "--port", env.get("ORCHESTRA_API_PORT", "8787"), "--reload"],
        cwd=BACKEND, env=env,
    )
    frontend = subprocess.Popen(
        ["npm", "run", "dev", "--", "--hostname", "127.0.0.1",
         "--port", env.get("ORCHESTRA_WEB_PORT", "3000")],
        cwd=FRONTEND, env=env,
    )
    url = f"http://127.0.0.1:{env.get('ORCHESTRA_WEB_PORT', '3000')}"
    print("\nORCHESTRA is starting.")
    print(f"Website: {url}")
    print(f"API:     http://127.0.0.1:{env.get('ORCHESTRA_API_PORT', '8787')}/docs")
    print("Press Ctrl+C to stop both services. Data stays in backend/data/.\n")
    time.sleep(2)
    if env.get("ORCHESTRA_OPEN_BROWSER", "true").lower() == "true":
        webbrowser.open(url)
    try:
        while backend.poll() is None and frontend.poll() is None:
            time.sleep(1)
        if backend.poll() is not None:
            raise RuntimeError(f"Backend exited with code {backend.returncode}")
        if frontend.poll() is not None:
            raise RuntimeError(f"Frontend exited with code {frontend.returncode}")
    except KeyboardInterrupt:
        print("\nStopping ORCHESTRA...")
    finally:
        for process in (frontend, backend):
            if process.poll() is None:
                process.terminate()
        for process in (frontend, backend):
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()


def main() -> None:
    parser = argparse.ArgumentParser(description="Set up and launch ORCHESTRA locally")
    parser.add_argument("--check", action="store_true", help="only check prerequisites")
    parser.add_argument("--no-install", action="store_true", help="skip dependency installation")
    args = parser.parse_args()
    check_prerequisites()
    if args.check:
        return
    if not args.no_install:
        prepare_environment()
    elif not VENV.exists():
        raise SystemExit("Missing .venv. Run without --no-install once to install dependencies.")
    launch()


if __name__ == "__main__":
    main()
