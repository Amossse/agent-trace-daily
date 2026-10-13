# Changelog

## Unreleased

- Require integer exit codes; booleans, floats and strings remain unknown instead of becoming success/failure claims. Parsed JSON objects do not fall back to textual exit-code guessing.
- Bump the helper version to 0.3.1 so checkpoints rebuild under the corrected result rules; existing reports remain untouched. No new release is published.

- Measure incremental test budgets and appended bytes from actual files, including Windows CRLF newlines.
- Add LF/CRLF fixtures with multibyte UTF-8 text to check bounded checkpoint resumption; runtime behavior is unchanged.

## 0.1.0 - 2026-10-07

- Local Codex, Claude Code and generic JSONL normalization and yesterday reporting.
- Task/project/file/output/failure sections, complete selected timeline and explicit gaps.
- Installation handoff to native daily 11:00 scheduling, configurable time/timezone.
- Structural privacy default, optional private redacted previews, no automatic uploads.
- Synthetic parser, time-boundary, installer/schedule-state and no-overwrite tests.

## 0.1.1

- Prioritize recently modified logs across sources without excluding old sessions.
- Scope timestamped parser gaps to the reporting day and recognize current Codex metadata.
- Show static exec tool references without inferring execution; expose scan totals and partial-coverage warnings.

## 0.2.0

- Add private incremental checkpoints with exact prefix validation, pending-call continuity, safe rebuilds and `--no-cache`.
- Separate newly parsed, reused and prefix-verification bytes; retry incomplete final lines and resume bounded scans.
- Label observations, Agent claims, inferences and unknown outcomes; keep structural caches free of task text and arguments.

## 0.3.0

- Put goal/outcome evidence briefs, failure review signals and verification gaps before the timeline.
- Require the Skill to save evidence-backed work insights and reusable knowledge candidates in private daily insight artifacts.
- Preserve structural privacy, explicit semantic opt-in, no-overwrite outputs and separate authorization for long-term memory.

## 0.4.0

- Scan the entire configured source scope by default; retain explicit optional ceilings and raise record support to 64 MiB.
- Parse current Codex completed command/file/MCP records, reconcile call IDs and exclude developer instructions.
- Generate safe offline HTML analysis briefs and support evidence-backed host analysis in a final .analysis.html.
