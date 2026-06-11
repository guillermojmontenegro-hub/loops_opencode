from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import first_existing_config, load_config, merge_value
from .runner import LoopSelection, RunnerOptions, run_loop, split_csv


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run /loop repeatedly in fresh opencode sessions until the loop state is complete.",
    )
    parser.add_argument("objective", nargs="*", help="Objective to start. Omit with --continue to resume existing loop state.")
    parser.add_argument("--config", help="Path to JSON config. Defaults to config/loop.config.json when present.")
    parser.add_argument("--continue", dest="resume", action="store_true", help="Resume from the configured state file.")
    parser.add_argument("--max-iterations", type=int, help="Safety cap for fresh sessions.")
    parser.add_argument("--sleep", type=float, help="Seconds to wait between iterations.")
    parser.add_argument("--opencode", help="opencode executable path or command name.")
    parser.add_argument("--state", help="Loop state file relative to project dir unless absolute.")
    parser.add_argument("--runs-dir", help="Run logs directory relative to project dir unless absolute.")
    parser.add_argument("--model", help="Model in provider/model form, passed to opencode run.")
    parser.add_argument("--agent", help="Agent id, passed to opencode run.")
    parser.add_argument("--mcp", action="append", default=[], help="Allowed MCP name. Repeat or use comma-separated names.")
    parser.add_argument("--skill", action="append", default=[], help="Allowed skill name. Repeat or use comma-separated names.")
    parser.add_argument("--no-mcp", action="store_true", help="Tell /loop not to use MCP tools in this loop.")
    parser.add_argument("--no-skills", action="store_true", help="Tell /loop not to use skills in this loop.")
    parser.add_argument("--attach", help="Attach to an existing opencode server URL.")
    parser.add_argument("--dir", help="Project directory for opencode.")
    parser.add_argument("--format", choices=("default", "json"), help="opencode run output format.")
    parser.add_argument("--dangerously-skip-permissions", action="store_true", help="Pass through to opencode run.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing them.")
    args = parser.parse_args(argv)

    if args.resume and args.objective:
        parser.error("Use either an objective or --continue, not both.")
    if not args.resume and not args.objective:
        parser.error("Provide an objective or use --continue.")
    if args.no_mcp and args.mcp:
        parser.error("Use either --mcp or --no-mcp, not both.")
    if args.no_skills and args.skill:
        parser.error("Use either --skill or --no-skills, not both.")
    return args


def resolve_path(project_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_dir / path


def config_list(value: list[str] | None) -> list[str]:
    return value if value else []


def build_options(args: argparse.Namespace) -> RunnerOptions:
    config_path = Path(args.config) if args.config else first_existing_config(
        [Path("config/loop.config.json"), Path("config/loop.config.example.json")]
    )
    config = load_config(config_path)

    project_dir = Path(merge_value(args.dir, config.project_dir))
    state_value = merge_value(args.state, config.state_path)
    runs_value = merge_value(args.runs_dir, config.runs_dir)

    skip_permissions = bool(config.dangerously_skip_permissions or args.dangerously_skip_permissions)
    selected_mcps = args.mcp if args.mcp else config_list(config.default_allowed_mcps)
    selected_skills = args.skill if args.skill else config_list(config.default_allowed_skills)

    return RunnerOptions(
        objective="" if args.resume else " ".join(args.objective),
        resume=args.resume,
        max_iterations=int(merge_value(args.max_iterations, config.default_max_iterations)),
        sleep_seconds=float(merge_value(args.sleep, config.default_sleep_seconds)),
        opencode_executable=str(merge_value(args.opencode, config.opencode_executable)),
        project_dir=project_dir,
        state_path=resolve_path(project_dir, state_value),
        runs_dir=resolve_path(project_dir, runs_value),
        output_format=str(merge_value(args.format, config.default_output_format)),
        model=merge_value(args.model, config.default_model),
        agent=merge_value(args.agent, config.default_agent),
        attach_url=merge_value(args.attach, config.default_attach_url),
        dangerously_skip_permissions=skip_permissions,
        dry_run=args.dry_run,
        selection=LoopSelection(
            mcps=split_csv(selected_mcps),
            skills=split_csv(selected_skills),
            no_mcp=args.no_mcp,
            no_skills=args.no_skills,
        ),
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    options = build_options(args)
    return run_loop(options)


if __name__ == "__main__":
    raise SystemExit(main())
