from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LoopConfig:
    opencode_executable: str = "opencode"
    project_dir: str = "."
    state_path: str = ".opencode/loop/state.md"
    runs_dir: str = ".opencode/loop/runs"
    default_max_iterations: int = 20
    default_sleep_seconds: float = 1.0
    default_output_format: str = "default"
    default_model: str | None = None
    default_agent: str | None = None
    default_attach_url: str | None = None
    dangerously_skip_permissions: bool = False


def load_config(path: Path | None) -> LoopConfig:
    if path is None or not path.exists():
        return LoopConfig()

    with path.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    if not isinstance(raw, dict):
        raise ValueError(f"Config must be a JSON object: {path}")

    allowed = set(LoopConfig.__dataclass_fields__)
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"Unknown config keys in {path}: {', '.join(unknown)}")

    return LoopConfig(**{key: value for key, value in raw.items() if value is not None})


def first_existing_config(candidates: list[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def merge_value(cli_value: Any, config_value: Any) -> Any:
    return config_value if cli_value is None else cli_value
