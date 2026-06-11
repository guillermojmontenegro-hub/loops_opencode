# loops_opencode

Portable runner for long opencode tasks. It runs `/loop` in fresh opencode sessions, stores continuity in project-local state files, and stops when the loop state is marked complete.

## Project Layout

```text
bin/
  loop-tui.sh
  loop-tui.bat
  run-opencode-loop.sh
  run-opencode-loop.bat
commands/
  loop.md
config/
  loop.config.example.json
src/
  loops_opencode/
    cli.py
    config.py
    runner.py
    tui.py
```

## Install

Copy the command into your opencode commands directory:

```bash
cp commands/loop.md <opencode-commands-dir>/loop.md
```

For Windows, copy `commands/loop.md` into your opencode commands directory.

Create a local config from the example:

```bash
cp config/loop.config.example.json config/loop.config.json
```

Then edit `config/loop.config.json` if needed.

## Configuration

All defaults live in:

```text
config/loop.config.example.json
```

Recommended local override:

```text
config/loop.config.json
```

Config keys:

```json
{
  "opencode_executable": "opencode",
  "project_dir": ".",
  "state_path": ".opencode/loop/state.md",
  "runs_dir": ".opencode/loop/runs",
  "default_max_iterations": 20,
  "default_sleep_seconds": 1.0,
  "default_output_format": "default",
  "default_model": null,
  "default_agent": null,
  "default_attach_url": null,
  "default_allowed_mcps": [],
  "default_allowed_skills": [],
  "mcp_options": [],
  "skill_options": [],
  "model_options": [],
  "agent_options": [],
  "dangerously_skip_permissions": false
}
```

Every path in the default config is relative. CLI arguments override config values.

`default_allowed_mcps` and `default_allowed_skills` are optional allowlists. Empty lists mean "use opencode defaults". If you pass `--mcp` or `--skill`, the CLI selection overrides the config selection for that run.

`mcp_options`, `skill_options`, `model_options`, and `agent_options` are optional menu choices for the TUI. They are intentionally empty by default because names are installation-specific.

## TUI

Linux/macOS:

```bash
bin/loop-tui.sh
```

Windows:

```bat
bin\loop-tui.bat
```

The TUI lets you:

- enter the objective,
- choose start or continue mode,
- select max iterations and sleep,
- select MCP and skill policies,
- select model and agent values from config-provided options or manual input,
- run the loop and see iteration output in the terminal.

To provide selectable options, edit `config/loop.config.json`:

```json
{
  "mcp_options": ["<mcp-a>", "<mcp-b>"],
  "skill_options": ["<skill-a>", "<skill-b>"],
  "model_options": ["<provider>/<model>"],
  "agent_options": ["<agent-name>"]
}
```

## Usage

Linux/macOS:

```bash
bin/run-opencode-loop.sh "objective"
```

Windows:

```bat
bin\run-opencode-loop.bat "objective"
```

Continue an existing loop:

```bash
bin/run-opencode-loop.sh --continue
```

Limit iterations:

```bash
bin/run-opencode-loop.sh --max-iterations 10 "objective"
```

Dry run:

```bash
bin/run-opencode-loop.sh --dry-run --max-iterations 2 "test runner"
```

Run the Python module directly:

```bash
PYTHONPATH=src python3 -m loops_opencode.cli "objective"
```

## MCPs And Skills

By default, the runner sends:

```text
allowed_mcps: default
allowed_skills: default
```

That means normal opencode behavior. When you pass `--mcp` or `--skill`, `/loop` receives only those names and must not inspect or use anything outside the allowlist.

Allow only selected MCPs and skills:

```bash
bin/run-opencode-loop.sh --mcp <mcp-name> --skill <skill-name> "objective"
```

Allow several:

```bash
bin/run-opencode-loop.sh --mcp <mcp-a>,<mcp-b> --skill <skill-a> --skill <skill-b> "objective"
```

Disable both:

```bash
bin/run-opencode-loop.sh --no-mcp --no-skills "local objective"
```

Continue with the same selection:

```bash
bin/run-opencode-loop.sh --continue --mcp <mcp-name> --skill <skill-name>
```

## Loop State

The loop stores continuity in the target project:

```text
.opencode/loop/state.md
.opencode/loop/learned.md
.opencode/loop/runs/
```

The runner stops when `state.md` contains:

```text
status: complete
```

## Notes

- The runner uses `opencode run --command loop`.
- Each iteration starts a fresh opencode session because the runner does not pass opencode `--continue` or `--session`.
- Continuity lives in `.opencode/loop/`, not in chat context.
- MCP and skill selection is enforced by the `/loop` command protocol. The opencode CLI does not currently expose native `--mcp` or `--skill` flags.
- `/loop` does not depend on custom learning commands. Durable loop learnings are written to `.opencode/loop/learned.md`.
