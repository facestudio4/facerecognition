import os
import sqlite3
import tempfile
import unittest

from backend.phase4_showcase_pack import Phase4ShowcaseRunner


class Phase4ShowcasePackTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.base_dir = self.tmp_dir.name
        self.db_path = os.path.join(self.base_dir, "test_facestudio.db")
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT,
                email TEXT,
                phone TEXT,
                role TEXT,
                created TEXT,
                logins_json TEXT,
                verified_email INTEGER,
                data_json TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO users(username, password, email, phone, role, created, logins_json, verified_email, data_json)
            VALUES ('alice', 'x', 'alice@example.com', '+911234567890', 'user', '2026-01-01 10:00:00', '[]', 1, '{}')
            """
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        try:
            self.tmp_dir.cleanup()
        except PermissionError:
            pass

    def test_viva_sequence_and_export(self):
        runner = Phase4ShowcaseRunner(self.base_dir, self.db_path, host="127.0.0.1", port=8798)
        try:
            data = runner.run_viva_sequence(user_limit=3)
            self.assertIn("health", data)
            self.assertIn("stats", data)
            path = runner.export_viva_report()
            self.assertTrue(os.path.exists(path))
        finally:
            runner.stop_services()


if __name__ == "__main__":
    unittest.main()
