"""Regression checks use temporary data and synthetic Codex replies, never a live account."""
import contextlib
import io
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain
import auto_brain
import brain_io
import sync_obsidian

SOURCE = Path(__file__).resolve().parents[1]
OLD = '# Perfil anterior\nDecisão histórica verificável.'
NEW = '# Perfil consolidado\nDecisão histórica verificável.\nNova descoberta.'


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'brain'
        self.root.mkdir()
        for name in ('brain.py', 'auto_brain.py', 'sync_obsidian.py', 'brain_io.py'):
            shutil.copyfile(SOURCE/name, self.root/name)
        self.project = self.base/'project'
        self.project.mkdir()
        (self.project/'main.py').write_text('print(1)\n')
        self.vault = self.base/'vault'
        self.vault.mkdir()
        self.data = self.root/'.brain'
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        self.stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
        for module, values in [
            (brain, dict(ROOT=self.root, BRAIN_DIR=self.data, RUNS_DIR=self.data/'runs', PROJECTS_DIR=self.data/'projects', DB_PATH=self.data/'brain.db')),
            (auto_brain, dict(ROOT=self.root, AUTO_DIR=self.data/'auto', STATE_PATH=self.data/'auto/state.json', LOG_PATH=self.data/'auto/auto.log', DB_PATH=self.data/'brain.db', DRY_RUN=False)),
            (sync_obsidian, dict(ROOT=self.root, PROJECTS_DIR=self.data/'projects')),
        ]:
            for name, value in values.items():
                self.stack.enter_context(patch.object(module, name, value))
        brain.save_profile(self.project, OLD, 0)
        brain.remember(SimpleNamespace(project=str(self.project), category='decisao', content='MEMORIA_DESTE_PROJETO', source='user', confidence=1.0))
        self.config = {'vault': str(self.vault), 'projects': [{'path': str(self.project), 'folder': 'Demo'}]}
        self.config_path = self.root/'config.json'
        self.config_path.write_text(json.dumps(self.config))

    def study_args(self):
        return SimpleNamespace(project=str(self.project), refresh=True, timeout=10)

    def run_auto(self, *flags):
        self.config_path.write_text(json.dumps(self.config))
        with patch('sys.argv', ['auto_brain.py', '--config', str(self.config_path), '--once', *flags]):
            return auto_brain.main()

    def note(self, vault=None):
        return (vault or self.vault)/'Projetos/Demo/Perfil do Codex Brain.md'

    def synthetic_study(self, project, timeout):
        with patch.object(brain, 'run_codex', return_value=(0, NEW, '', 0, '', None)):
            return brain.study(self.study_args()), 'Resposta sintética'

    def test_refresh_includes_full_profile_and_memories(self):
        large = OLD + '\n' + ('conteudo ' * 3000) + 'FIM_DO_PERFIL'
        brain.save_profile(self.project, large, 0)
        with patch.object(brain, 'run_codex', return_value=(0, NEW, '', 0, '', None)) as run:
            self.assertEqual(brain.study(self.study_args()), 0)
        prompt = run.call_args.args[1]
        self.assertIn(large, prompt)
        self.assertIn('MEMORIA_DESTE_PROJETO', prompt)
        self.assertEqual(run.call_args.args[2], 'read-only')
        self.assertEqual(brain.get_profile(self.project), NEW)

    def test_run_includes_full_profile(self):
        large = OLD + ('conteudo ' * 3000) + 'FIM_DO_PERFIL'
        brain.save_profile(self.project, large, 0)
        with patch.object(brain, 'run_codex', return_value=(0, 'OK', '', 0, '', None)) as run:
            brain.run_task(SimpleNamespace(project=str(self.project), task='Explique', timeout=10))
        self.assertIn(large, run.call_args.args[1])

    def test_failed_or_empty_study_preserves_profile(self):
        for code, answer in [(1, 'Erro com texto'), (124, ''), (0, '  ')]:
            with self.subTest(code=code, answer=answer), patch.object(brain, 'run_codex', return_value=(code, answer, '', 0, '', None)):
                self.assertNotEqual(brain.study(self.study_args()), 0)
                self.assertEqual(brain.get_profile(self.project), OLD)
                self.assertEqual(brain.profile_path_for(self.project).read_text(), OLD)

    def test_history_is_saved_before_replacing_profile(self):
        brain.save_profile(self.project, NEW, 0)
        history = brain.profile_path_for(self.project).parent/'history'
        self.assertEqual([p.read_text() for p in history.glob('*/profile.md')], [OLD])
        rows = [json.loads(p.read_text()) for p in history.glob('*/record.json')]
        self.assertEqual(rows[0]['profile'], OLD)

    def test_backup_failure_does_not_replace_profile(self):
        real = brain.atomic_write_bytes
        def fail_backup(path, content):
            if 'history' in path.parts:
                raise OSError('Falha de disco simulada')
            return real(path, content)
        with patch.object(brain, 'atomic_write_bytes', side_effect=fail_backup):
            with self.assertRaises(OSError):
                brain.save_profile(self.project, NEW, 0)
        self.assertEqual(brain.get_profile(self.project), OLD)
        self.assertEqual(brain.profile_path_for(self.project).read_text(), OLD)

    def test_sqlite_failure_restores_profile_file(self):
        con = brain.connect()
        con.execute("CREATE TRIGGER fail_update BEFORE UPDATE ON project_profiles BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        con.commit()
        con.close()
        with self.assertRaises(sqlite3.DatabaseError):
            brain.save_profile(self.project, NEW, 0)
        self.assertEqual(brain.get_profile(self.project), OLD)
        self.assertEqual(brain.profile_path_for(self.project).read_text(), OLD)

    def test_concurrent_result_cannot_overwrite_newer_profile(self):
        revision = brain.profile_revision(self.project)
        brain.save_profile(self.project, NEW, 0)
        with self.assertRaises(RuntimeError):
            brain.save_profile(self.project, 'RESPOSTA_ATRASADA', 0, expected_revision=revision)
        self.assertEqual(brain.get_profile(self.project), NEW)

    def test_cli_prompt_uses_stdin_and_json_events_are_not_a_profile(self):
        event = '{"type":"thread.started","thread_id":"fixture"}\n'
        result = subprocess.CompletedProcess(['codex'], 0, event, '')
        with patch.object(brain, 'codex_path', return_value='codex'), patch.object(brain.subprocess, 'run', return_value=result) as run:
            self.assertNotEqual(brain.study(self.study_args()), 0)
        self.assertEqual(run.call_args.args[0][-1], '-')
        self.assertIn(OLD, run.call_args.kwargs['input'])
        self.assertNotIn(OLD, ' '.join(run.call_args.args[0]))
        self.assertEqual(brain.get_profile(self.project), OLD)

    def test_auto_failed_study_is_nonzero_and_keeps_profile(self):
        with patch.object(auto_brain, 'run_brain_study', return_value=(1, 'Falha sintética')):
            self.assertEqual(self.run_auto('--force'), 1)
        self.assertEqual(brain.get_profile(self.project), OLD)
        self.assertEqual(json.loads(auto_brain.STATE_PATH.read_text())['events'][-1]['status'], 'falha')

    def test_auto_failed_sync_is_nonzero_and_retries_without_study(self):
        with patch.object(auto_brain, 'sync_project', return_value=(2, 'Falha sintética')):
            self.assertEqual(self.run_auto(), 1)
        with patch.object(auto_brain, 'run_brain_study') as study:
            self.assertEqual(self.run_auto(), 0)
            study.assert_not_called()
        self.assertIn(OLD, self.note().read_text())

    def test_deleted_note_or_index_is_recreated_without_study(self):
        self.assertEqual(self.run_auto(), 0)
        paths = [self.note(), self.vault/'Sistemas/Índice dos perfis do Codex Brain.md']
        for path in paths:
            path.unlink()
            with patch.object(auto_brain, 'run_brain_study') as study:
                self.assertEqual(self.run_auto(), 0)
                study.assert_not_called()
            self.assertTrue(path.is_file())

    def test_changed_destination_receives_unchanged_profile(self):
        self.assertEqual(self.run_auto(), 0)
        new_vault = self.base/'outro-cofre'
        new_vault.mkdir()
        self.config['vault'] = str(new_vault)
        with patch.object(auto_brain, 'run_brain_study') as study:
            self.assertEqual(self.run_auto(), 0)
            study.assert_not_called()
        self.assertIn(OLD, self.note(new_vault).read_text())

    def test_manual_note_collision_is_preserved_and_reported(self):
        self.note().parent.mkdir(parents=True)
        self.note().write_text('MINHA_NOTA_MANUAL')
        self.assertEqual(self.run_auto(), 1)
        self.assertEqual(self.note().read_text(), 'MINHA_NOTA_MANUAL')

    def test_cycle_studies_changes_and_saves_history_and_preserves_manual_notes(self):
        manual = self.vault/'Minha nota.md'
        manual.write_text('Anotações do usuário')
        self.assertEqual(self.run_auto(), 0)
        (self.project/'main.py').write_text('print(22222)\n')
        with patch.object(auto_brain, 'run_brain_study', side_effect=self.synthetic_study) as study:
            self.assertEqual(self.run_auto(), 0)
            study.assert_called_once()
        self.assertIn(NEW, self.note().read_text())
        history = self.note().parent/'Histórico Codex Brain'
        self.assertTrue(any(OLD in p.read_text() for p in history.glob('Perfil anterior*.md')))
        self.assertTrue(list(history.glob('Mudanças*.md')))
        self.assertEqual(manual.read_text(), 'Anotações do usuário')
        note_bytes = self.note().read_bytes()
        with patch.object(auto_brain, 'run_brain_study') as study:
            self.assertEqual(self.run_auto(), 0)
            study.assert_not_called()
        self.assertEqual(self.note().read_bytes(), note_bytes)

    def test_history_export_failure_still_has_local_backup_and_nonzero_exit(self):
        with patch.object(auto_brain, 'run_brain_study', side_effect=self.synthetic_study), patch.object(auto_brain, 'create_history', side_effect=OSError('Falha no cofre')):
            self.assertEqual(self.run_auto('--force'), 1)
        self.assertEqual(brain.get_profile(self.project), NEW)
        history = brain.profile_path_for(self.project).parent/'history'
        self.assertTrue(any(p.read_text() == OLD for p in history.glob('*/profile.md')))

    def test_dry_run_writes_nothing(self):
        before = {str(p.relative_to(self.base)): p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
        with patch.object(auto_brain, 'run_brain_study') as study:
            self.assertEqual(self.run_auto('--dry-run', '--force'), 0)
            study.assert_not_called()
        after = {str(p.relative_to(self.base)): p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_missing_vault_is_not_created_and_reports_failure(self):
        missing = self.base/'missing-vault'
        self.config['vault'] = str(missing)
        self.assertEqual(self.run_auto(), 1)
        self.assertFalse(missing.exists())

    def test_corrupt_state_is_preserved(self):
        auto_brain.STATE_PATH.parent.mkdir(parents=True)
        auto_brain.STATE_PATH.write_text('{invalid')
        self.assertEqual(self.run_auto(), 1)
        self.assertEqual(auto_brain.STATE_PATH.read_text(), '{invalid')

    def test_lock_excludes_second_process_and_can_be_reused(self):
        lock = self.base/'check.lock'
        fd = brain_io.acquire_file_lock(lock)
        self.assertIsNotNone(fd)
        try:
            self.assertIsNone(brain_io.acquire_file_lock(lock))
        finally:
            brain_io.release_file_lock(fd)
        fd2 = brain_io.acquire_file_lock(lock)
        self.assertIsNotNone(fd2)
        brain_io.release_file_lock(fd2)


if __name__ == '__main__':
    unittest.main()
