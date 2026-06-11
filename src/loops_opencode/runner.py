from __future__ import annotations

import datetime as dt
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


STATUS_RE = re.compile(r"^\s*(?:[-*]\s*)?(?:`?status`?\s*:|status\s*:)\s*`?([a-zA-Z_-]+)`?", re.MULTILINE)


@dataclass(frozen=True)
class LoopSelection:
    mcps: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    no_mcp: bool = False
    no_skills: bool = False


@dataclass(frozen=True)
class RunnerOptions:
    objective: str
    resume: bool
    max_iterations: int
    sleep_seconds: float
    opencode_executable: str
    project_dir: Path
    state_path: Path
    runs_dir: Path
    output_format: str
    model: str | None
    agent: str | None
    attach_url: str | None
    dangerously_skip_permissions: bool
    dry_run: bool
    selection: LoopSelection


def read_status(state_path: Path) -> str | None:
    if not state_path.exists():
        return None
    text = state_path.read_text(encoding="utf-8", errors="replace")
    match = STATUS_RE.search(text)
    return match.group(1).lower() if match else None


def split_csv(values: list[str]) -> tuple[str, ...]:
    items: list[str] = []
    for value in values:
        items.extend(part.strip() for part in value.split(","))
    return tuple(item for item in items if item)


def build_loop_args(options: RunnerOptions, resume: bool) -> str:
    lines = ["[loop-control]"]
    lines.append(f"mode: {'continue' if resume else 'start'}")

    if options.selection.no_mcp:
        lines.append("allowed_mcps: none")
    elif options.selection.mcps:
        lines.append("allowed_mcps: " + ", ".join(options.selection.mcps))
    else:
        lines.append("allowed_mcps: default")

    if options.selection.no_skills:
        lines.append("allowed_skills: none")
    elif options.selection.skills:
        lines.append("allowed_skills: " + ", ".join(options.selection.skills))
    else:
        lines.append("allowed_skills: default")

    lines.append("[/loop-control]")
    lines.append("--continue" if resume else options.objective)
    return "\n".join(lines)


def build_command(options: RunnerOptions, loop_args: str) -> list[str]:
    command = [
        options.opencode_executable,
        "run",
        "--command",
        "loop",
        "--dir",
        str(options.project_dir),
        "--format",
        options.output_format,
    ]
    if options.model:
        command.extend(["--model", options.model])
    if options.agent:
        command.extend(["--agent", options.agent])
    if options.attach_url:
        command.extend(["--attach", options.attach_url])
    if options.dangerously_skip_permissions:
        command.append("--dangerously-skip-permissions")
    command.append(loop_args)
    return command


def write_log(path: Path, command: list[str], result: subprocess.CompletedProcess[str] | None) -> None:
    lines = [f"command: {shlex.join(command)}", ""]
    if result is None:
        lines.append("dry_run: true")
    else:
        lines.extend(
            [
                f"returncode: {result.returncode}",
                "",
                "## stdout",
                result.stdout,
                "",
                "## stderr",
                result.stderr,
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def run_loop(options: RunnerOptions) -> int:
    if options.max_iterations < 1:
        raise ValueError("max_iterations must be >= 1")

    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + f"-pid{os.getpid()}"
    run_dir = options.runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"project_dir={options.project_dir}")
    print(f"state_path={options.state_path}")
    print(f"run_dir={run_dir}")

    current_status = read_status(options.state_path)
    if options.resume and current_status == "complete":
        print("Loop state is already complete; nothing to run.")
        return 0

    for iteration in range(1, options.max_iterations + 1):
        resume_iteration = options.resume or iteration > 1
        loop_args = build_loop_args(options, resume=resume_iteration)
        command = build_command(options, loop_args)
        log_path = run_dir / f"iteration_{iteration:03d}.log"

        print(f"\n[{iteration}/{options.max_iterations}] {shlex.join(command)}")
        if options.dry_run:
            write_log(log_path, command, None)
            continue

        result = subprocess.run(
            command,
            cwd=options.project_dir,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        write_log(log_path, command, result)

        if result.stdout:
            print(result.stdout.rstrip())
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)

        if result.returncode != 0:
            print(f"opencode failed with exit code {result.returncode}; see {log_path}", file=sys.stderr)
            return result.returncode

        status = read_status(options.state_path)
        print(f"state_status={status or 'unknown'}")
        if status == "complete":
            print("Loop objective marked complete.")
            return 0

        time.sleep(options.sleep_seconds)

    if options.dry_run:
        print("Dry-run complete; no opencode sessions were started.")
        return 0

    print(f"Reached --max-iterations={options.max_iterations} without status: complete.", file=sys.stderr)
    print("Resume later with the same command plus --continue.", file=sys.stderr)
    return 2
