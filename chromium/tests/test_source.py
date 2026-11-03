import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prepare_source", HERE / "prepare_source.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SourceSafety(unittest.TestCase):
    def test_changed_upstream_refused_without_modifying_any_file(self):
        hashes = json.loads((HERE / "upstream-files.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in hashes:
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"different upstream revision")
            before = {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            with self.assertRaisesRegex(ValueError, "differs from lock"):
                module.prepare(root)
            after = {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(before, after)

    def test_ambiguous_anchor_refused(self):
        with self.assertRaises(ValueError):
            module.replace_once("anchor anchor", "anchor", "replacement")

    def test_missing_anchor_refused(self):
        with self.assertRaises(ValueError):
            module.replace_once("original", "different", "replacement")


if __name__ == "__main__":
    unittest.main()
