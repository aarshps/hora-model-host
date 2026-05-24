# Tool Guidance

You have a real shell, a real filesystem, a real browser. Use them.

## When to use which tool

| Situation | Use |
|---|---|
| User asks a factual question with a date-sensitive answer | `browser` (search) |
| User asks something you already know | answer directly, no tool |
| User wants a file generated/edited | `write` / `edit` |
| User wants something computed, scripted, or installed | `bash` |
| User wants a long task tracked | `sessions_spawn` + report back |
| User wants a recurring check | `cron` |

## Streaming
Always stream output. The operator is on Telegram and will read partial
results — they don't want to wait for the full response before seeing
progress.

## Long-running tasks
For anything that takes more than ~30 seconds:
1. Acknowledge the task in one line.
2. Spawn a sub-session or background process.
3. Report progress in chunks (every meaningful step), not at the end.
4. Final summary at the end with the actual outcome.

## Workspace hygiene
- Keep scratch files under `~/.openclaw/workspace/scratch/`.
- Keep persistent artifacts under `~/.openclaw/workspace/artifacts/`.
- Don't litter the home directory.
