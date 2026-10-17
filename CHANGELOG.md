# Changelog

## Unreleased

- Validate pending-call checkpoint indices before reuse; out-of-range, negative, boolean and non-integer indices rebuild from source instead of crashing or linking the wrong event.

- Rebuild checkpoints after wrong object types, incomplete context arrays or excessive JSON nesting instead of crashing report generation; source logs and prior reports remain unchanged.

- Treat escaped unpaired Unicode surrogates as encoding coverage gaps before normalization, preserving later valid records in both privacy modes. Refresh parser checkpoints with version 0.4.2; existing reports stay unchanged.

- Treat non-text patch arguments as a missing-file-path coverage gap instead of crashing the entire report; valid later events remain available.
- Cover both tool-call and completed MCP envelopes; parser cache version 0.4.1 rebuilds older checkpoints so missing-path gaps are not hidden. Report layout and source data remain unchanged.

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

## 0.5.0

- Replace per-task HTML cards with an aggregate dashboard and four accessible offline SVG charts.
- Separate exact repeated requests, tool frequency and cross-task failure groups; handle empty data without false anomalies.
- Require cross-task synthesis of reusable experience, process improvements and anomaly solutions with evidence.

## 0.5.1

- Fix squeezed timeline columns with fixed metadata widths, wrapped record content and a keyboard-accessible horizontal scroll region on narrow screens.
- Format timestamps for reading while preserving full ISO values in time attributes; highlight linked evidence rows.
