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
