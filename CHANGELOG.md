# Changelog

## Unreleased

- Close the staged output descriptor if stream construction fails, retaining staging cleanup and existing target bytes. Cover descriptor ownership and successful retry; no parser or cache format change.

- Reject duplicate JSON fields in incremental checkpoints at every depth and rebuild from the configured source rather than reusing ambiguous cached evidence. Cover duplicate version/offset fields, unchanged source bytes and subsequent valid reuse; no source/report mutation or cache authenticity guarantee.

- Reject duplicate JSON fields in report/schedule configuration at every object depth instead of silently choosing the last value. Ambiguous privacy settings cannot enable text previews or rewrite scheduling config; preserve the original config, logs and absent outputs. No timer changes or checkpoint migration.

- Keep malformed non-text FileChange status unknown and record `invalid_tool_status` instead of crashing on array/object status. Preserve structured path candidates and following events, mark coverage partial, and rebuild older checkpoints with parser 0.4.7; existing logs and reports stay unchanged.

- Validate completed Codex item types before set-based dispatch so malformed arrays/objects become unsupported-item gaps instead of aborting reports. Preserve following events and partial coverage; cover uncached/new/reused/legacy-version scans and bump the checkpoint parser to 0.4.6.

- Keep parsed non-object result JSON unknown rather than interpreting its nested text as exit evidence. Preserve explicit host status, plain shell text and object-result handling; cover uncached/new/reused scans and rebuild older checkpoints with parser version 0.4.5.

- Reject duplicate fields inside embedded tool-argument/result JSON without falling back to guessed paths or exit codes. Record unreadable-tool gaps, preserve later events, and rebuild older checkpoints with parser version 0.4.4. Cover ordinary and completed MCP calls with uncached/new/reused checkpoints; explicit host status remains separate evidence.

- Reject duplicate JSON fields at every object depth in source JSONL records instead of silently reinterpreting roles/types. Mark rejected records as invalid-JSON gaps, preserve later events, and bump the parser checkpoint version so legacy caches rebuild. Source logs and prior reports remain unchanged.

- Treat excessively nested tool-argument JSON as an unreadable-arguments gap instead of crashing. Preserve following events without guessing file paths; cover regular and completed MCP calls in uncached and checkpoint scans.

- Keep reports running when a tool-result string contains excessively nested JSON. Record an unreadable-result gap, leave its outcome unknown instead of inferring a nested exit code, and preserve later records with and without checkpoints.

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
