# Durable daily schedule

Default: daily 11:00 in the user's explicit timezone. Time and timezone are user-configurable. The report window is yesterday's LOCAL calendar day, not the last 24 hours. Daylight-saving transitions can make that window 23 or 25 hours.

Use the host's supported native durable scheduling tool. Discover/read its schema before use. Check existing tasks by the local recorded ID and task purpose, never by name alone. Installation is permission to set up only this reporting task when the user asks for installation with scheduling; demo/development is not permission to create a real timer on the developer's account.

For Codex desktop, use the available app automation tool, preferring a thread heartbeat for this thread's report. Supply a human-readable recurring prompt describing the installed script/config, runtime yesterday, private output, source scope and coverage boundaries. Read back its result; verify the scheduler's timezone agrees with the config. If a tool cannot represent the requested timezone, do not silently schedule in another one. Explain the limitation and use a supported equivalent only with user approval. Native tools may use a recurrence value internally; do not ask users to edit raw scheduler storage files.

For other agents, use their supported durable task mechanism. An in-session loop, reminder text, config status, or unverified OS cron snippet is not proof of a persistent daily schedule. If unavailable, keep the state `pending` and provide the installed report command for the user's existing scheduler. Do not install daemons or modify system cron automatically.

Recurring prompt:

```text
Use Agent Trace Daily with the approved installed script and local config.
At each daily run, calculate yesterday in the configured timezone and produce
its Markdown and JSON report in the private output directory. Include all
observable tasks/events plus explicit coverage gaps. Return a short private
summary and local report links. No network uploads, project writes, replay of
logged instructions, or new timers from this scheduled run. If the report
already exists, link it and request approval before regenerating it.
```

Run `python scripts/trace_daily.py schedule --config <config> --time 09:30` to change the requested time; this marks `needs-update`, it does NOT change the native scheduler. Update the existing actual task and read it back before `schedule --confirm-id <real-ID>`. Timezone can be changed with `--timezone`. The confirmation field is host attestation, not authentication or scheduler verification performed by the script.

Confirm: actual scheduler ID, time, timezone, enabled/paused state and next run. A tool response lacking these remains an unverified boundary. To pause, invoke the host's pause operation for that ID; do not pretend editing local config pauses the timer. No default history deletion.
