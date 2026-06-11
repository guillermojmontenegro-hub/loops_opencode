#!/usr/bin/env python3
"""
Objetivo: ejecutar un objetivo largo de opencode en iteraciones con sesiones nuevas.
Inputs: objetivo inicial o --continue, opciones CLI del runner.
Outputs: logs por iteracion en .opencode/loop/runs/<timestamp>/.
Como correr:
  source ./venv/bin/activate
  python scripts/opencode_loop_runner.py "objetivo largo"
  python scripts/opencode_loop_runner.py --continue
Side-effects:
  - Ejecuta `opencode run --command loop ...`.
  - Crea/actualiza archivos bajo .opencode/loop/ mediante el comando /loop.
  - Guarda stdout/stderr de cada iteracion en .opencode/loop/runs/.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path


STATUS_RE = re.compile(r"^\s*(?:[-*]\s*)?(?:`?status`?\s*:|status\s*:)\s*`?([a-zA-Z_-]+)`?", re.MULTILINE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run /loop repeatedly in fresh opencode sessions until .opencode/loop/state.md is complete.",
    )
    parser.add_argument("objective", nargs="*", help="Objective to start. Omit with --continue to resume existing loop state.")
    parser.add_argument("--continue", dest="resume", action="store_true", help="Resume from .opencode/loop/state.md.")
    parser.add_argument("--max-iterations", type=int, default=20, help="Safety cap for fresh sessions. Default: 20.")
    parser.add_argument("--sleep", type=float, default=1.0, help="Seconds to wait between iterations. Default: 1.")
    parser.add_argument("--opencode", default="opencode", help="opencode executable path. Default: opencode.")
    parser.add_argument("--state", default=".opencode/loop/state.md", help="Loop state file. Default: .opencode/loop/state.md.")
    parser.add_argument("--runs-dir", default=".opencode/loop/runs", help="Run logs directory. Default: .opencode/loop/runs.")
    parser.add_argument("--model", help="Model in provider/model form, passed to opencode run.")
    parser.add_argument("--agent", help="Agent id, passed to opencode run.")
    parser.add_argument("--mcp", action="append", default=[], help="Allowed MCP name. Repeat or use comma-separated names.")
    parser.add_argument("--skill", action="append", default=[], help="Allowed skill name. Repeat or use comma-separated names.")
    parser.add_argument("--no-mcp", action="store_true", help="Tell /loop not to use MCP tools in this loop.")
    parser.add_argument("--no-skills", action="store_true", help="Tell /loop not to use skills in this loop.")
    parser.add_argument("--attach", help="Attach to an existing opencode server URL.")
    parser.add_argument("--dir", default=os.getcwd(), help="Project directory for opencode. Default: current directory.")
    parser.add_argument("--format", choices=("default", "json"), default="default", help="opencode run output format.")
    parser.add_argument(
        "--dangerously-skip-permissions",
        action="store_true",
        help="Pass through to opencode run. Use only for trusted objectives.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing them.")
    args = parser.parse_args()

    if args.max_iterations < 1:
        parser.error("--max-iterations must be >= 1")
    if args.resume and args.objective:
        parser.error("Use either an objective or --continue, not both.")
    if not args.resume and not args.objective:
        parser.error("Provide an objective or use --continue.")
    if args.no_mcp and args.mcp:
        parser.error("Use either --mcp or --no-mcp, not both.")
    if args.no_skills and args.skill:
        parser.error("Use either --skill or --no-skills, not both.")
    return args


def read_status(state_path: Path) -> str | None:
    if not state_path.exists():
        return None
    text = state_path.read_text(encoding="utf-8", errors="replace")
    match = STATUS_RE.search(text)
    return match.group(1).lower() if match else None


def build_command(args: argparse.Namespace, loop_args: str) -> list[str]:
    cmd = [
        args.opencode,
        "run",
        "--command",
        "loop",
        "--dir",
        args.dir,
        "--format",
        args.format,
    ]
    if args.model:
        cmd.extend(["--model", args.model])
    if args.agent:
        cmd.extend(["--agent", args.agent])
    if args.attach:
        cmd.extend(["--attach", args.attach])
    if args.dangerously_skip_permissions:
        cmd.append("--dangerously-skip-permissions")
    cmd.append(loop_args)
    return cmd


def split_csv(values: list[str]) -> list[str]:
    items: list[str] = []
    for value in values:
        items.extend(part.strip() for part in value.split(","))
    return [item for item in items if item]


def build_loop_args(args: argparse.Namespace, objective: str, resume: bool) -> str:
    lines = ["[loop-control]"]
    lines.append(f"mode: {'continue' if resume else 'start'}")
    if args.no_mcp:
        lines.append("allowed_mcps: none")
    elif args.mcp:
        lines.append("allowed_mcps: " + ", ".join(split_csv(args.mcp)))
    else:
        lines.append("allowed_mcps: default")

    if args.no_skills:
        lines.append("allowed_skills: none")
    elif args.skill:
        lines.append("allowed_skills: " + ", ".join(split_csv(args.skill)))
    else:
        lines.append("allowed_skills: default")

    lines.append("[/loop-control]")
    lines.append("--continue" if resume else objective)
    return "\n".join(lines)


def write_log(path: Path, command: list[str], result: subprocess.CompletedProcess[str] | None) -> None:
    lines = [
        f"command: {shlex.join(command)}",
        "",
    ]
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


def main() -> int:
    args = parse_args()
    project_dir = Path(args.dir).resolve()
    state_path = (project_dir / args.state).resolve()
    runs_root = (project_dir / args.runs_dir).resolve()
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + f"-pid{os.getpid()}"
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    objective = "" if args.resume else " ".join(args.objective)

    print(f"project_dir={project_dir}")
    print(f"state_path={state_path}")
    print(f"run_dir={run_dir}")

    current_status = read_status(state_path)
    if args.resume and current_status == "complete":
        print("Loop state is already complete; nothing to run.")
        return 0

    for iteration in range(1, args.max_iterations + 1):
        loop_args = build_loop_args(args, objective, resume=(args.resume or iteration > 1))
        command = build_command(args, loop_args)
        log_path = run_dir / f"iteration_{iteration:03d}.log"

        print(f"\n[{iteration}/{args.max_iterations}] {shlex.join(command)}")
        if args.dry_run:
            write_log(log_path, command, None)
            continue

        result = subprocess.run(
            command,
            cwd=project_dir,
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

        status = read_status(state_path)
        print(f"state_status={status or 'unknown'}")
        if status == "complete":
            print("Loop objective marked complete.")
            return 0

        time.sleep(args.sleep)

    if args.dry_run:
        print("Dry-run complete; no opencode sessions were started.")
        return 0

    print(f"Reached --max-iterations={args.max_iterations} without status: complete.", file=sys.stderr)
    print(f"Resume later with: python scripts/opencode_loop_runner.py --continue", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
