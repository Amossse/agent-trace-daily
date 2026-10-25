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
    def test_non_text_file_change_status_keeps_paths_but_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "trace.jsonl"
            rows = [{"timestamp": "2026-10-06T01:00:00Z", "type": "event_msg", "payload": {
                "type": "item_completed", "item": {"type": "FileChange", "id": f"fictional-{index}",
                "changes": {"fictional.md": {}}, "status": status}}}
                for index, status in enumerate(([], {}, True, 42))]
            rows.append({"timestamp": "2026-10-06T01:01:00Z", "type": "response_item", "payload": {
                "type": "message", "role": "user", "content": "Fictional follow-up"}})
            source.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding="utf-8")
            start, end = trace.window("2026-10-06", trace.zone("UTC"))
            cache = root / "cache"
            for destination in (None, cache, cache):
                events, gaps, inputs = trace.collect([f"codex:{source}"], start, end, 100000, 10, destination)
                self.assertEqual(len(events), 5)
                self.assertTrue(all(e["status"] == "unknown" and e["files"] == ["fictional.md"]
                                    for e in events[:4]))
                self.assertEqual(events[-1]["kind"], "task")
                self.assertEqual(gaps["invalid_tool_status"], 4)
                self.assertEqual(trace.report(events, gaps, inputs, start, end)["coverage"]["status"], "partial")
            self.assertGreater(inputs[0]["reused_bytes"], 0)
            checkpoint = next(cache.glob("*.json"))
            legacy = json.loads(checkpoint.read_text(encoding="utf-8"))
            legacy["version"] = "0.4.6"
            legacy["state"]["day_gaps"] = {}
            checkpoint.write_text(json.dumps(legacy), encoding="utf-8")
            _, gaps, inputs = trace.collect([f"codex:{source}"], start, end, 100000, 10, cache)
            self.assertEqual(inputs[0]["reused_bytes"], 0)
            self.assertEqual(gaps["invalid_tool_status"], 4)

    def test_completed_item_type_must_be_text_before_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "trace.jsonl"
            rows = [{"timestamp": "2026-10-06T01:00:00Z", "type": "event_msg", "payload": {
                "type": "item_completed", "item": {"type": kind, "id": f"fictional-{index}"}}}
                for index, kind in enumerate(([], {}, 42, None))]
            rows.append({"timestamp": "2026-10-06T01:01:00Z", "type": "response_item", "payload": {
                "type": "message", "role": "user", "content": "Fictional follow-up"}})
            source.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding="utf-8")
            start, end = trace.window("2026-10-06", trace.zone("UTC"))
            cache = root / "cache"
            for destination in (None, cache, cache):
                events, gaps, inputs = trace.collect([f"codex:{source}"], start, end, 100000, 10, destination)
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0]["kind"], "task")
                self.assertEqual(gaps["unsupported_codex_completed_item"], 4)
                self.assertEqual(trace.report(events, gaps, inputs, start, end)["coverage"]["status"], "partial")
            self.assertGreater(inputs[0]["reused_bytes"], 0)
            checkpoint = next(cache.glob("*.json"))
            legacy = json.loads(checkpoint.read_text(encoding="utf-8"))
            legacy["version"] = "0.4.5"
            legacy["state"]["day_gaps"] = {}
            checkpoint.write_text(json.dumps(legacy), encoding="utf-8")
            _, gaps, inputs = trace.collect([f"codex:{source}"], start, end, 100000, 10, cache)
            self.assertEqual(inputs[0]["reused_bytes"], 0)
            self.assertEqual(gaps["unsupported_codex_completed_item"], 4)

    def test_non_object_result_json_is_not_textual_exit_evidence(self):
        for value in ([{"exit_code": 0}], ["Process exited with code 1"], "Process exited with code 0"):
            with self.subTest(value=value):
                self.assertEqual(trace.success(json.dumps(value)), "unknown")
                self.assertEqual(trace.success(json.dumps(value), explicit_error=False), "succeeded")
        self.assertEqual(trace.success('Process exited with code 0'), "succeeded")
        self.assertEqual(trace.success('{"exit_code":1}'), "failed")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "trace.jsonl"
            rows = [
                {"timestamp": "2026-10-06T01:00:00Z", "type": "response_item", "payload": {
                    "type": "function_call", "name": "exec_command", "call_id": "fictional", "arguments": {}}},
                {"timestamp": "2026-10-06T01:01:00Z", "type": "response_item", "payload": {
                    "type": "function_call_output", "call_id": "fictional", "output": '[{"exit_code":0}]'}},
                {"timestamp": "2026-10-06T01:02:00Z", "type": "response_item", "payload": {
                    "type": "message", "role": "user", "content": "Fictional follow-up"}},
            ]
            source.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding="utf-8")
            start, end = trace.window("2026-10-06", trace.zone("UTC"))
            cache = root / "cache"
            for destination in (None, cache, cache):
                events, _, _ = trace.collect([f"codex:{source}"], start, end, 100000, 10, destination)
                self.assertEqual(events[0]["status"], "unknown")
                self.assertEqual(events[1]["kind"], "task")
            checkpoint = next(cache.glob("*.json"))
            legacy = json.loads(checkpoint.read_text(encoding="utf-8"))
            legacy["version"] = "0.4.4"
            checkpoint.write_text(json.dumps(legacy), encoding="utf-8")
            events, _, inputs = trace.collect([f"codex:{source}"], start, end, 100000, 10, cache)
            self.assertEqual(events[0]["status"], "unknown")
            self.assertEqual(inputs[0]["reused_bytes"], 0)

    def test_duplicate_embedded_tool_fields_do_not_invent_files_or_success(self):
        arguments = '{"path":"fictional-a.md","path":"fictional-b.md"}'
        result = '{"exit_code":1,"exit_code":0}'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "trace.jsonl"
            rows = [
                {"timestamp": "2026-10-06T01:00:00Z", "type": "response_item", "payload": {
                    "type": "function_call", "name": "read_file", "call_id": "fictional", "arguments": arguments}},
                {"timestamp": "2026-10-06T01:01:00Z", "type": "response_item", "payload": {
                    "type": "function_call_output", "call_id": "fictional", "output": result}},
                {"timestamp": "2026-10-06T01:02:00Z", "type": "event_msg", "payload": {
                    "type": "item_completed", "item": {"type": "McpToolCall", "id": "fictional-mcp",
                    "server": "fictional", "tool": "read_file", "arguments": arguments, "result": result}}},
                {"timestamp": "2026-10-06T01:03:00Z", "type": "response_item", "payload": {
                    "type": "message", "role": "user", "content": "Fictional follow-up"}},
            ]
            source.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding="utf-8")
            start, end = trace.window("2026-10-06", trace.zone("UTC"))
            cache = root / "cache"
            for destination in (None, cache, cache):
                events, gaps, inputs = trace.collect([f"codex:{source}"], start, end, 100000, 10, destination)
                self.assertEqual(len(events), 3)
                self.assertTrue(all(not event["files"] for event in events))
                self.assertEqual([event["status"] for event in events[:2]], ["unknown", "unknown"])
                self.assertEqual(gaps["unreadable_tool_arguments_json"], 2)
                self.assertEqual(gaps["unreadable_tool_result_json"], 2)
                self.assertEqual(events[-1]["kind"], "task")
                self.assertEqual(trace.report(events, gaps, inputs, start, end)["coverage"]["status"], "partial")
            checkpoint = next(cache.glob("*.json"))
            legacy = json.loads(checkpoint.read_text(encoding="utf-8"))
            legacy["version"] = "0.4.3"
            legacy["state"]["day_gaps"] = {}
            checkpoint.write_text(json.dumps(legacy), encoding="utf-8")
            _, gaps, inputs = trace.collect([f"codex:{source}"], start, end, 100000, 10, cache)
            self.assertEqual(gaps["unreadable_tool_result_json"], 2)
            self.assertEqual(inputs[0]["reused_bytes"], 0)

    def test_duplicate_record_fields_are_gaps_not_reinterpreted_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "trace.jsonl"
            row = {"timestamp": "2026-10-06T01:00:00Z", "type": "response_item", "payload": {
                "type": "message", "role": "user", "content": "Fictional ambiguous marker"}}
            raw = json.dumps(row)
            source.write_text(raw.replace('"role": "user"', '"role":"system","role":"user"') + '\n'
                              + raw.replace('"type": "response_item"', '"type":"unknown","type":"response_item"') + '\n'
                              + json.dumps({**row, "payload": {"type": "message", "role": "user",
                                                            "content": "Fictional valid follow-up"}}) + '\n', encoding="utf-8")
            start, end = trace.window("2026-10-06", trace.zone("UTC"))
            cache = root / "cache"
            for destination in (None, cache, cache):
                events, gaps, inputs = trace.collect([f"codex:{source}"], start, end, 100000, 10, destination, keep_text=True)
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0]["text"], "Fictional valid follow-up")
                self.assertEqual(gaps["invalid_json_or_encoding"], 2)
                self.assertEqual(trace.report(events, gaps, inputs, start, end)["coverage"]["status"], "partial")
            checkpoint = next(cache.glob("*.json"))
            legacy = json.loads(checkpoint.read_text(encoding="utf-8"))
            legacy["version"] = "0.4.2"
            legacy["state"]["day_gaps"] = {}
            checkpoint.write_text(json.dumps(legacy), encoding="utf-8")
            _, gaps, inputs = trace.collect([f"codex:{source}"], start, end, 100000, 10, cache, keep_text=True)
            self.assertEqual(gaps["invalid_json_or_encoding"], 2)
            self.assertEqual(inputs[0]["reused_bytes"], 0)

    def test_deep_tool_arguments_are_gaps_and_do_not_stop_following_events(self):
        nested = '[' * 100000 + '"fictional"' + ']' * 100000
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "trace.jsonl"
            rows = [
                {"timestamp": "2026-10-06T01:00:00Z", "type": "response_item", "payload": {
                    "type": "function_call", "name": "read_file", "call_id": "fictional", "arguments": nested}},
                {"timestamp": "2026-10-06T01:01:00Z", "type": "event_msg", "payload": {
                    "type": "item_completed", "item": {"type": "McpToolCall", "id": "fictional-mcp",
                    "server": "fictional", "tool": "read_file", "arguments": nested, "result": {}}}},
                {"timestamp": "2026-10-06T01:02:00Z", "type": "response_item", "payload": {
                    "type": "message", "role": "user", "content": "Fictional follow-up"}},
            ]
            source.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding="utf-8")
            start, end = trace.window("2026-10-06", trace.zone("UTC"))
            for cache in (None, root / "cache", root / "cache"):
                events, gaps, inputs = trace.collect([f"codex:{source}"], start, end, 1000000, 10, cache)
                self.assertEqual(len(events), 3)
                self.assertEqual(events[-1]["kind"], "task")
                self.assertTrue(all(not event["files"] for event in events))
                self.assertEqual(gaps["unreadable_tool_arguments_json"], 2)
                self.assertEqual(trace.report(events, gaps, inputs, start, end)["coverage"]["status"], "partial")

    def test_deeply_nested_tool_result_is_unknown_and_later_records_survive(self):
        # A shallow JSONL envelope can contain JSON deeper than the decoder accepts.
        nested = '[' * 100000 + '{"exit_code":0}' + ']' * 100000
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "trace.jsonl"
            rows = [
                {"timestamp": "2026-10-06T01:00:00Z", "type": "response_item", "payload": {
                    "type": "function_call", "name": "exec_command", "call_id": "fictional", "arguments": {}}},
                {"timestamp": "2026-10-06T01:01:00Z", "type": "response_item", "payload": {
                    "type": "function_call_output", "call_id": "fictional", "output": nested}},
                {"timestamp": "2026-10-06T01:02:00Z", "type": "response_item", "payload": {
                    "type": "message", "role": "user", "content": "Fictional follow-up"}},
            ]
            source.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding="utf-8")
            start, end = trace.window("2026-10-06", trace.zone("UTC"))
            for cache in (None, root / "cache", root / "cache"):
                events, gaps, inputs = trace.collect([f"codex:{source}"], start, end, 1000000, 10, cache)
                self.assertEqual(len(events), 2)
                self.assertEqual(events[0]["status"], "unknown")
                self.assertEqual(events[1]["kind"], "task")
                self.assertEqual(gaps["unreadable_tool_result_json"], 1)
                self.assertEqual(trace.report(events, gaps, inputs, start, end)["coverage"]["status"], "partial")

    def test_corrupt_pending_indices_rebuild_instead_of_crashing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "trace.jsonl"
            row = {"timestamp": "2026-10-06T01:00:00Z", "type": "response_item", "payload": {
                "type": "function_call", "call_id": "fictional-call", "name": "exec_command", "arguments": {}}}
            source.write_text(json.dumps(row) + "\n", encoding="utf-8")
            start, end = trace.window("2026-10-06", trace.zone("UTC"))
            cache = root / "cache"
            trace.collect([f"codex:{source}"], start, end, 100000, 10, cache)
            checkpoint = next(cache.glob("*.json"))
            saved = json.loads(checkpoint.read_text(encoding="utf-8"))
            for index in (999, -1, True, "0"):
                saved["state"]["pending"]["fictional-call"] = index
                checkpoint.write_text(json.dumps(saved), encoding="utf-8")
                events, gaps, inputs = trace.collect([f"codex:{source}"], start, end, 100000, 10, cache)
                self.assertEqual(len(events), 1)
                self.assertFalse(gaps)
                self.assertEqual(inputs[0]["reused_bytes"], 0)

    def test_structurally_corrupt_checkpoints_rebuild_from_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "trace.jsonl"
            source.write_text(json.dumps({"timestamp": "2026-10-06T01:00:00Z", "type": "response_item",
                                         "payload": {"type": "message", "role": "user", "content": "fictional task"}})
                              + "\n", encoding="utf-8")
            start, end = trace.window("2026-10-06", trace.zone("UTC"))
            sources = [f"codex:{source}"]
            cache = root / "cache"
            trace.collect(sources, start, end, 100000, 10, cache)
            checkpoint = next(cache.glob("*.json"))
            saved = json.loads(checkpoint.read_text(encoding="utf-8"))
            saved["state"]["context"] = []
            for raw in ("[]", json.dumps(saved), "[" * 5000 + "]" * 5000):
                with self.subTest(shape=raw[:20]):
                    checkpoint.write_text(raw, encoding="utf-8")
                    events, gaps, inputs = trace.collect(sources, start, end, 100000, 10, cache)
                    self.assertEqual(len(events), 1)
                    self.assertFalse(gaps)
                    self.assertEqual(inputs[0]["reused_bytes"], 0)

    def test_unpaired_surrogates_are_gaps_and_later_events_survive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "trace.jsonl"
            rows = [
                {"timestamp": "2026-10-06T01:00:00Z", "type": "response_item", "payload": {
                    "type": "message", "role": "user", "content": "\ud800"}},
                {"timestamp": "2026-10-06T01:01:00Z", "type": "response_item", "payload": {
                    "type": "function_call", "name": "read_file", "call_id": "fictional",
                    "arguments": {"path": "\udfff"}}},
                {"timestamp": "2026-10-06T01:02:00Z", "type": "response_item", "payload": {
                    "type": "message", "role": "user", "content": "Fictional note \U0001f4da"}},
            ]
            source.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            start, end = trace.window("2026-10-06", trace.zone("UTC"))
            for keep_text in (False, True):
                for _ in range(2):
                    events, gaps, inputs = trace.collect([f"codex:{source}"], start, end, 100000, 10,
                                                        root / str(keep_text), keep_text=keep_text)
                    self.assertEqual(len(events), 1)
                    self.assertEqual(gaps["invalid_json_or_encoding"], 2)
                    self.assertEqual(trace.report(events, gaps, inputs, start, end)["coverage"]["status"], "partial")

    def test_non_text_patch_is_a_gap_not_a_report_crash(self):
        for value in (None, 42, [], {}):
            with self.subTest(value=value):
                self.assertEqual(trace.tool_info("apply_patch", {"patch": value})[:2], ("write", []))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "trace.jsonl"
            rows = [
                {"timestamp": "2026-10-06T01:00:00Z", "type": "response_item", "payload": {
                    "type": "function_call", "name": "apply_patch", "call_id": "demo", "arguments": {"patch": None}}},
                {"timestamp": "2026-10-06T01:01:00Z", "type": "response_item", "payload": {
                    "type": "message", "role": "user", "content": "fictional follow-up"}},
                {"timestamp": "2026-10-06T01:02:00Z", "type": "event_msg", "payload": {
                    "type": "item_completed", "item": {"type": "McpToolCall", "id": "mcp-demo",
                    "server": "fictional", "tool": "apply_patch", "arguments": {"patch": []}, "result": {}}}},
            ]
            source.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            start, end = trace.window("2026-10-06", trace.zone("UTC"))
            events, gaps, inputs = trace.collect([f"codex:{source}"], start, end, 100000, 10, root / "cache")
            self.assertEqual(len(events), 3)
            self.assertEqual(gaps["missing_structured_file_path"], 2)
            self.assertEqual(trace.report(events, gaps, inputs, start, end)["coverage"]["status"], "partial")

    def test_exit_code_requires_an_integer_not_boolean(self):
        for code in (False, True, 0.0, "0", None):
            with self.subTest(code=code):
                self.assertEqual(trace.success({"exit_code": code}), "unknown")
                self.assertEqual(trace.success(json.dumps({"exit_code": code})), "unknown")
        self.assertEqual(trace.success({"exit_code": 0}), "succeeded")
        self.assertEqual(trace.success({"exit_code": 1}), "failed")
        self.assertEqual(trace.success("Process exited with code 0"), "succeeded")
        for text in ("Process exited with code 0.5", "exit_code: 0e1"):
            self.assertEqual(trace.success(text), "unknown")
        self.assertEqual(trace.success({"exit_code": False}, False), "succeeded")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source, cache = root / "trace.jsonl", root / "cache"
            rows = [
                {"timestamp": "2026-10-06T01:00:00Z", "type": "response_item", "payload": {
                    "type": "function_call", "name": "exec_command", "call_id": "demo", "arguments": {}}},
                {"timestamp": "2026-10-06T01:01:00Z", "type": "response_item", "payload": {
                    "type": "function_call_output", "call_id": "demo", "output": {"exit_code": False}}},
            ]
            source.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            start, end = trace.window("2026-10-06", trace.zone("UTC"))
            events, _, _ = trace.collect([f"codex:{source}"], start, end, 100000, 10, cache)
            self.assertEqual(events[0]["status"], "unknown")
            checkpoint = next(cache.glob("*.json"))
            saved = json.loads(checkpoint.read_text(encoding="utf-8"))
            saved["version"] = "0.3.0"
            saved["state"]["events"][0]["status"] = "succeeded"
            checkpoint.write_text(json.dumps(saved), encoding="utf-8")
            events, _, inputs = trace.collect([f"codex:{source}"], start, end, 100000, 10, cache)
            self.assertEqual(events[0]["status"], "unknown")
            self.assertEqual(inputs[0]["reused_bytes"], 0)

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
            self.assertEqual(dict(gaps), {})

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
            previous_size = source.stat().st_size
            with source.open("a") as handle:
                handle.write(appended)
            start, end = trace.window("2026-10-06", trace.zone("UTC"))
            events, gaps, inputs = trace.collect(sources, start, end, 100000, 10, cache)
            self.assertEqual(inputs[0]["scanned_bytes"], source.stat().st_size - previous_size)
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
            # Byte budgets include the on-disk newline, which is CRLF on Windows.
            first_line_bytes = len(source.read_bytes().splitlines(keepends=True)[0])
            events, gaps, _ = trace.collect(sources, start, end, first_line_bytes, 10, cache)
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

    def test_incremental_lf_and_crlf_byte_budgets(self):
        for newline in (b"\n", b"\r\n"):
            with self.subTest(newline=newline), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                source, cache = root / "demo.jsonl", root / "cache"
                row = {"timestamp": "2026-10-06T01:00:00Z", "kind": "task", "session_id": "demo", "text": "虚构"}
                line = json.dumps(row, ensure_ascii=False).encode("utf-8") + newline
                source.write_bytes(line + line)
                start, end = trace.window("2026-10-06", trace.zone("UTC"))
                sources = [f"jsonl:{source}"]
                _, gaps, inputs = trace.collect(sources, start, end, len(line), 10, cache)
                self.assertIn("byte_limit_reached", gaps)
                self.assertEqual(inputs[0]["scanned_bytes"], len(line))
                _, gaps, inputs = trace.collect(sources, start, end, len(line), 10, cache)
                self.assertFalse(gaps)
                self.assertEqual(inputs[0]["scanned_bytes"], len(line))
                self.assertEqual(inputs[0]["reused_bytes"], len(line))

    def test_insight_brief_privacy_and_evidence_boundaries(self):
        start, end = trace.window("2026-10-06", trace.zone("UTC"))
        events, gaps, sources = trace.collect([f"jsonl:{ROOT / 'examples/demo.jsonl'}"], start, end, 100000, 20)
        structural = trace.report(events, gaps, sources, start, end)
        semantic = trace.report(events, gaps, sources, start, end, True)
        self.assertEqual(structural["insights"]["semantic_analysis_status"], "needs-text-opt-in")
        self.assertNotIn("Create a fictional study guide", json.dumps(structural["insights"]))
        self.assertEqual(semantic["insights"]["semantic_analysis_status"], "agent-review-required")
        self.assertTrue(all(p["business_completion"] == "unknown" for p in semantic["insights"]["progress"]))
        self.assertFalse(semantic["insights"]["memory_written"])
        self.assertTrue(semantic["insights"]["knowledge_candidates"])
        failure = next(item for item in semantic["insights"]["problems"] if item["kind"] == "failed_call")
        self.assertTrue(failure["evidence"])
        md = trace.markdown(semantic)
        self.assertLess(md.index("## 问题洞察"), md.index("## 完整可观察事件序列"))
        self.assertIn("未独立验证", md)
        task = semantic["tasks"][0]
        calls = [{"task": task["id"], "kind": "tool", "status": status, "tool": "demo", "evidence": f"S1:{i}"}
                 for i, status in enumerate(("failed", "failed", "succeeded"), 1)]
        brief = trace.insights([task], calls, [], True, True)
        self.assertEqual(brief["scope"], "partial")
        self.assertEqual(brief["problems"][0]["kind"], "repeated_failure")
        self.assertIn("不能确定", brief["problems"][0]["finding"])
        self.assertFalse(brief["knowledge_candidates"])

    def test_completed_formats_full_scan_and_html_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root / "fixture.jsonl"
            rows = [
                {"timestamp": "2026-10-06T00:00:00Z", "type": "response_item", "payload": {"type": "message", "role": "developer", "content": "do not export"}},
                {"timestamp": "2026-10-06T01:00:00Z", "type": "response_item", "payload": {"type": "message", "role": "user", "content": "<script>alert(1)</script> build a guide"}},
                {"timestamp": "2026-10-06T01:01:00Z", "type": "response_item", "payload": {"type": "function_call", "call_id": "call1", "name": "exec_command", "arguments": {"cmd": "fictional"}}},
                {"timestamp": "2026-10-06T01:02:00Z", "type": "event_msg", "payload": {"type": "item_completed", "item": {"type": "CommandExecution", "id": "call1", "exit_code": 0, "status": "completed", "command": "fictional"}}},
                {"timestamp": "2026-10-06T01:03:00Z", "type": "event_msg", "payload": {"type": "item_completed", "item": {"type": "FileChange", "id": "patch1", "changes": {"guide.md": {"type": "add"}}, "status": "completed"}}},
                {"timestamp": "2026-10-06T01:04:00Z", "type": "event_msg", "payload": {"type": "item_completed", "item": {"type": "McpToolCall", "id": "mcp1", "server": "demo", "tool": "Read", "arguments": {"path": "guide.md"}, "result": {"isError": False}}}},
                {"timestamp": "2026-10-06T01:05:00Z", "type": "response_item", "payload": {"type": "agent_message", "text": "draft created, verification pending"}},
            ]
            source.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            start, end = trace.window("2026-10-06", trace.zone("UTC"))
            events, gaps, inputs = trace.collect([f"codex:{source}"], start, end, sys.maxsize, sys.maxsize)
            self.assertFalse(gaps)
            self.assertEqual(len([e for e in events if e["kind"] == "tool"]), 3)
            self.assertEqual([e["status"] for e in events if e["kind"] == "tool"], ["succeeded"] * 3)
            data = trace.report(events, gaps, inputs, start, end, True)
            data["insights"]["progress"][0]["objective"] = "<script>alert(1)</script>"
            html = trace.html_report(data, [{"title": "总结", "finding": "<img onerror=bad>", "level": "inference", "evidence": ["S1:3"]}])
            self.assertIn("综合分析已附", html)
            self.assertNotIn("<img", html)
            self.assertNotIn("<script>", html)
            self.assertIn("&lt;img onerror=bad&gt;", html)
            self.assertNotIn("do not export", html)
            self.assertIn("知识沉淀候选", html)
            self.assertIn('href="#e-S1:4"', html)
            self.assertIn('id="e-S1:4"', html)
            command = [sys.executable, str(SCRIPT), "report", "--source", f"codex:{source}", "--date", "2026-10-06", "--output-dir", str(root / "reports")]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            path = Path(json.loads(result.stdout)["html"])
            self.assertTrue(path.is_file())
            self.assertNotIn("build a guide", path.read_text(encoding="utf-8"))
            if sys.platform != "win32":
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            # A formerly oversized record is parsed, while unknown formats stay visible.
            row = dict(rows[0], payload={"type": "reasoning", "data": "x" * (2 * 1024 * 1024 + 1)})
            source.write_text(json.dumps(row) + "\n" + json.dumps(dict(rows[-1], payload={"type": "future_unknown"})) + "\n", encoding="utf-8")
            _, gaps, _ = trace.collect([f"codex:{source}"], start, end, sys.maxsize, sys.maxsize)
            self.assertNotIn("oversized_line", gaps)
            self.assertEqual(gaps["unsupported_codex_item"], 1)

    def test_cross_task_dashboard_patterns_and_empty_charts(self):
        start, end = trace.window("2026-10-06", trace.zone("UTC"))
        events, gaps, sources = trace.collect([f"jsonl:{ROOT / 'examples/demo.jsonl'}"], start, end, 100000, 20)
        data = trace.report(events, gaps, sources, start, end, True)
        task = dict(data["insights"]["progress"][0], task="extra")
        data["insights"]["progress"].append(task)
        aggregate = trace.dashboard(data)
        self.assertEqual(len(aggregate["repeated_requests"]), 1)
        self.assertEqual(aggregate["repeated_requests"][0]["count"], 2)
        self.assertTrue(all(item["failed"] > 0 for item in aggregate["anomalies"]))
        self.assertEqual(sum(aggregate["hours"].values()), sum(aggregate["statuses"].values()))
        html = trace.html_report(data)
        self.assertEqual(html.count('<svg '), 4)
        self.assertIn('table class="timeline"', html)
        self.assertIn('table-layout:fixed', html)
        self.assertIn('tabindex="0"', html)
        self.assertIn('<time datetime=', html)
        self.assertIn('01:01:00 +0000', html)
        self.assertIn('role="img"', html)
        self.assertNotIn('工作进展与结果', html)
        self.assertNotIn('<h3>T1', html)
        data["privacy"] = "structural-only"
        self.assertFalse(trace.dashboard(data)["repeated_requests"])
        empty = trace.report([], {}, [], start, end)
        self.assertIn('未观察到相关记录', trace.html_report(empty))
        self.assertFalse(trace.dashboard(empty)["anomalies"])

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
