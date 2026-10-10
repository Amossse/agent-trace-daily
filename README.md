# Agent Trace Daily

[中文](README.zh-CN.md)

A portable Skill that reports yesterday's recorded Agent work: requests, tool executions, working directories, evidenced file operations, output candidates, failures, and a complete **normalized observable timeline**. A bundled Python helper makes collection reproducible; the Agent explains the results without replaying logged commands.

Installation immediately prints an instruction to the Agent to create a daily native scheduled task, default **11:00 in the selected timezone**. Time is configurable. The installer itself does not secretly create a timer; only scheduler read-back establishes that one exists. A manual Skill folder copy requires first activation for onboarding.

## Install

Python 3.11+. Linux/macOS normally have IANA timezone data; Windows may need `python -m pip install tzdata`. Fixed offsets such as `+08:00` work without a timezone database but do not adapt to daylight saving. The report helper does not need model APIs, network access, or third-party packages other than optional timezone data.

```sh
git clone https://github.com/Amossse/agent-trace-daily.git
cd agent-trace-daily
python scripts/trace_daily.py install --agent codex --timezone Asia/Shanghai
# Claude Code: use --agent claude
# Different time: add --time 09:30
# Readable private task/path/argument previews: opt in with --include-text
```

Default sources: Codex local `sessions` and `archived_sessions`, or Claude Code local `projects`. The installer chooses only that host's directories; it never searches the entire machine. Before scheduling, the Agent confirms sources, timezone and privacy mode. For multiple hosts or exported traces, repeat `--source codex:<dir>`, `--source claude:<dir>`, `--source jsonl:<dir-or-file>`. A generic host requires explicit sources.

The installer prints `installed`, `config`, `schedule_status: pending`, and `agent_instruction`. **Give that instruction to your Agent**, or say:

```text
Use agent-trace-daily. Follow the installed LOCAL_SETUP.md to create one daily
11:00 task in my configured timezone. Verify the actual scheduler result.
Keep logs and reports local. Do not create duplicate timers.
```

Use the host's native durable scheduler; no hidden OS cron edits, daemon installation, app hooks or network upload. If it is unavailable, the Agent reports `schedule_pending` and gives the manual command. See [scheduling boundaries](references/scheduling.md). Different agents have different scheduling capabilities; this project does not promise every host supports persistent timers.

## Runnable fictional example

Keep even demo reports outside the source checkout:

```sh
python scripts/trace_daily.py report --source jsonl:examples/demo.jsonl \
  --timezone Asia/Shanghai --date 2026-10-06 \
  --output-dir ../trace-demo-output --include-text
```

Expected: 2 tasks, 7 normalized events, 1 working-directory project, 2 explicit file paths, 1 failed tool call, and output candidates. JSON and Chinese Markdown are written under the chosen private directory. The guide completion text is an Agent/exporter claim, not independently proven success. The date and all inputs are fictional. The command refuses existing outputs unless you explicitly request reviewed regeneration with `--replace`.

For an installed config:

```sh
python /path/to/installed/agent-trace-daily/scripts/trace_daily.py report \
  --config /path/to/private/config.json --date yesterday
```

The scheduler calculates yesterday at runtime, using local-calendar midnight boundaries; it never freezes yesterday's date or substitutes the last 24 hours. `--date YYYY-MM-DD` backfills a selected day. Daily report runs do not create schedules, modify projects, clean up history, or continue unfinished jobs.

## What the report means

| Section | Evidence boundary |
|---|---|
| Tasks and outcomes | User requests and Agent self-reports; self-report is not verification |
| Projects | Working directories are project proxies, not verified repository roots |
| Changes | Structured writes + matching successful result, not a guessed shell diff |
| Files | Explicit Read/Edit/Write/patch paths; opaque shell/JS internals remain gaps |
| Accumulation | Explicit exported artifacts and confirmed-write candidates; no invented memory saves |
| Timeline | All selected normalized events, not raw thoughts, entire transcripts or all real execution |
| Coverage | Missing/unreadable sources, schema mismatches, orphan results, invalid timestamps, truncation and caps |

Codex and Claude Code local JSONL are supported; other Agents can export the [generic contract](references/formats.md). Copied active/archive events are deduplicated. Long-running sessions are selected by event timestamps, not filenames or mtime. A result arriving after the reporting day cannot prove that operation succeeded during that day. Subagent logs under selected directories are included if their formats are supported.

`within-configured-logs` means no detected parsing gap for those inputs. It NEVER means every Agent's every action was captured. Ephemeral sessions, cloud-only activity, GUI/browser actions without local logs, opaque function wrappers and unsupported versions can be absent. Do not infer a quiet day merely from an empty report. Live schema drift requires new fictional fixtures, not assumptions.

## Configuration and schedule changes

Private config defaults to `~/.agent-trace-daily/config.json`; reports go to its `reports` directory. Windows uses the user's home directory as well. Choose `--state-dir`/`--skill-dir` explicitly for a portable setup. Existing installations/configs are preserved; no forced upgrade. Config fields: source list, timezone, requested time, private output directory, text opt-in, installed script path and host-attested schedule ID/status. No keys, raw transcripts or databases are required.

