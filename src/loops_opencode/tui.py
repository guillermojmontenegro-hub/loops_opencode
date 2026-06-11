from __future__ import annotations

import sys
from pathlib import Path

from .config import LoopConfig, first_existing_config, load_config
from .runner import LoopSelection, RunnerOptions, run_loop, split_csv

try:
    from textual import work
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical
    from textual.widgets import Button, Checkbox, Footer, Header, Input, Label, RichLog, Select, Static, TextArea
except ModuleNotFoundError:  # pragma: no cover - exercised only when optional dep is missing.
    from .simple_tui import main
else:

    def config_list(value: list[str] | None) -> list[str]:
        return list(value or [])


    def load_default_config() -> LoopConfig:
        config_path = first_existing_config([Path("config/loop.config.json"), Path("config/loop.config.example.json")])
        return load_config(config_path)


    def option_pairs(
        values: list[str],
        include_default: bool = False,
        include_none: bool = False,
        include_manual: bool = True,
    ) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        if include_default:
            rows.append(("default", "default"))
        if include_none:
            rows.append(("none", "none"))
        rows.extend((value, value) for value in values)
        if include_manual:
            rows.append(("manual", "manual"))
        return rows


    def csv_values(value: str) -> tuple[str, ...]:
        return split_csv([value])


    class LoopTuiApp(App[int]):
        CSS = """
        Screen {
            layout: vertical;
        }

        #body {
            layout: horizontal;
            height: 1fr;
        }

        #left {
            width: 42%;
            min-width: 42;
            padding: 1;
            border: solid $primary;
        }

        #right {
            width: 58%;
            padding: 1;
            border: solid $secondary;
        }

        .row {
            height: auto;
            margin-bottom: 1;
        }

        .pair {
            layout: horizontal;
            height: auto;
            margin-bottom: 1;
        }

        .pair > * {
            width: 1fr;
            margin-right: 1;
        }

        Label {
            height: 1;
        }

        TextArea {
            height: 6;
        }

        #log {
            height: 1fr;
            border: round $accent;
        }

        #status {
            height: 3;
            padding: 1;
        }

        Button {
            margin-right: 1;
        }
        """

        BINDINGS = [
            ("ctrl+r", "run_loop", "Run"),
            ("ctrl+d", "toggle_dark", "Theme"),
            ("q", "quit", "Quit"),
        ]

        def __init__(self, config: LoopConfig) -> None:
            super().__init__()
            self.config_data = config
            self.running = False
            self.exit_code = 0

        def compose(self) -> ComposeResult:
            config = self.config_data
            mcps = config_list(config.mcp_options)
            skills = config_list(config.skill_options)
            models = config_list(config.model_options)
            agents = config_list(config.agent_options)

            yield Header(show_clock=True)
            with Horizontal(id="body"):
                with Vertical(id="left"):
                    yield Label("Objective")
                    yield TextArea("", id="objective")

                    with Container(classes="pair"):
                        yield Checkbox("Continue existing loop", id="resume")
                        yield Checkbox("Dry run", id="dry_run")

                    with Container(classes="pair"):
                        yield Input(str(config.default_max_iterations), id="max_iterations", placeholder="Max iterations")
                        yield Input(str(config.default_sleep_seconds), id="sleep_seconds", placeholder="Sleep seconds")

                    yield Label("Execution")
                    with Container(classes="pair"):
                        yield Input(config.opencode_executable, id="opencode_executable", placeholder="opencode executable")
                        yield Input(config.project_dir, id="project_dir", placeholder="Project dir")

                    with Container(classes="pair"):
                        yield Input(config.state_path, id="state_path", placeholder="State path")
                        yield Input(config.runs_dir, id="runs_dir", placeholder="Runs dir")

                    with Container(classes="pair"):
                        yield Select(option_pairs(["default", "json"], include_manual=False), value=config.default_output_format, id="output_format")
                        yield Checkbox("Skip permissions", id="skip_permissions", value=config.dangerously_skip_permissions)

                    yield Label("Model and agent")
                    with Container(classes="pair"):
                        yield Select(option_pairs(models, include_none=True), value=config.default_model or "none", id="model")
                        yield Select(option_pairs(agents, include_none=True), value=config.default_agent or "none", id="agent")

                    yield Label("MCP policy")
                    with Container(classes="pair"):
                        yield Select(option_pairs(mcps, include_default=True, include_none=True), value="default", id="mcp_policy")
                        yield Input("", id="mcp_manual", placeholder="Manual MCP list")

                    yield Label("Skill policy")
                    with Container(classes="pair"):
                        yield Select(option_pairs(skills, include_default=True, include_none=True), value="default", id="skill_policy")
                        yield Input("", id="skill_manual", placeholder="Manual skill list")

                    with Container(classes="row"):
                        yield Button("Run loop", id="run", variant="success")
                        yield Button("Stop", id="stop", variant="error", disabled=True)
                        yield Button("Clear log", id="clear", variant="default")

                with Vertical(id="right"):
                    yield Static("Ready.", id="status")
                    yield RichLog(id="log", wrap=True, highlight=True, markup=True)
            yield Footer()

        def on_mount(self) -> None:
            self.query_one("#log", RichLog).write("Configure the loop, then press Ctrl+R or Run loop.")

        def action_toggle_dark(self) -> None:
            self.dark = not self.dark

        def action_run_loop(self) -> None:
            self.start_loop()

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "run":
                self.start_loop()
            elif event.button.id == "stop":
                self.stop_loop()
            elif event.button.id == "clear":
                self.query_one("#log", RichLog).clear()

        def start_loop(self) -> None:
            if self.running:
                self.write_log("Loop is already running.")
                return
            try:
                options = self.build_options()
            except ValueError as exc:
                self.set_status(f"Invalid configuration: {exc}")
                return
            if not options.resume and not options.objective.strip():
                self.set_status("Enter an objective or enable continue mode.")
                return
            self.running = True
            self.query_one("#run", Button).disabled = True
            self.query_one("#stop", Button).disabled = False
            self.set_status("Running loop...")
            self.write_log("[bold green]Starting loop[/bold green]")
            self.run_loop_worker(options)

        def stop_loop(self) -> None:
            worker = self.workers.get_worker("loop", default=None)
            if worker:
                worker.cancel()
                self.write_log("[yellow]Stop requested.[/yellow]")
            self.running = False
            self.query_one("#run", Button).disabled = False
            self.query_one("#stop", Button).disabled = True
            self.set_status("Stop requested.")

        @work(thread=True, name="loop", exclusive=True)
        def run_loop_worker(self, options: RunnerOptions) -> None:
            code = run_loop(options, emit=lambda message: self.call_from_thread(self.write_log, message))
            self.call_from_thread(self.loop_finished, code)

        def loop_finished(self, code: int) -> None:
            self.running = False
            self.exit_code = code
            self.query_one("#run", Button).disabled = False
            self.query_one("#stop", Button).disabled = True
            self.set_status(f"Loop exited with code {code}.")
            self.write_log(f"[bold]Loop exited with code {code}.[/bold]")

        def write_log(self, message: str) -> None:
            self.query_one("#log", RichLog).write(message)

        def set_status(self, message: str) -> None:
            self.query_one("#status", Static).update(message)

        def input_value(self, selector: str) -> str:
            return self.query_one(selector, Input).value.strip()

        def text_value(self, selector: str) -> str:
            return self.query_one(selector, TextArea).text.strip()

        def selected_value(self, selector: str) -> str:
            value = self.query_one(selector, Select).value
            return "" if value is None else str(value)

        def checked(self, selector: str) -> bool:
            return bool(self.query_one(selector, Checkbox).value)

        def build_options(self) -> RunnerOptions:
            max_iterations = self.parse_int(self.input_value("#max_iterations"), "max iterations")
            sleep_seconds = self.parse_float(self.input_value("#sleep_seconds"), "sleep seconds")
            project_dir = Path(self.input_value("#project_dir") or ".")
            state_path = Path(self.input_value("#state_path") or ".opencode/loop/state.md")
            runs_dir = Path(self.input_value("#runs_dir") or ".opencode/loop/runs")
            resume = self.checked("#resume")
            model = self.none_if_empty_or_none(self.selected_value("#model"))
            agent = self.none_if_empty_or_none(self.selected_value("#agent"))

            return RunnerOptions(
                objective="" if resume else self.text_value("#objective"),
                resume=resume,
                max_iterations=max_iterations,
                sleep_seconds=sleep_seconds,
                opencode_executable=self.input_value("#opencode_executable") or "opencode",
                project_dir=project_dir,
                state_path=state_path if state_path.is_absolute() else project_dir / state_path,
                runs_dir=runs_dir if runs_dir.is_absolute() else project_dir / runs_dir,
                output_format=self.selected_value("#output_format") or "default",
                model=model,
                agent=agent,
                attach_url=None,
                dangerously_skip_permissions=self.checked("#skip_permissions"),
                dry_run=self.checked("#dry_run"),
                selection=self.build_selection(),
            )

        def build_selection(self) -> LoopSelection:
            mcp_policy = self.selected_value("#mcp_policy")
            skill_policy = self.selected_value("#skill_policy")
            mcps = self.policy_values(mcp_policy, self.input_value("#mcp_manual"))
            skills = self.policy_values(skill_policy, self.input_value("#skill_manual"))
            return LoopSelection(
                mcps=mcps,
                skills=skills,
                no_mcp=mcp_policy == "none",
                no_skills=skill_policy == "none",
            )

        @staticmethod
        def policy_values(policy: str, manual: str) -> tuple[str, ...]:
            if policy in ("default", "none"):
                return ()
            if policy == "manual":
                return csv_values(manual)
            return (policy,) if policy else ()

        @staticmethod
        def none_if_empty_or_none(value: str) -> str | None:
            return None if value in ("", "none") else value

        @staticmethod
        def parse_int(value: str, label: str) -> int:
            try:
                parsed = int(value)
            except ValueError as exc:
                raise ValueError(f"{label} must be an integer") from exc
            if parsed < 1:
                raise ValueError(f"{label} must be >= 1")
            return parsed

        @staticmethod
        def parse_float(value: str, label: str) -> float:
            try:
                parsed = float(value)
            except ValueError as exc:
                raise ValueError(f"{label} must be a number") from exc
            if parsed < 0:
                raise ValueError(f"{label} must be >= 0")
            return parsed


    def main(argv: list[str] | None = None) -> int:
        _ = argv
        config = load_default_config()
        app = LoopTuiApp(config)
        result = app.run()
        return int(result or app.exit_code or 0)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
