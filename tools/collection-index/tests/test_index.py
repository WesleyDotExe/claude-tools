import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from index import collect  # noqa: E402


class CollectTests(unittest.TestCase):
    def test_reads_well_formed_manifests(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "alpha").mkdir()
            (root / "alpha" / "manifest.json").write_text(json.dumps({
                "name": "alpha", "summary": "does a thing", "problem": "a gap",
                "keyless": True, "created": "2026-01-01",
            }))
            entries = collect(root)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["name"], "alpha")
            self.assertEqual(entries[0]["path"], f"{root.name}/alpha")

    def test_skips_manifest_missing_required_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "broken").mkdir()
            (root / "broken" / "manifest.json").write_text(json.dumps({"name": "broken"}))
            entries = collect(root)
            self.assertEqual(entries, [])

    def test_skips_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bad").mkdir()
            (root / "bad" / "manifest.json").write_text("{not json")
            entries = collect(root)
            self.assertEqual(entries, [])

    def test_sorted_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("zeta", "alpha"):
                (root / name).mkdir()
                (root / name / "manifest.json").write_text(json.dumps({
                    "name": name, "summary": "x", "problem": "y",
                    "keyless": True, "created": "2026-01-01",
                }))
            entries = collect(root)
            self.assertEqual([e["name"] for e in entries], ["alpha", "zeta"])


if __name__ == "__main__":
    unittest.main()
