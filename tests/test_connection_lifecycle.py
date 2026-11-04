"""Regression checks for Windows SQLite temporary-file locking."""
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from adon_context import store
from adon_context.store import connect, ensure_project, add_event


class TestConnectionLifecycle(unittest.TestCase):
    def test_connection_is_closed_after_context(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / 'temp.sqlite3'
            with connect(db) as c:
                ensure_project(c, 'isolated')
            with self.assertRaises(sqlite3.ProgrammingError):
                c.execute('SELECT 1')
            # On Windows, deleting the directory would raise WinError 32
            # if the SQLite file were still open.
        self.assertFalse(db.exists())

    def test_rollback_and_close_on_error(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / 'temp.sqlite3'
            with self.assertRaisesRegex(RuntimeError, 'rollback'):
                with connect(db) as c:
                    ensure_project(c, 'should-not-commit')
                    raise RuntimeError('rollback')
            with self.assertRaises(sqlite3.ProgrammingError):
                c.execute('SELECT 1')
            with connect(db) as c2:
                self.assertEqual(
                    c2.execute("SELECT COUNT(*) FROM projects WHERE id='should-not-commit'").fetchone()[0], 0
                )

    def test_concurrent_writers_complete_without_locks(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / 'concurrent.sqlite3'
            with connect(db) as c:
                ensure_project(c, 'concurrent')

            def write_batch(worker):
                with connect(db) as c:
                    for index in range(10):
                        add_event(c, 'concurrent', 'note', f'worker-{worker}-{index}', 'parallel write')

            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(write_batch, range(4)))
            with connect(db) as c:
                count = c.execute("SELECT COUNT(*) FROM events WHERE project='concurrent'").fetchone()[0]
                self.assertEqual(count, 40)
                self.assertEqual(c.execute("PRAGMA integrity_check").fetchone()[0], 'ok')

    def test_connection_closes_when_schema_initialization_fails(self):
        class FailingConnection:
            closed = False
            row_factory = None

            def execute(self, *_args):
                return None

            def executescript(self, *_args):
                raise sqlite3.OperationalError('schema failure')

            def close(self):
                self.closed = True

        fake = FailingConnection()
        with tempfile.TemporaryDirectory() as d:
            with patch.object(store.sqlite3, 'connect', return_value=fake):
                with self.assertRaisesRegex(sqlite3.OperationalError, 'schema failure'):
                    connect(Path(d) / 'broken.sqlite3')
        self.assertTrue(fake.closed)


if __name__ == '__main__':
    unittest.main()
