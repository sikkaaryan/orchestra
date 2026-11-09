from pathlib import Path
import os
import tempfile

from orchestra_api.runtime import AgentRuntime


def test_prompt_contains_scope_and_no_permission_bypass():
    runtime = AgentRuntime()
    prompt = runtime._prompt(
        {"title": "Implement feature", "description": "Add a safe feature"},
        {"name": "Maya", "role": "Developer", "specialization": "UI", "instructions": ""},
        {"name": "Demo", "game_spec_path": None},
    )
    assert "isolated Git worktree" in prompt
    assert "Do not merge, push, release" in prompt


def test_terminal_reader_handles_missing_file(tmp_path, monkeypatch):
    from orchestra_api import runtime as runtime_module
    monkeypatch.setattr(runtime_module.settings, "data_dir", tmp_path, raising=False)
    assert AgentRuntime().terminal("unknown") == []
