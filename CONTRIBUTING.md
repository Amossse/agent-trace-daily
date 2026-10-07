# Contributing

Report a demonstrated parser gap or scheduling ambiguity with a fictional minimal JSONL case, expected events, timezone and boundary. Never paste personal/internal logs, paths, real reports, provider configuration or credentials. New exporters should follow the generic JSONL contract unless a real supported format needs an adapter.

Keep stdlib-first changes narrow. Preserve read-only sources, explicit scan budgets, unknown/attempted versus confirmed status, no-overwrite outputs, privacy defaults and honest coverage claims. Do not add telemetry, background upload or automatic cleanup. Run `python -m unittest discover -s tests -v`; add a regression case when fixing behavior. CI checks Linux/macOS/Windows and installs `tzdata` for timezone tests only.

Review docs in both languages when changing installation, privacy, evidence or scheduling. Declare what was actually verified; a mock schedule test is not a real daily timer. Contributions are under MIT.
