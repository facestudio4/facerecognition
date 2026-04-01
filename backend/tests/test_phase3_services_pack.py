import os
import sqlite3
import tempfile
import unittest

from backend.phase3_services_pack import Phase3ServiceHub


class Phase3ServicesPackTests(unittest.TestCase):
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
            VALUES ('alice', 'x', 'alice@example.com', '+911234567890', 'user', '2026-01-01 10:00:00', '[]', 1, '{}')
            """
        )
        conn.execute(
            """
            INSERT INTO face_events(name, distance, event_time, payload_json)
            VALUES ('alice', 0.78, '2026-01-01 11:00:00', '{"name":"alice"}')
            """
        )
        conn.execute(
            """
            INSERT INTO attendance_entries(payload_json)
            VALUES ('{"date":"2026-01-01","count":1}')
            """
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        try:
            self.tmp_dir.cleanup()
        except PermissionError:
            pass

    def test_api_key_created_and_stable(self):
        hub_a = Phase3ServiceHub(self.base_dir, self.db_path)
        key_a = hub_a.api_key
        self.assertTrue(isinstance(key_a, str) and len(key_a) >= 16)
        hub_b = Phase3ServiceHub(self.base_dir, self.db_path)
        self.assertEqual(key_a, hub_b.api_key)

    def test_stats_and_user_listing(self):
        hub = Phase3ServiceHub(self.base_dir, self.db_path)
        stats = hub.get_stats()
        self.assertGreaterEqual(stats["users"], 1)
        self.assertGreaterEqual(stats["face_events"], 1)
        users = hub.list_users(limit=10)
        self.assertTrue(any(u["username"] == "alice" for u in users))

    def test_scheduler_creates_backup(self):
        hub = Phase3ServiceHub(self.base_dir, self.db_path)
        backup_path = hub._create_backup()
        self.assertTrue(os.path.exists(backup_path))
        self.assertTrue(backup_path.endswith(".db"))

    def test_token_generation_and_validation(self):
        hub = Phase3ServiceHub(self.base_dir, self.db_path)
        token_data = hub.generate_access_token(subject="tester", ttl_minutes=5)
        token = token_data["token"]
        self.assertTrue(hub._validate_access_token(token))

    def test_docs_and_demo_kit_export(self):
        hub = Phase3ServiceHub(self.base_dir, self.db_path)
        docs = hub.get_api_docs()
        self.assertEqual(docs["name"], "Face Studio API")
        out_dir = hub.export_demo_kit()
        self.assertTrue(os.path.exists(os.path.join(out_dir, "api_docs.json")))
        self.assertTrue(os.path.exists(os.path.join(out_dir, "quick_demo.ps1")))
        self.assertTrue(os.path.exists(os.path.join(out_dir, "quick_demo.py")))

    def test_stop_scheduler_when_not_running_is_safe(self):
        hub = Phase3ServiceHub(self.base_dir, self.db_path)
        before = len(hub.list_recent_activity(limit=20))
        hub.stop_backup_scheduler()
        after = len(hub.list_recent_activity(limit=20))
        self.assertEqual(before, after)

    def test_scheduler_stop_event_is_independent(self):
        hub = Phase3ServiceHub(self.base_dir, self.db_path)
        hub.start_backup_scheduler(interval_minutes=1)
        self.assertTrue(hub.is_scheduler_running())
        self.assertFalse(hub._scheduler_stop_event.is_set())
        hub.stop_backup_scheduler()
        self.assertFalse(hub.is_scheduler_running())
        self.assertTrue(hub._scheduler_stop_event.is_set())

    def test_save_and_search_recognition_locations(self):
        hub = Phase3ServiceHub(self.base_dir, self.db_path)
        result = hub.save_recognition_location_event(
            recognized_name='alice',
            location_name='Mumbai, India',
            latitude=19.0760,
            longitude=72.8777,
            confidence=0.88,
            requested_by='alice',
        )
        self.assertTrue(result.get('ok'))
        rows = hub.search_recognition_locations(name='alice', limit=10)
        self.assertGreaterEqual(len(rows), 1)
        self.assertEqual(rows[0]['recognized_name'].lower(), 'alice')
        self.assertEqual(rows[0]['location_name'], 'Mumbai, India')

    def test_recognition_location_preserves_last_known_coordinates(self):
        hub = Phase3ServiceHub(self.base_dir, self.db_path)
        first = hub.save_recognition_location_event(
            recognized_name='alice',
            location_name='Mumbai, India',
            latitude=19.0760,
            longitude=72.8777,
            confidence=0.91,
            requested_by='alice',
        )
        self.assertTrue(first.get('ok'))

        second = hub.save_recognition_location_event(
            recognized_name='alice',
            location_name='Location fetch failed',
            latitude=None,
            longitude=None,
            confidence=0.89,
            requested_by='alice',
        )
        self.assertTrue(second.get('ok'))
        self.assertEqual(second.get('data', {}).get('saved'), False)
        self.assertEqual(
            second.get('data', {}).get('reason'),
            'kept_last_known_location',
        )

        rows = hub.search_recognition_locations(name='alice', limit=10)
        self.assertGreaterEqual(len(rows), 1)
        self.assertEqual(rows[0]['location_name'], 'Mumbai, India')
        self.assertAlmostEqual(float(rows[0]['latitude']), 19.0760, places=4)
        self.assertAlmostEqual(float(rows[0]['longitude']), 72.8777, places=4)

    def test_signup_email_verification_flow(self):
        hub = Phase3ServiceHub(self.base_dir, self.db_path)
        sent = []

        def fake_send_email(to_email, subject, body):
            sent.append({"to": to_email, "subject": subject, "body": body})
            return {"ok": True}

        hub._send_email = fake_send_email

        start = hub.begin_signup_verification(
            username='bob',
            email='bob@example.com',
            phone='+911112223334',
            password='pass1234',
        )
        self.assertTrue(start.get('ok'))
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]['to'], 'bob@example.com')

        pending = hub._pending_signup_codes.get('bob@example.com')
        self.assertIsNotNone(pending)
        code = str(pending.get('code'))

        done = hub.complete_signup_verification(email='bob@example.com', code=code)
        self.assertTrue(done.get('ok'))
        profile = hub.authenticate_user(identifier='bob', password='pass1234')
        self.assertIsNotNone(profile)
        self.assertEqual(profile['username'], 'bob')

    def test_signup_email_verification_phone_optional(self):
        hub = Phase3ServiceHub(self.base_dir, self.db_path)
        hub._send_email = lambda to_email, subject, body: {"ok": True}

        start = hub.begin_signup_verification(
            username='charlie',
            email='charlie@example.com',
            phone='',
            password='pass1234',
        )
        self.assertTrue(start.get('ok'))

        pending = hub._pending_signup_codes.get('charlie@example.com')
        self.assertIsNotNone(pending)
        code = str(pending.get('code'))

        done = hub.complete_signup_verification(email='charlie@example.com', code=code)
        self.assertTrue(done.get('ok'))
        self.assertEqual(done.get('data', {}).get('phone', ''), '')


if __name__ == "__main__":
    unittest.main()
