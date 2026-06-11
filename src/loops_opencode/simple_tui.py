from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import LoopConfig, first_existing_config, load_config
from .runner import LoopSelection, RunnerOptions, run_loop, split_csv


@dataclass
class TuiState:
    objective: str = ""
    resume: bool = False
    max_iterations: int = 20
    sleep_seconds: float = 1.0
    opencode_executable: str = "opencode"
    project_dir: str = "."
    state_path: str = ".opencode/loop/state.md"
    runs_dir: str = ".opencode/loop/runs"
    output_format: str = "default"
    model: str | None = None
    agent: str | None = None
    attach_url: str | None = None
    dangerously_skip_permissions: bool = False
    dry_run: bool = False
    mcp_mode: str = "default"
    skill_mode: str = "default"
    mcps: list[str] | None = None
    skills: list[str] | None = None


def config_list(value: list[str] | None) -> list[str]:
    return list(value or [])


def load_default_config() -> LoopConfig:
    config_path = first_existing_config([Path("config/loop.config.json"), Path("config/loop.config.example.json")])
    return load_config(config_path)


def state_from_config(config: LoopConfig) -> TuiState:
    mcps = config_list(config.default_allowed_mcps)
    skills = config_list(config.default_allowed_skills)
    return TuiState(
        max_iterations=config.default_max_iterations,
        sleep_seconds=config.default_sleep_seconds,
        opencode_executable=config.opencode_executable,
        project_dir=config.project_dir,
        state_path=config.state_path,
        runs_dir=config.runs_dir,
        output_format=config.default_output_format,
        model=config.default_model,
        agent=config.default_agent,
        attach_url=config.default_attach_url,
        dangerously_skip_permissions=config.dangerously_skip_permissions,
        mcp_mode="allowlist" if mcps else "default",
        skill_mode="allowlist" if skills else "default",
        mcps=mcps,
        skills=skills,
    )


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def pause() -> None:
    input("\nPress Enter to continue...")


def prompt_text(label: str, current: str | None = None, allow_empty: bool = True) -> str | None:
    suffix = f" [{current}]" if current else ""
    value = input(f"{label}{suffix}: ").strip()
    if value:
        return value
    if allow_empty:
        return current
    return None


def prompt_int(label: str, current: int) -> int:
    while True:
        value = input(f"{label} [{current}]: ").strip()
        if not value:
            return current
        try:
            parsed = int(value)
        except ValueError:
            print("Enter an integer.")
            continue
        if parsed < 1:
            print("Enter a value >= 1.")
            continue
        return parsed


def prompt_float(label: str, current: float) -> float:
    while True:
        value = input(f"{label} [{current}]: ").strip()
        if not value:
            return current
        try:
            parsed = float(value)
        except ValueError:
            print("Enter a number.")
            continue
        if parsed < 0:
            print("Enter a value >= 0.")
            continue
        return parsed


def choose_one(label: str, options: list[str], current: str | None = None, allow_none: bool = True) -> str | None:
    while True:
        print(f"\n{label}")
        rows = list(options)
        if allow_none:
            print("0) none")
        for index, option in enumerate(rows, start=1):
            marker = " *" if option == current else ""
            print(f"{index}) {option}{marker}")
        print("m) manual")
        print("Enter to keep current")
        choice = input("> ").strip()
        if not choice:
            return current
        if allow_none and choice == "0":
            return None
        if choice.lower() == "m":
            return prompt_text("Manual value", current, allow_empty=True)
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(rows):
                return rows[index - 1]
        print("Invalid selection.")


def choose_allowlist(label: str, options: list[str], mode: str, current: list[str] | None) -> tuple[str, list[str] | None]:
    while True:
        print(f"\n{label}")
        print(f"Current mode: {mode}")
        print(f"Current allowlist: {', '.join(current or []) if current else '(empty)'}")
        print("1) default")
        print("2) none")
        print("3) choose from configured options")
        print("4) manual comma-separated list")
        print("Enter to keep current")
        choice = input("> ").strip()
        if not choice:
            return mode, current
        if choice == "1":
            return "default", None
        if choice == "2":
            return "none", None
        if choice == "3":
            if not options:
                print("No configured options. Use manual entry or add options to config.")
                continue
            selected = select_many(options, current or [])
            return "allowlist", selected
        if choice == "4":
            value = input("Names: ").strip()
            return "allowlist", list(split_csv([value]))
        print("Invalid selection.")


def select_many(options: list[str], current: list[str]) -> list[str]:
    selected = set(current)
    while True:
        print("\nToggle options:")
        for index, option in enumerate(options, start=1):
            marker = "x" if option in selected else " "
            print(f"{index}) [{marker}] {option}")
        print("a) accept")
        print("c) clear")
        choice = input("> ").strip().lower()
        if choice == "a" or not choice:
            return [option for option in options if option in selected]
        if choice == "c":
            selected.clear()
            continue
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(options):
                option = options[index - 1]
                if option in selected:
                    selected.remove(option)
                else:
                    selected.add(option)
                continue
        print("Invalid selection.")