```sh
python /path/to/installed/scripts/trace_daily.py schedule \
  --config /path/to/private/config.json --time 09:30
```

This prints an Agent instruction and marks `needs-update`; ask the Agent to update the **existing native timer** and verify it, then record the real ID. Local config changes do not modify or pause the native scheduler by themselves. Stop/pause through that scheduler; keep historical logs/reports unless separately asked to delete them.

## Privacy, resource ceilings and limitations

Structural mode is default: aliases replace session/project/file identities and text/arguments are omitted. Opt-in `--include-text` gives best-effort-redacted previews up to 1,000 characters, plus redacted paths. These are **private, not safe-for-publication exports**; previews can still contain identifying, internal, or confidential content. Raw tool outputs and base/system instructions are not copied; write contents are omitted. Command previews may contain code fragments. Review before sharing or using an external model/provider. The helper itself makes no network/model calls.

POSIX outputs are created as 0600 files; new private directories are 0700. Windows confidentiality depends on directory ACLs. Symlink paths are rejected; use physical paths. This is not a hostile-filesystem sandbox, forensic audit or privacy certification. Markdown/JSON are separate atomic files, not a cross-file transaction; an I/O failure can leave one report file. Existing output is never silently overwritten. No automatic retention deletion.

Default caps: 256 MiB scanned bytes, 10,000 files, 2 MiB per input line. Reaching a cap creates a coverage gap; it is not hidden sampling. Raise `--max-bytes`/`--max-files` deliberately. Per-file buffering joins call/result evidence and can use significant RAM. There is no historical cache, indexing service, duration/cost estimation, or invented token total.

## Test and contribute

```sh
python -m unittest discover -s tests -v
```

Tests use only fictional temporary traces and temporary installations. They check DST, date boundaries, parsers, deduplication, failed/late results, privacy mode, budgets, installation handoff, schedule-state attestation and no-overwrite behavior. Timer-state tests do **not** create real timers. See [validation](VALIDATION.md), [security](SECURITY.md), [contributing](CONTRIBUTING.md), [changelog](CHANGELOG.md), [MIT license](LICENSE) and [unposted bilingual launch drafts](LAUNCH.md).

Source references: [Agent Skills specification](https://agentskills.io/specification), [Codex protocol](https://github.com/openai/codex/blob/main/codex-rs/protocol/src/models.rs), [Claude Code sessions](https://code.claude.com/docs/en/sessions).

Keywords: Agent execution trace, daily report, Agent activity, Agent Skills, Codex, Claude Code, local-first, trajectory, privacy, scheduled reporting.

Scan all sources in descending file modification order to prioritize recent activity under the byte budget; modification time never excludes a session, and event timestamps still select the day. Coverage reports scan file/byte totals and distinguishes day-scoped parser gaps from scan-wide read/budget gaps. Tool names inside functions.exec are static references only, never proof of execution, success or file operations.

Incremental reports keep owner-only checkpoints in `cache` beside the reports directory. Checkpoints retain source identities, byte/line offsets, normalized events and pending calls; structural mode omits task text and arguments, while text opt-in retains only bounded best-effort-redacted previews. Exact prefix hashes validate reuse; append-only updates parse new bytes, while truncation, replacement, prefix edits, corrupt caches or parser-version changes rebuild that file. Torn final lines are retried after completion. Old reports remain unchanged. `--no-cache` disables checkpoints. Prefix verification still reads historical bytes from disk and is reported separately from the new-byte parsing budget; the first scan remains bounded and can be partial. Checkpoint writes do not upload or change source logs.

Evidence labels distinguish `observation` (recorded event/result), `claim` (Agent self-report), `inference` (static tool references or output candidates), and `unknown` (unconfirmed outcome). These labels do not prove business completion. This design borrows evidence separation and validated snapshot reuse ideas from [REA](https://github.com/morluto/rea/blob/main/docs/cli.md); REA is not a runtime dependency and no process capture or command replay is enabled.

## Insights, not just log counts

The helper now places goal/outcome evidence briefs, repeated-failure review signals, verification gaps and output-review candidates before the timeline. JSON includes `insights` with explicit analysis and knowledge status. The Skill must turn authorized previews into work progress, concrete next actions and reusable lessons, save a private `<date>.insights.md`, read it back, and link it. A lesson needs its problem, method, applicable conditions, verification limits and evidence IDs; Agent claims and file writes do not establish verified success or knowledge value. Long-term memory is never updated automatically.

Default structural privacy still hides semantic content. It supports structural failure/verification findings, not meaningful goal or lesson analysis. Explicit `--include-text` enables bounded best-effort-redacted previews; a tool success never becomes business completion, and repeated tool failures do not establish a shared root cause. Counts and the full timeline remain supporting evidence. The helper performs no model/API calls; semantic analysis is the host Agent's job and its provider policies apply.
