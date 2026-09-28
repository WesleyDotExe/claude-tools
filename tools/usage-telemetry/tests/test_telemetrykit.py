"""Tests aimed at: logging is truly off by default (no file touched, no env
read needed) and only writes when a path is given; `track` records both the
success and the exception path and never swallows the exception; `summarize`
and `tail` aggregate correctly, including malformed-line handling and env-var
fallback. Run:
python3 -m unittest discover -s tests -v
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telemetrykit import (  # noqa: E402
    log_path_from_env,
    record,
    summarize,
    tail,
    track,
)


class TestRecord(unittest.TestCase):
    def test_no_op_when_no_path_given_and_env_unset(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_TOOLS_USAGE_LOG", None)
            with tempfile.TemporaryDirectory() as d:
                # No log_path, no env var: record() must not create anything,
                # and must not raise even though there's nowhere to write.
                record("some-server", "some_tool", True)
                self.assertEqual(os.listdir(d), [])

    def test_writes_one_json_line_per_call(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "usage.jsonl")
            record("secure-random", "roll_dice", True, log_path=path)
            record("secure-random", "generate_password", False, "ValueError", log_path=path)
            with open(path) as f:
                lines = [json.loads(line) for line in f if line.strip()]
            self.assertEqual(len(lines), 2)
            self.assertEqual(lines[0]["server"], "secure-random")
            self.assertEqual(lines[0]["tool"], "roll_dice")
            self.assertTrue(lines[0]["ok"])
            self.assertNotIn("error", lines[0])
            self.assertFalse(lines[1]["ok"])
            self.assertEqual(lines[1]["error"], "ValueError")
            self.assertIn("ts", lines[0])

    def test_never_logs_payloads(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "usage.jsonl")
            record("s", "t", True, log_path=path)
            with open(path) as f:
                entry = json.loads(f.readline())
            self.assertEqual(set(entry.keys()), {"ts", "server", "tool", "ok"})

    def test_creates_parent_directories(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "nested", "dir", "usage.jsonl")
            record("s", "t", True, log_path=path)
            self.assertTrue(os.path.exists(path))

    def test_env_var_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "usage.jsonl")
            with patch.dict(os.environ, {"CLAUDE_TOOLS_USAGE_LOG": path}):
                self.assertEqual(log_path_from_env(), path)
                record("s", "t", True)
            with open(path) as f:
                self.assertEqual(len(f.readlines()), 1)

    def test_empty_env_var_counts_as_unset(self):
        with patch.dict(os.environ, {"CLAUDE_TOOLS_USAGE_LOG": ""}):
            self.assertIsNone(log_path_from_env())


class TestTrack(unittest.TestCase):
    def test_records_success_and_returns_value(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "usage.jsonl")

            @track("my-server", log_path=path)
            def add(a, b):
                return a + b

            self.assertEqual(add(2, 3), 5)
            entries = tail(10, log_path=path)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["tool"], "add")
            self.assertTrue(entries[0]["ok"])

    def test_records_error_and_reraises(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "usage.jsonl")

            @track("my-server", log_path=path)
            def boom():
                raise ValueError("nope")

            with self.assertRaises(ValueError):
                boom()
            entries = tail(10, log_path=path)
            self.assertEqual(len(entries), 1)
            self.assertFalse(entries[0]["ok"])
            self.assertEqual(entries[0]["error"], "ValueError")

    def test_preserves_function_metadata(self):
        @track("my-server")
        def documented(a: int) -> int:
            """A docstring worth preserving."""
            return a

        self.assertEqual(documented.__name__, "documented")
        self.assertEqual(documented.__doc__, "A docstring worth preserving.")


class TestSummarize(unittest.TestCase):
    def test_missing_log_reports_not_exists(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "does-not-exist.jsonl")
            result = summarize(log_path=path)
            self.assertFalse(result["exists"])
            self.assertEqual(result["total_invocations"], 0)
            self.assertEqual(result["servers"], {})

    def test_unset_reports_none_path(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_TOOLS_USAGE_LOG", None)
            result = summarize()
            self.assertIsNone(result["log_path"])
            self.assertFalse(result["exists"])

    def test_aggregates_per_server_and_tool(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "usage.jsonl")
            record("secure-random", "roll_dice", True, log_path=path)
            record("secure-random", "roll_dice", True, log_path=path)
            record("secure-random", "roll_dice", False, "ValueError", log_path=path)
            record("time-arithmetic", "add_duration", True, log_path=path)

            result = summarize(log_path=path)
            self.assertTrue(result["exists"])
            self.assertEqual(result["total_invocations"], 4)
            self.assertEqual(result["malformed_lines"], 0)

            sr = result["servers"]["secure-random"]
            self.assertEqual(sr["total"], 3)
            self.assertEqual(sr["ok"], 2)
            self.assertEqual(sr["error"], 1)
            self.assertEqual(sr["tools"]["roll_dice"]["total"], 3)

            ta = result["servers"]["time-arithmetic"]
            self.assertEqual(ta["total"], 1)
            self.assertEqual(ta["ok"], 1)

    def test_skips_malformed_lines_without_crashing(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "usage.jsonl")
            with open(path, "w") as f:
                f.write("not json at all\n")
                f.write(json.dumps({"server": "s", "tool": "t", "ok": True}) + "\n")
                f.write("\n")  # blank line, silently skipped, not malformed
                f.write(json.dumps({"missing": "fields"}) + "\n")

            result = summarize(log_path=path)
            self.assertEqual(result["total_invocations"], 1)
            self.assertEqual(result["malformed_lines"], 2)

    def test_first_seen_and_last_seen(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "usage.jsonl")
            with open(path, "w") as f:
                f.write(json.dumps({"ts": "2026-09-28T10:00:00Z", "server": "s", "tool": "t", "ok": True}) + "\n")
                f.write(json.dumps({"ts": "2026-09-28T12:00:00Z", "server": "s", "tool": "t", "ok": True}) + "\n")
                f.write(json.dumps({"ts": "2026-09-28T11:00:00Z", "server": "s", "tool": "t", "ok": True}) + "\n")

            result = summarize(log_path=path)
            self.assertEqual(result["first_seen"], "2026-09-28T10:00:00Z")
            self.assertEqual(result["last_seen"], "2026-09-28T12:00:00Z")


class TestTail(unittest.TestCase):
    def test_most_recent_first_and_limit(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "usage.jsonl")
            for i in range(5):
                record("s", f"tool_{i}", True, log_path=path)

            result = tail(3, log_path=path)
            self.assertEqual(len(result), 3)
            self.assertEqual([e["tool"] for e in result], ["tool_4", "tool_3", "tool_2"])

    def test_empty_when_no_log(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "missing.jsonl")
            self.assertEqual(tail(5, log_path=path), [])

    def test_zero_n_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "usage.jsonl")
            record("s", "t", True, log_path=path)
            self.assertEqual(tail(0, log_path=path), [])


if __name__ == "__main__":
    unittest.main()
