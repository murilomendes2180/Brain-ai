import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain

class BrainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.old = (brain.BRAIN_DIR, brain.RUNS_DIR, brain.PROJECTS_DIR, brain.DB_PATH)
        brain.BRAIN_DIR = base / ".brain"
        brain.RUNS_DIR = brain.BRAIN_DIR / "runs"
        brain.PROJECTS_DIR = brain.BRAIN_DIR / "projects"
        brain.DB_PATH = brain.BRAIN_DIR / "brain.db"

    def tearDown(self):
        brain.BRAIN_DIR, brain.RUNS_DIR, brain.PROJECTS_DIR, brain.DB_PATH = self.old
        self.tmp.cleanup()

    def test_tables_initialize(self):
        con = brain.connect()
        tables = {r["name"] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        con.close()
        self.assertTrue({"memories", "runs", "proposals", "project_profiles"}.issubset(tables))

    def test_save_and_retrieve_project_profile(self):
        project = Path(self.tmp.name).resolve()
        target = project / "sample-project"
        target.mkdir()
        path = brain.save_profile(target, "# Perfil\nTeste", 0)
        self.assertTrue(path.exists())
        self.assertEqual(brain.get_profile(target), "# Perfil\nTeste")

    def test_project_keys_are_distinct(self):
        a = Path("C:/repo-a")
        b = Path("C:/repo-b")
        self.assertNotEqual(brain.project_key(a), brain.project_key(b))

if __name__ == "__main__":
    unittest.main()
