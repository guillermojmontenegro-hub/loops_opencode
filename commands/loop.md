---
description: Ejecuta un objetivo largo con checkpoints y continuidad entre sesiones
agent: assistant-general
---

Run the loop protocol for a long-running objective.

Arguments: `$ARGUMENTS`
Current directory: !`pwd`
Configured local model context windows:
!`node -e 'const fs=require("fs"); const p="/home/guillermo/.config/opencode/opencode.json"; const c=JSON.parse(fs.readFileSync(p,"utf8")); for (const [provider,pc] of Object.entries(c.provider||{})) for (const [model,mc] of Object.entries(pc.models||{})) console.log(`${provider}/${model}: context=${mc.limit?.context ?? "unknown"} output=${mc.limit?.output ?? "unknown"}`)'`

Configured MCP servers:
!`node -e 'const fs=require("fs"); const p="/home/guillermo/.config/opencode/opencode.json"; const c=JSON.parse(fs.readFileSync(p,"utf8")); for (const [name,mcp] of Object.entries(c.mcp||{})) console.log(`${name}: ${mcp.enabled === false || mcp.disabled === true ? "disabled" : "enabled"}`)'`

Available local skills:
!`find /home/guillermo/.config/opencode/skills /mnt/ssd_storage/ParaAgentes/.agents/skills -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | sort -u`

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
- `allowed_mcps: default` means use the MCPs enabled by opencode config when useful.
- `allowed_mcps: none` means do not use MCP-backed tools or MCP-derived commands.
- A comma-separated `allowed_mcps` list means use only those MCP servers. If the objective appears to require an unlisted MCP, stop and report the missing MCP instead of using it.
- `allowed_skills: default` means use normal skill routing.
- `allowed_skills: none` means do not use skills.
- A comma-separated `allowed_skills` list means use only those skills. If another skill would normally trigger, mention it as not allowed and continue without it unless the task cannot be completed safely.
- If a requested MCP or skill is not available, stop before substantive work and report the invalid selection.

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
- Run `/aprender` with the durable, reusable learning when it is genuinely reusable beyond this loop.
- If invoking another slash command is not available from inside this command, write the reusable learning into `.opencode/loop/learned.md` and explicitly tell the user to run `/aprender <summary>` after the checkpoint.

7. Session rollover.
- A markdown command cannot reliably force the TUI to execute `/new` or switch sessions by itself.
- When checkpointing for context rollover, return only:
  - checkpoint file paths,
  - whether `/aprender` was run or the exact `/aprender ...` command to run,
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
- Do not use `/aprender` for one-off details with no reuse value.
- Do not keep working past a checkpoint decision just because there is more to do.
