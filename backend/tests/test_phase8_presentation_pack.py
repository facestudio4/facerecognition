import os
import sqlite3
import tempfile
import unittest

from backend.phase8_presentation_pack import PresentationStartupPack


class Phase8PresentationPackTests(unittest.TestCase):
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
            CREATE TABLE IF NOT EXISTS face_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                distance REAL,
                event_time TEXT,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO users(username, password, email, phone, role, created, logins_json, verified_email, data_json)
            VALUES ('alice', 'x', 'alice@example.com', '+911234567890', 'admin', '2026-01-01 10:00:00', '[]', 1, '{}')
            """
        )
        conn.execute(
            """
            INSERT INTO face_events(name, distance, event_time, payload_json)
            VALUES ('alice', 0.78, '2026-01-01 11:00:00', '{"name":"alice"}')
            """
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        try:
            self.tmp_dir.cleanup()
        except PermissionError:
            pass

    def test_create_startup_scripts(self):
        pack = PresentationStartupPack(self.base_dir, self.db_path)
        try:
            summary_path, summary = pack.create_startup_scripts()
            self.assertTrue(os.path.exists(summary_path))
            self.assertTrue(os.path.exists(summary["scripts"]["start_judge_mode.bat"]))
            self.assertTrue(os.path.exists(summary["scripts"]["start_demo_launcher.ps1"]))
        finally:
            pack.orchestrator.controller.showcase.stop_services()


if __name__ == "__main__":
    unittest.main()
