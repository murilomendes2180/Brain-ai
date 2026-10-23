import os
import tempfile
import unittest
from pathlib import Path

import auto_brain


class AutoBrainHelpersTest(unittest.TestCase):
    def test_project_key_is_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Alethe Agents"
            path.mkdir()
            self.assertEqual(auto_brain.project_key(path.resolve()), auto_brain.project_key(path.resolve()))
            self.assertIn("Alethe-Agents", auto_brain.project_key(path.resolve()))

    def test_secret_files_are_excluded(self):
        self.assertTrue(auto_brain.is_secret_file(Path(".env")))
        self.assertTrue(auto_brain.is_secret_file(Path(".env.production")))
        self.assertTrue(auto_brain.is_secret_file(Path("private.pem")))
        self.assertFalse(auto_brain.is_secret_file(Path(".env.example")))
        self.assertFalse(auto_brain.is_secret_file(Path("secure_store.rs")))

    def test_scan_detects_file_change_and_skips_secrets_and_build_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "node_modules" / "package").mkdir(parents=True)
            source = root / "src" / "app.py"
            source.write_text("print('one')\n", encoding="utf-8")
            (root / ".env").write_text("SHOULD_NOT_READ=secret\n", encoding="utf-8")
            (root / "node_modules" / "package" / "ignored.js").write_text("ignored", encoding="utf-8")
            fingerprint1, manifest1, skipped = auto_brain.scan_project(root, {}, {})
            self.assertIn("src/app.py", manifest1)
            self.assertNotIn(".env", manifest1)
            self.assertFalse(any("node_modules" in key for key in manifest1))
            self.assertEqual(skipped, 1)
            source.write_text("print('two')\n", encoding="utf-8")
            # Ensure the modified file has a distinct stat signature even on filesystems
            # whose timestamp granularity may be coarse.
            os.utime(source, ns=(source.stat().st_atime_ns, source.stat().st_mtime_ns + 2_000_000_000))
            fingerprint2, manifest2, _ = auto_brain.scan_project(root, manifest1, {})
            self.assertNotEqual(fingerprint1, fingerprint2)
            self.assertNotEqual(manifest1["src/app.py"]["digest"], manifest2["src/app.py"]["digest"])


if __name__ == "__main__":
    unittest.main()
