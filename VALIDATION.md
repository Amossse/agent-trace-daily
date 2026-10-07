# Validation record

Date: 2026-10-07. Tests and the model acceptance probe used only original fictional events, temporary installations/configs and temporary reports. Real transcripts, host logs, private configs and generated real reports are not publication assets.

## Verified locally

- Standard-library unittest checks passed: IANA DST 23/25-hour days; timezone-aware yesterday; task continuation across midnight; Codex call/result pairing; Claude failed reads; duplicate active/archive records; late results not proving yesterday's success; invalid JSON and missing sources; scan budget gaps; structural privacy; best-effort redaction; installation refusal on existing directories/configs; 11:00 onboarding handoff; 09:30 request state; local schedule-ID attestation; installed-copy report execution; output no-overwrite; POSIX 0600; symlink refusal; Unicode paths with a forced legacy stdout encoding.
- Official Skill Creator `quick_validate.py`: valid. YAML was an isolated validation dependency, not a Skill runtime requirement.
- Ruff `--isolated --select E9,F`: passed correctness-oriented checks. This is not a claim that every optional style rule or security scanner passes.
- Standalone temporary installation and fictional example: generated Markdown and JSON with 2 tasks, 7 selected normalized events, 1 working directory, 2 explicit files and 1 failed tool call. Outputs stayed outside the checkout and source logs were unchanged.
- Fresh read-only Codex CLI model probe: explicitly read the installed Skill, scheduling/format references, fictional config and report. Correctly reported 11:00 Asia/Shanghai and `schedule_pending`, did not claim a real timer existed, summarized the fixture counts with evidence boundaries, and described changing the existing task rather than duplicating it. No network, real timer creation or source/project write was permitted. This does not verify automatic discovery on every host.
- Gitleaks publication-directory scan: no findings. Internal-identifier review: no findings. Source contains only generic home-path redaction patterns, not actual developer/user home paths. Raw model/host logs and generated private artifacts are excluded.
- Chinese delivery review: commands, version, times, numeric limits, evidence and privacy boundaries retained. Mechanical Chinese punctuation/em-dash/meta-phrase scan of Chinese README and bilingual draft: zero findings; no extra efficacy or complete-coverage claim introduced.

## Not established

No real recurring timer was created as part of development. The installation feature is a tested handoff to the host Agent/native scheduler; successful native scheduling requires actual tool read-back in the user's installation environment. Local schedule state is not independent verification.

Not verified: every Agent/host's automatic Skill discovery, every historical/future transcript version, complete real-world execution coverage, opaque shell/JS file effects, privacy against all inputs, encrypted storage, native timers firing on sleeping machines, or delivery to external apps. The helper has no network/model client, replay engine, silent cron installer or automatic retention cleanup.

CI runs the fictional Python checks on Linux/macOS/Windows, with timezone data for DST tests. Release-time CI and public-clone checks are reported only after actual completion; structural tests alone do not prove a live daily schedule.
