---
description: Ejecuta un objetivo largo con checkpoints y continuidad entre sesiones
---

Run the loop protocol for a long-running objective.

Arguments: `$ARGUMENTS`
Current directory: !`pwd`

Existing loop state, if any:
!`mkdir -p .opencode/loop && test -f .opencode/loop/state.md && cat .opencode/loop/state.md || echo "no existing loop state"`

Existing loop learning, if any:
!`test -f .opencode/loop/learned.md && cat .opencode/loop/learned.md || echo "no existing loop learning"`

Protocol:

1. Resolve intent.
- If `$ARGUMENTS` contains a `[loop-control]...[/loop-control]` block, parse it first.
- Supported loop-control fields:
  - `mode`: `start` or `continue`.
  - `allowed_mcps`: `default`, `none`, or comma-separated MCP names.
  - `allowed_skills`: `default`, `none`, or comma-separated skill names.
- Remove the loop-control block from the human objective before interpreting the objective.
- If `$ARGUMENTS` contains a new objective, start or replace the active loop objective with that objective.
- If `$ARGUMENTS` is empty or is `--continue`, continue from `.opencode/loop/state.md`.
- If there is no objective in arguments and no state file, ask for the objective in one concise question.
- If `mode: continue`, continue even when the remaining argument is `--continue`.

2. Enforce MCP and skill selection.
- Persist the selected MCPs and skills in `.opencode/loop/state.md`.
- `allowed_mcps: default` means use normal opencode MCP behavior for this installation.
- `allowed_mcps: none` means do not use MCP-backed tools or MCP-derived commands.
- A comma-separated `allowed_mcps` list means use only those MCP servers. Do not inspect, invoke, or rely on MCPs outside that list. If the objective appears to require an unlisted MCP, stop and report the missing MCP instead of using it.
- `allowed_skills: default` means use normal skill routing.
- `allowed_skills: none` means do not use skills.
- A comma-separated `allowed_skills` list means use only those skills. Do not inspect, load, or rely on skills outside that list. If another skill would normally trigger, mention it as not allowed and continue without it unless the task cannot be completed safely.
- If a requested MCP or skill is not available in this opencode installation, stop before substantive work and report the invalid selection.

3. Persist state before doing substantial work.
- Ensure `.opencode/loop/` exists.
- Create or update `.opencode/loop/state.md` with this structure:
  - `# Loop State`
  - `objective`
  - `status`: `active` or `complete`
  - `iteration`
  - `last_updated`
  - `allowed_mcps`
  - `allowed_skills`
  - `done`
  - `evidence`
  - `current_plan`
  - `open_questions`
  - `files_touched`
  - `next_actions`
  - `resume_prompt`
- Keep this file concise and high-signal. It must be useful after `/new`.

4. Work autonomously toward the objective.
- Inspect first, then modify.
- Prefer existing repo patterns and local instructions.
- Execute verification appropriate to the task.
- Keep the active plan current for multi-step work.

5. Context checkpoint policy.
- Treat half of the configured context window as the checkpoint threshold.
- If the configured context is unknown, use `100000` tokens as the default checkpoint threshold.
- Because exact live token count may not be available inside a markdown command, estimate conservatively from accumulated conversation, command output, file reads, and reasoning state.
- When the session appears near or past the half-context threshold, stop expanding context and checkpoint immediately.

6. Checkpoint procedure.
- Update `.opencode/loop/state.md`.
- Update `.opencode/loop/learned.md` with:
  - durable facts learned in this loop,
  - repo-specific constraints,
  - failed attempts and why they failed,
  - commands run and meaningful results,
  - next best action.
- Do not call external learning commands. This command must work in a fresh opencode installation with no custom commands.
- If the user has their own learning system, `.opencode/loop/learned.md` is the handoff artifact they can import separately.

7. Session rollover.
- A markdown command cannot reliably force the TUI to execute `/new` or switch sessions by itself.
- When checkpointing for context rollover, return only:
  - checkpoint file paths,
  - current `allowed_mcps` and `allowed_skills`,
  - exact resume command:
    `/new`
    `/loop --continue`
- Do not continue solving after a rollover checkpoint.

8. Completion.
- Mark `.opencode/loop/state.md` as `status: complete` only when the objective is actually achieved and evidence is recorded.
- Stop the loop when complete.
- Return:
  - summary,
  - files changed,
  - validation performed,
  - remaining risks or none.

Constraints:
- Do not claim automatic `/new` execution unless it actually happened.
- Do not overwrite unrelated `.opencode/` files.
- Do not depend on custom learning commands.
- Do not keep working past a checkpoint decision just because there is more to do.
