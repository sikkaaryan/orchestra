from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    project_path: Path | None
    game_spec_path: Path | None
    claude_cli_path: str
    claude_model: str
    max_concurrent_agents: int
    permission_mode: str
    require_approval_for_commands: bool
    allow_destructive_commands: bool
    max_retries: int
    task_timeout_seconds: int
    github_token: str
    github_repository: str


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


def _path(name: str) -> Path | None:
    value = os.getenv(name, "").strip()
    return Path(value).expanduser().resolve() if value else None


def resolve_claude_cli(configured: str | None = None) -> str | None:
    """Find Claude Code on PATH or in common macOS install locations."""
    candidate = (configured or os.getenv("CLAUDE_CLI_PATH", "claude")).strip() or "claude"
    found = shutil.which(candidate)
    if found:
        return str(Path(found).expanduser().resolve())
    explicit = Path(candidate).expanduser()
    if explicit.is_file() and os.access(explicit, os.X_OK):
        return str(explicit.resolve())
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


def load_settings() -> Settings:
    env_file = Path(os.getenv("ORCHESTRA_ENV_FILE", Path(__file__).resolve().parents[1] / ".env"))
    if load_dotenv:
        load_dotenv(env_file, override=False)
    data_dir = Path(os.getenv("ORCHESTRA_DATA_DIR", Path(__file__).resolve().parents[1] / "data")).expanduser()
    return Settings(
        data_dir=data_dir.resolve(),
        project_path=_path("ORCHESTRA_PROJECT_PATH"),
        game_spec_path=_path("ORCHESTRA_GAME_SPEC_PATH"),
        claude_cli_path=os.getenv("CLAUDE_CLI_PATH", "claude").strip() or "claude",
        claude_model=os.getenv("CLAUDE_MODEL", "").strip(),
        max_concurrent_agents=max(1, min(16, int(os.getenv("CLAUDE_MAX_CONCURRENT_AGENTS", "4")))),
        permission_mode=os.getenv("CLAUDE_PERMISSION_MODE", "default").strip(),
        require_approval_for_commands=_bool("ORCHESTRA_REQUIRE_APPROVAL_FOR_COMMANDS", True),
        allow_destructive_commands=_bool("ORCHESTRA_ALLOW_DESTRUCTIVE_COMMANDS", False),
        max_retries=max(0, int(os.getenv("ORCHESTRA_MAX_RETRIES", "2"))),
        task_timeout_seconds=max(60, int(os.getenv("ORCHESTRA_TASK_TIMEOUT_SECONDS", "3600"))),
        github_token=os.getenv("GITHUB_TOKEN", ""),
        github_repository=os.getenv("GITHUB_REPOSITORY", ""),
    )


settings = load_settings()
