# Input formats and evidence boundaries

Inputs must be explicitly chosen `--source codex:<file-or-dir>`, `claude:<file-or-dir>` or `jsonl:<file-or-dir>`. Directories are recursively searched for JSONL; source symlinks, broken inputs, oversized lines, invalid timestamps and scan caps are coverage gaps. Read only these logs, not home-directory-wide searches. The collector never executes commands or loads source-side Python/plugins.

Codex: `session_meta`/`turn_context` supplies session/workdir; `response_item` carries user/assistant messages and function/custom tool calls/results. Mirrored `event_msg` messages are not double-counted. Known unsupported records are counted. Format is based on [public Codex protocol source](https://github.com/openai/codex/blob/main/codex-rs/protocol/src/models.rs); it may change. Local active and archived directories should be explicitly selected if available. Ephemeral/cloud sessions may have no accessible trace.

Claude Code: timestamped user/assistant JSONL messages, `tool_use`, `tool_result`, session ID and cwd. Read/Edit/Write paths are structured; Bash file effects are not guessed. See [official session documentation](https://code.claude.com/docs/en/sessions). CLI storage does not imply coverage of every desktop/cloud conversation.

Generic JSONL is the cross-agent input contract. Each line is an object:

```json
{"timestamp":"2026-10-06T09:00:00+08:00","session_id":"demo-a","kind":"task","task_id":"task-a","project":"/workspace/demo","text":"Write a fictional study guide","status":"unknown"}
{"timestamp":"2026-10-06T09:01:00+08:00","session_id":"demo-a","kind":"tool","task_id":"task-a","project":"/workspace/demo","tool":"Write","operation":"write","files":["guide.md"],"status":"succeeded"}
```

Field meanings: `timestamp` is the event's timezone-aware ISO time; `session_id` identifies a session, not a person; `kind` is task/tool/summary/artifact; `task_id` links events to the request; `project` is an optional working directory proxy; `text` is optional historical text; `tool` is an optional tool name; `operation` is a structured read/write/execute/other label; `files` is a list of explicitly recorded path strings; `status` is succeeded/failed/unknown/attempted. A supplied success claim is trusted only as a claim from that exporter, not independently audited OS truth. Never invent exporter events to fill gaps.

Reports contain all selected normalized events, task grouping, projects, file operations, output candidates and gaps. Text previews are optional and capped at 1,000 characters. Raw tool outputs, thoughts, source code and base/system instructions are not copied. JSONL metadata does not prove an event was executed if no matching successful result exists. File modifications after the reporting window do not count as success during that window.

Aliases A/T/P/F identify sessions/tasks/projects/files only within a report; S:number identifies source-file sequence and line. Private text mode shows redacted source locations for lookup, not clickable external links. Default structural mode hides locations. Copied active/archive records are deduplicated; source enumeration order is not an activity timestamp. Missing/orphan results and unrecognized records prevent claims of full coverage.

Budgets: maximum 256 MiB scanned bytes, 10,000 source files, 2 MiB per JSONL line by default. They are explicit ceilings, not silent sampling. Increase the first two via `--max-bytes`/`--max-files` after reviewing resource use. Per-file event buffering joins calls with their results; large inputs can consume substantial RAM. No persistent transcript cache or SQLite database in v0.1.
