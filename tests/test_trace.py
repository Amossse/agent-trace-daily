import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/trace_daily.py"
spec = importlib.util.spec_from_file_location("trace_daily", SCRIPT)
trace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trace)


class TraceDaily(unittest.TestCase):
    def test_calendar_window(self):
        tz = trace.zone("America/New_York")
        start, end = trace.window("2026-03-08", tz)
        self.assertEqual((end.astimezone(timezone.utc) - start.astimezone(timezone.utc)).total_seconds(), 23 * 3600)
        start, end = trace.window("2026-11-01", tz)
        self.assertEqual((end.astimezone(timezone.utc) - start.astimezone(timezone.utc)).total_seconds(), 25 * 3600)
        start, _ = trace.window("yesterday", trace.zone("+08:00"), datetime.fromisoformat("2026-10-07T00:30:00+08:00"))
        self.assertEqual(start.date().isoformat(), "2026-10-06")
        with self.assertRaises(ValueError):
            trace.stamp("2026-10-06T12:00:00")
        with self.assertRaises(ValueError):
            trace.validate_time("25:00")

    def test_parsers_evidence_and_coverage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            codex = root / "old-filename.jsonl"
            rows = [
                {"timestamp":"2026-10-05T23:00:00+08:00", "type":"session_meta", "payload":{"id":"codex-demo", "cwd":"/workspace/demo"}},
                {"timestamp":"2026-10-05T23:10:00+08:00", "type":"response_item", "payload":{"type":"message", "role":"user", "content":[{"type":"input_text", "text":"Continue a fictional guide"}]}},
                {"timestamp":"2026-10-06T00:00:00+08:00", "type":"response_item", "payload":{"type":"custom_tool_call", "name":"apply_patch", "call_id":"c1", "input":"*** Begin Patch\n*** Add File: guide.md\n+fictional\n*** End Patch"}},
                {"timestamp":"2026-10-06T00:01:00+08:00", "type":"response_item", "payload":{"type":"custom_tool_call_output", "call_id":"c1", "output":"Success. Updated the following files:\nA guide.md"}},
                {"timestamp":"2026-10-06T23:59:00+08:00", "type":"response_item", "payload":{"type":"function_call", "name":"exec_command", "call_id":"c2", "arguments":"{\"cmd\":\"echo fictional\"}"}},
                {"timestamp":"2026-10-07T00:01:00+08:00", "type":"response_item", "payload":{"type":"function_call_output", "call_id":"c2", "output":"{\"exit_code\":0}"}},
                {"timestamp":"2026-10-06T02:00:00+08:00", "type":"event_msg", "payload":{"type":"user_message", "message":"mirror, not another request"}},
            ]
            codex.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
            copied = root / "archive.jsonl"
            copied.write_bytes(codex.read_bytes())
            claude = root / "claude.jsonl"
            claude_rows = [
                {"timestamp":"2026-10-06T09:00:00+08:00", "sessionId":"claude-demo", "cwd":"/workspace/another", "type":"user", "message":{"content":"Read the fictional notes"}},
                {"timestamp":"2026-10-06T09:01:00+08:00", "sessionId":"claude-demo", "type":"assistant", "message":{"content":[{"type":"tool_use", "id":"read1", "name":"Read", "input":{"file_path":"notes.md"}}]}},
                {"timestamp":"2026-10-06T09:02:00+08:00", "sessionId":"claude-demo", "type":"user", "message":{"content":[{"type":"tool_result", "tool_use_id":"read1", "content":"denied", "is_error":True}]}},
            ]
            claude.write_text("\n".join(json.dumps(r) for r in claude_rows) + "\n{broken", encoding="utf-8")
            start, end = trace.window("2026-10-06", trace.zone("+08:00"))
            events, gaps, sources = trace.collect([f"codex:{codex}", f"codex:{copied}", f"claude:{claude}", f"jsonl:{root / 'missing'}"], start, end, 100000, 20)
            self.assertEqual(len(events), 4)
            self.assertEqual([e["status"] for e in events if e["kind"] == "tool"], ["succeeded", "failed", "attempted"])
            data = trace.report(events, gaps, sources, start, end, True)
            self.assertEqual(data["coverage"]["status"], "partial")
            self.assertEqual(data["counts"]["files"], 2)
            self.assertEqual(data["counts"]["failed_tools"], 1)
            self.assertTrue(any(t.get("context") == "Continue a fictional guide" for t in data["tasks"]))
            self.assertEqual(gaps["invalid_json_or_encoding"], 1)
            self.assertEqual(gaps["missing_source"], 1)
            structural = json.dumps(trace.report(events, gaps, sources, start, end))
            self.assertNotIn("Continue a fictional", structural)
            self.assertNotIn("notes.md", structural)
            self.assertNotIn(str(root), structural)
            self.assertTrue(all(not t["summaries"] for t in data["tasks"]))
            _, capped, _ = trace.collect([f"codex:{codex}"], start, end, 5, 20)
            self.assertGreater(capped["byte_limit_reached"], 0)

    def test_recent_priority_window_gaps_and_wrapper_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            old, recent = root / "old.jsonl", root / "recent.jsonl"
            rows = [
                {"timestamp": "2026-10-05T01:00:00Z", "type": "event_msg", "payload": {"type": "future_unknown"}},
                {"timestamp": "2026-10-06T01:00:00Z", "type": "session_meta", "payload": {"id": "fictional", "cwd": "/fictional"}},
                {"timestamp": "2026-10-06T01:01:00Z", "type": "response_item", "payload": {"type": "function_call", "name": "functions.exec", "call_id": "wrapper", "arguments": 'await tools.apply_patch("fictional patch"); tools.exec_command({cmd: "fictional"});'}},
                {"timestamp": "2026-10-06T01:02:00Z", "type": "response_item", "payload": {"type": "function_call_output", "call_id": "wrapper", "output": "Script completed"}},
                {"timestamp": "2026-10-06T01:03:00Z", "type": "token_usage_record", "payload": {}},
                {"timestamp": "2026-10-06T01:04:00Z", "type": "world_state", "payload": {}},
                {"timestamp": "2026-10-06T01:05:00Z", "type": "compacted", "payload": {}},
                {"timestamp": "2026-10-06T01:06:00Z", "type": "event_msg", "payload": {"type": "thread_settings_applied"}},
            ]
            recent.write_text("".join(json.dumps(row) + "\n" for row in rows))
            old.write_text(json.dumps({"timestamp": "2026-10-06T02:00:00Z", "kind": "task", "session_id": "old-session", "text": "fictional"}) + "\n")
            os.utime(old, (1, 1))
            os.utime(recent, (2, 2))
            start, end = trace.window("2026-10-06", trace.zone("UTC"))
            sources = [f"jsonl:{old}", f"codex:{recent}"]
            events, gaps, inputs = trace.collect(sources, start, end, recent.stat().st_size, 20)
            self.assertEqual(len(events), 1)
            self.assertEqual(inputs[0]["location"], str(recent))
            self.assertNotIn("unsupported_codex_event", gaps)
            self.assertEqual(events[0]["referenced_tools"], ["apply_patch", "exec_command"])
            self.assertEqual(events[0]["status"], "unknown")
            self.assertEqual(events[0]["files"], [])
            data = trace.report(events, gaps, inputs, start, end)
            self.assertEqual(data["coverage"]["scan"]["bytes"], recent.stat().st_size)
            self.assertIn("不是全天总量", trace.markdown(data))
            self.assertIn("不证明执行或成功", trace.markdown(data))
            events, gaps, _ = trace.collect(sources, start, end, 100000, 20)
            self.assertEqual(len(events), 2)  # Old mtime does not exclude same-day events.
            self.assertEqual(dict(gaps), {"opaque_tool_wrapper": 1})

    def test_incremental_append_cross_day_and_invalidation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source, cache = root / "trace.jsonl", root / "cache"
            rows = [
                {"timestamp": "2026-10-05T23:00:00Z", "type": "session_meta", "payload": {"id": "demo", "cwd": "/fictional"}},
                {"timestamp": "2026-10-05T23:01:00Z", "type": "response_item", "payload": {"type": "message", "role": "user", "content": "PRIVATE_TASK_MARKER"}},
                {"timestamp": "2026-10-05T23:02:00Z", "type": "response_item", "payload": {"type": "function_call", "name": "Read", "call_id": "pending", "arguments": {"path": "notes.md", "secret": "PRIVATE_ARG_MARKER"}}},
            ]
            source.write_text("".join(json.dumps(row) + "\n" for row in rows))
            sources = [f"codex:{source}"]
            start, end = trace.window("2026-10-05", trace.zone("UTC"))
            trace.collect(sources, start, end, 100000, 10, cache)
            saved = next(cache.glob("*.json")).read_text()
            self.assertNotIn("PRIVATE_TASK_MARKER", saved)
            self.assertNotIn("PRIVATE_ARG_MARKER", saved)
            if sys.platform != "win32":
                self.assertEqual(next(cache.glob("*.json")).stat().st_mode & 0o777, 0o600)
            result = {"timestamp": "2026-10-06T00:01:00Z", "type": "response_item", "payload": {"type": "function_call_output", "call_id": "pending", "output": {"exit_code": 0}}}
            appended = json.dumps(result) + "\n"
            with source.open("a") as handle:
                handle.write(appended)
            start, end = trace.window("2026-10-06", trace.zone("UTC"))
            events, gaps, inputs = trace.collect(sources, start, end, 100000, 10, cache)
            self.assertEqual(inputs[0]["scanned_bytes"], len(appended.encode()))
            self.assertGreater(inputs[0]["reused_bytes"], 0)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["status"], "succeeded")
            self.assertTrue(events[0]["started_before_window"])
            self.assertFalse(gaps)
            data = trace.report(events, gaps, inputs, start, end)
            self.assertEqual(data["timeline"][0]["outcome_evidence_level"], "observation")
            full, full_gaps, _ = trace.collect(sources, start, end, 100000, 10)
            self.assertEqual([(e["timestamp"], e["status"], e["files"]) for e in events],
                             [(e["timestamp"], e["status"], e["files"]) for e in full])
            self.assertEqual(gaps, full_gaps)
            _, _, inputs = trace.collect(sources, start, end, 100000, 10, cache)
            self.assertEqual(inputs[0]["scanned_bytes"], 0)
            # Source aliases can shift when a newer source is discovered.
            other = root / "newer.jsonl"
            other.write_text(json.dumps({"timestamp": "2026-10-06T00:00:00Z", "kind": "task", "session_id": "other"}) + "\n")
            os.utime(source, (1, 1))
            os.utime(other, (2, 2))
            shifted, _, _ = trace.collect([f"jsonl:{other}", *sources], start, end, 100000, 10, cache)
            tool = next(e for e in shifted if e["kind"] == "tool")
            self.assertEqual(tool["evidence"], "S2:3")
            self.assertEqual(tool["result_evidence"], "S2:4")
            self.assertEqual(tool["task"], "S2:2")
            # Text opt-in has a separate checkpoint and still redacts credential previews.
            rows[1]["payload"]["content"] = "token=fictionalcredential"
            text_source = root / "text.jsonl"
            text_source.write_text("".join(json.dumps(row) + "\n" for row in rows))
            trace.collect([f"codex:{text_source}"], start, end, 100000, 10, cache, True)
            self.assertTrue(all("fictionalcredential" not in p.read_text() for p in cache.glob("*.json")))
            # A same-size prefix edit followed by append must invalidate, not reuse stale success.
            source.write_text(source.read_text().replace('"exit_code": 0', '"exit_code": 1') + appended)
            events, _, inputs = trace.collect(sources, start, end, 100000, 10, cache)
            self.assertEqual(inputs[0]["reused_bytes"], 0)
            # Truncation also discards cached events and pending calls.
            source.write_text(json.dumps(result) + "\n")
            events, gaps, inputs = trace.collect(sources, start, end, 100000, 10, cache)
            self.assertFalse(events)
            self.assertEqual(inputs[0]["reused_bytes"], 0)
            self.assertEqual(gaps["orphan_tool_result"], 1)

    def test_incremental_budget_torn_tail_and_evidence_levels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source, cache = root / "demo.jsonl", root / "cache"
            rows = [
                {"timestamp": "2026-10-06T01:00:00Z", "kind": "task", "session_id": "demo", "task_id": "one", "text": "fictional"},
                {"timestamp": "2026-10-06T01:01:00Z", "kind": "summary", "session_id": "demo", "task_id": "one", "text": "done"},
                {"timestamp": "2026-10-06T01:02:00Z", "kind": "tool", "session_id": "demo", "task_id": "one", "operation": "write", "files": ["demo.md"], "status": "succeeded"},
            ]
            lines = [json.dumps(row) + "\n" for row in rows]
            source.write_text("".join(lines[:2]) + lines[2][:-1])
            start, end = trace.window("2026-10-06", trace.zone("UTC"))
            sources = [f"jsonl:{source}"]
            events, gaps, _ = trace.collect(sources, start, end, len(lines[0]), 10, cache)
            self.assertEqual(len(events), 1)
            self.assertIn("byte_limit_reached", gaps)
            events, gaps, _ = trace.collect(sources, start, end, 100000, 10, cache)
            self.assertEqual(len(events), 2)
            self.assertNotIn("byte_limit_reached", gaps)
            self.assertIn("incomplete_last_line", gaps)
            with source.open("a") as handle:
                handle.write("\n")
            events, gaps, inputs = trace.collect(sources, start, end, 100000, 10, cache)
            self.assertEqual(len(events), 3)
            self.assertFalse(gaps)
            data = trace.report(events, gaps, inputs, start, end)
            self.assertEqual([e["evidence_level"] for e in data["timeline"]], ["observation", "claim", "observation"])
            self.assertEqual(data["artifacts"][0]["evidence_level"], "inference")
            self.assertEqual(data["artifacts"][0]["evidence"], ["S1:3"])
            # Invalid cache content is safely rebuilt from the source.
            next(cache.glob("*.json")).write_text("{broken")
            events, gaps, inputs = trace.collect(sources, start, end, 100000, 10, cache)
            self.assertEqual(len(events), 3)
            self.assertEqual(inputs[0]["reused_bytes"], 0)

    def test_install_schedule_and_public_demo(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "示例空间"
            root.mkdir()
            destination, state = root / "skills/agent-trace-daily", root / "state"
            command = [sys.executable, str(SCRIPT), "install", "--agent", "generic", "--source", f"jsonl:{ROOT / 'examples/demo.jsonl'}", "--skill-dir", str(destination), "--state-dir", str(state), "--timezone", "+08:00"]
            result = subprocess.run(command, capture_output=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING":"cp1252"})
            self.assertEqual(result.returncode, 0, result.stderr)
            setup = json.loads(result.stdout)
            self.assertEqual(setup["schedule_status"], "pending")
            self.assertIn("11:00", setup["agent_instruction"])
            self.assertIn("daily", (destination / "LOCAL_SETUP.md").read_text())
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            config = state / "config.json"
            scheduling = [sys.executable, str(destination / "scripts/trace_daily.py"), "schedule", "--config", str(config)]
            changed = subprocess.run(scheduling + ["--time", "09:30"], capture_output=True, encoding="utf-8")
            self.assertEqual(changed.returncode, 0, changed.stderr)
            self.assertEqual(json.loads(changed.stdout)["schedule"]["status"], "needs-update")
            # This synthetic ID tests local attestation only, never claims a real timer.
            recorded = subprocess.run(scheduling + ["--confirm-id", "fictional-test-only"], capture_output=True, encoding="utf-8")
            self.assertEqual(recorded.returncode, 0, recorded.stderr)
            run = [sys.executable, str(destination / "scripts/trace_daily.py"), "report", "--config", str(config), "--date", "2026-10-06", "--include-text"]
            result = subprocess.run(run, capture_output=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["counts"]["events"], 7)
            self.assertEqual(summary["counts"]["tasks"], 2)
            self.assertEqual(summary["coverage"], "within-configured-logs")
            md = Path(summary["markdown"])
            before = md.read_bytes()
            self.assertIn("Create a fictional study guide", before.decode())
            self.assertNotEqual(subprocess.run(run, capture_output=True).returncode, 0)
            self.assertEqual(md.read_bytes(), before)
            if sys.platform != "win32":
                self.assertEqual(md.stat().st_mode & 0o777, 0o600)
                link = root / "linked"
                link.symlink_to(state, target_is_directory=True)
                with self.assertRaises(ValueError):
                    trace.safe_path(link / "config.json")

    def test_redaction_and_input_failure(self):
        sensitive = "Bearer fictionalcredential123 token=fictionalvalue123 person@example.com https://example.com/private?x=1\n# injected"
        clean = trace.redact(sensitive)
        for fragment in ("fictionalcredential123", "fictionalvalue123", "person@example.com", "https://", "\n"):
            self.assertNotIn(fragment, clean)
        self.assertEqual(trace.success({"exit_code":0}), "succeeded")
        self.assertEqual(trace.success({"exit_code":1}), "failed")
        self.assertEqual(trace.success("unknown tool output"), "unknown")
        result = subprocess.run([sys.executable, str(SCRIPT), "report", "--source", "not-a-source"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