def print_header(state: TuiState) -> None:
    clear_screen()
    print("loops_opencode TUI")
    print("==================")
    print(f"Objective: {state.objective or '(not set)'}")
    print(f"Mode: {'continue' if state.resume else 'start'}")
    print(f"Iterations: {state.max_iterations}")
    print(f"Sleep: {state.sleep_seconds}")
    print(f"Project dir: {state.project_dir}")
    print(f"opencode: {state.opencode_executable}")
    print(f"Output format: {state.output_format}")
    print(f"Model: {state.model or '(default)'}")
    print(f"Agent: {state.agent or '(default)'}")
    print(f"MCPs: {format_policy(state.mcp_mode, state.mcps)}")
    print(f"Skills: {format_policy(state.skill_mode, state.skills)}")
    print(f"Dry run: {state.dry_run}")
    print(f"Skip permissions: {state.dangerously_skip_permissions}")


def format_policy(mode: str, values: list[str] | None) -> str:
    if mode == "default":
        return "default"
    if mode == "none":
        return "none"
    return ", ".join(values or []) or "(empty allowlist)"


def build_runner_options(state: TuiState) -> RunnerOptions:
    project_dir = Path(state.project_dir)
    state_path = Path(state.state_path)
    runs_dir = Path(state.runs_dir)
    selection = LoopSelection(
        mcps=tuple(state.mcps or ()),
        skills=tuple(state.skills or ()),
        no_mcp=state.mcp_mode == "none",
        no_skills=state.skill_mode == "none",
    )
    return RunnerOptions(
        objective="" if state.resume else state.objective,
        resume=state.resume,
        max_iterations=state.max_iterations,
        sleep_seconds=state.sleep_seconds,
        opencode_executable=state.opencode_executable,
        project_dir=project_dir,
        state_path=state_path if state_path.is_absolute() else project_dir / state_path,
        runs_dir=runs_dir if runs_dir.is_absolute() else project_dir / runs_dir,
        output_format=state.output_format,
        model=state.model,
        agent=state.agent,
        attach_url=state.attach_url,
        dangerously_skip_permissions=state.dangerously_skip_permissions,
        dry_run=state.dry_run,
        selection=selection,
    )


def edit_advanced(state: TuiState, config: LoopConfig) -> None:
    while True:
        clear_screen()
        print("Advanced")
        print("========")
        print("1) opencode executable")
        print("2) project dir")
        print("3) state path")
        print("4) runs dir")
        print("5) output format")
        print("6) model")
        print("7) agent")
        print("8) attach URL")
        print("9) toggle skip permissions")
        print("0) back")
        choice = input("> ").strip()
        if choice == "0" or not choice:
            return
        if choice == "1":
            state.opencode_executable = prompt_text("opencode executable", state.opencode_executable) or state.opencode_executable
        elif choice == "2":
            state.project_dir = prompt_text("Project dir", state.project_dir) or state.project_dir
        elif choice == "3":
            state.state_path = prompt_text("State path", state.state_path) or state.state_path
        elif choice == "4":
            state.runs_dir = prompt_text("Runs dir", state.runs_dir) or state.runs_dir
        elif choice == "5":
            state.output_format = choose_one("Output format", ["default", "json"], state.output_format, allow_none=False) or state.output_format
        elif choice == "6":
            state.model = choose_one("Model", config_list(config.model_options), state.model)
        elif choice == "7":
            state.agent = choose_one("Agent", config_list(config.agent_options), state.agent)
        elif choice == "8":
            state.attach_url = prompt_text("Attach URL", state.attach_url)
        elif choice == "9":
            state.dangerously_skip_permissions = not state.dangerously_skip_permissions


def main(argv: list[str] | None = None) -> int:
    _ = argv
    config = load_default_config()
    state = state_from_config(config)

    while True:
        print_header(state)
        print("\nMenu")
        print("1) objective")
        print("2) toggle start/continue")
        print("3) max iterations")
        print("4) sleep seconds")
        print("5) MCP policy")
        print("6) Skill policy")
        print("7) toggle dry run")
        print("8) advanced")
        print("9) run loop")
        print("0) quit")
        choice = input("> ").strip()

        if choice == "0":
            return 0
        if choice == "1":
            state.objective = prompt_text("Objective", state.objective, allow_empty=True) or ""
        elif choice == "2":
            state.resume = not state.resume
        elif choice == "3":
            state.max_iterations = prompt_int("Max iterations", state.max_iterations)
        elif choice == "4":
            state.sleep_seconds = prompt_float("Sleep seconds", state.sleep_seconds)
        elif choice == "5":
            state.mcp_mode, state.mcps = choose_allowlist(
                "MCP policy",
                config_list(config.mcp_options),
                state.mcp_mode,
                state.mcps,
            )
        elif choice == "6":
            state.skill_mode, state.skills = choose_allowlist(
                "Skill policy",
                config_list(config.skill_options),
                state.skill_mode,
                state.skills,
            )
        elif choice == "7":
            state.dry_run = not state.dry_run
        elif choice == "8":
            edit_advanced(state, config)
        elif choice == "9":
            if not state.resume and not state.objective.strip():
                print("Set an objective first, or switch to continue mode.")
                pause()
                continue
            clear_screen()
            print("Running loop")
            print("============")
            code = run_loop(build_runner_options(state))
            print(f"\nLoop exited with code {code}.")
            pause()
        else:
            print("Invalid selection.")
            pause()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
