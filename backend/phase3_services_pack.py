import json
import os
import secrets
import sqlite3
import smtplib
import shutil
import threading
import time
import urllib.parse
import base64
import hashlib
import hmac
import re
import sys
import traceback
from random import randint
from email.message import EmailMessage
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except Exception:
    tk = None
    filedialog = None
    messagebox = None
    ttk = None

import cv2
import numpy as np


PASSWORD_SALT = "FaceStudio_v2_salt"


class AutoClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            return super().__exit__(exc_type, exc_val, exc_tb)
        finally:
            self.close()


class Phase3ServiceHub:
    def __init__(self, base_dir: str, db_path: str, host: str = "127.0.0.1", port: int = 8787):
        self.base_dir = base_dir
        self.db_path = db_path
        self.host = host
        self.port = int(port)
        self._api_server = None
        self._api_thread = None
        self._scheduler_thread = None
        self._scheduler_stop_event = threading.Event()
        self._scheduler_interval_seconds = 86400
        self._last_backup_at = None
        self._ensure_schema()
        self.api_key = self._get_or_create_api_key()
        self.token_secret = self._get_or_create_token_secret()
        self._mobile_known_encodings = None
        self._mobile_known_loaded_at = 0.0
        self._pending_reset_codes = {}
        self._pending_signup_codes = {}
        self._sync_refresh_thread = None
        self._sync_refresh_running = False
        self._sync_refresh_error = ""

    def _connect(self):
        conn = sqlite3.connect(self.db_path, factory=AutoClosingConnection)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _ensure_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS project_meta (
                    meta_key TEXT PRIMARY KEY,
                    meta_value TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS activity_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_time TEXT,
                    username TEXT,
                    role TEXT,
                    action TEXT,
                    detail TEXT,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS recognition_location_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_time TEXT,
                    recognized_name TEXT,
                    location_name TEXT,
                    latitude REAL,
                    longitude REAL,
                    confidence REAL,
                    source TEXT,
                    requested_by TEXT,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_time ON activity_events(event_time)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rec_loc_name ON recognition_location_events(recognized_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rec_loc_time ON recognition_location_events(event_time)")
            if self._table_exists(conn, "users"):
                self._ensure_users_privacy_columns(conn)
            conn.commit()

    def _column_exists(self, conn, table_name: str, column_name: str):
        try:
            rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        except Exception:
            return False
        for row in rows:
            if str(row[1]).strip().lower() == str(column_name).strip().lower():
                return True
        return False

    def _ensure_users_privacy_columns(self, conn):
        if not self._column_exists(conn, "users", "privacy_mode"):
            conn.execute("ALTER TABLE users ADD COLUMN privacy_mode TEXT DEFAULT 'public'")
        if not self._column_exists(conn, "users", "privacy_allowed_json"):
            conn.execute("ALTER TABLE users ADD COLUMN privacy_allowed_json TEXT DEFAULT '[]'")
        if not self._column_exists(conn, "users", "privacy_allowed_map_json"):
            conn.execute("ALTER TABLE users ADD COLUMN privacy_allowed_map_json TEXT DEFAULT '[]'")
        if not self._column_exists(conn, "users", "privacy_allowed_profile_json"):
            conn.execute("ALTER TABLE users ADD COLUMN privacy_allowed_profile_json TEXT DEFAULT '[]'")
        conn.execute("UPDATE users SET privacy_mode='public' WHERE privacy_mode IS NULL OR trim(privacy_mode)=''")
        conn.execute("UPDATE users SET privacy_allowed_json='[]' WHERE privacy_allowed_json IS NULL OR trim(privacy_allowed_json)=''")
        conn.execute(
            "UPDATE users SET privacy_allowed_map_json=privacy_allowed_json "
            "WHERE privacy_allowed_map_json IS NULL OR trim(privacy_allowed_map_json)=''"
        )
        conn.execute(
            "UPDATE users SET privacy_allowed_profile_json=privacy_allowed_json "
            "WHERE privacy_allowed_profile_json IS NULL OR trim(privacy_allowed_profile_json)=''"
        )

    def _normalize_privacy_mode(self, value):
        mode = str(value or "public").strip().lower()
        return "private" if mode == "private" else "public"

    def _parse_allowed_usernames(self, value):
        raw = value
        if isinstance(value, str):
            try:
                raw = json.loads(value)
            except Exception:
                raw = []
        if not isinstance(raw, list):
            raw = []
        out = []
        seen = set()
        for item in raw:
            uname = str(item or "").strip().lower()
            if not uname or uname in seen:
                continue
            seen.add(uname)
            out.append(uname)
        return out

    def _encode_allowed_usernames(self, usernames):
        if not isinstance(usernames, list):
            usernames = []
        cleaned = self._parse_allowed_usernames(usernames)
        return json.dumps(cleaned, ensure_ascii=False)

    def _get_user_privacy_row(self, conn, username: str):
        uname = (username or "").strip()
        if not uname:
            return None
        if not self._table_exists(conn, "users"):
            return None
        row = conn.execute(
            """
            SELECT username, role, privacy_mode, privacy_allowed_json,
                   privacy_allowed_map_json, privacy_allowed_profile_json
            FROM users
            WHERE lower(username)=lower(?)
            LIMIT 1
            """,
            (uname,),
        ).fetchone()
        if not row:
            return None
        allowed_legacy = self._parse_allowed_usernames(row["privacy_allowed_json"])
        allowed_map = self._parse_allowed_usernames(row["privacy_allowed_map_json"])
        allowed_profile = self._parse_allowed_usernames(row["privacy_allowed_profile_json"])
        if not allowed_map:
            allowed_map = list(allowed_legacy)
        if not allowed_profile:
            allowed_profile = list(allowed_legacy)
        return {
            "username": str(row["username"] or "").strip(),
            "role": str(row["role"] or "user").strip().lower(),
            "privacy_mode": self._normalize_privacy_mode(row["privacy_mode"]),
            "privacy_allowed": allowed_legacy,
            "privacy_allowed_map": allowed_map,
            "privacy_allowed_profile": allowed_profile,
        }

    def can_user_access_person(self, target_username: str, requester_username: str = "", requester_role: str = "user", access_scope: str = "profile"):
        role = str(requester_role or "user").strip().lower()
        requester = str(requester_username or "").strip().lower()
        target = str(target_username or "").strip()
        scope = str(access_scope or "profile").strip().lower()
        if not target:
            return False
        if role == "admin":
            return True
        with self._connect() as conn:
            target_row = self._get_user_privacy_row(conn, target)
        if not target_row:
            return True
        target_name_l = str(target_row["username"]).lower()
        if requester and requester == target_name_l:
            return True
        if target_row["privacy_mode"] != "private":
            return True
        if scope == "map":
            return requester in set(target_row["privacy_allowed_map"])
        return requester in set(target_row["privacy_allowed_profile"])

    def _get_or_create_api_key(self):
        with self._connect() as conn:
            row = conn.execute("SELECT meta_value FROM project_meta WHERE meta_key='api_key'").fetchone()
            if row and row["meta_value"]:
                return row["meta_value"]
            new_key = secrets.token_hex(24)
            conn.execute(
                "INSERT OR REPLACE INTO project_meta(meta_key, meta_value) VALUES ('api_key', ?)",
                (new_key,),
            )
            conn.commit()
            return new_key

    def _get_or_create_token_secret(self):
        with self._connect() as conn:
            row = conn.execute("SELECT meta_value FROM project_meta WHERE meta_key='api_token_secret'").fetchone()
            if row and row["meta_value"]:
                return row["meta_value"]
            secret = secrets.token_hex(32)
            conn.execute(
                "INSERT OR REPLACE INTO project_meta(meta_key, meta_value) VALUES ('api_token_secret', ?)",
                (secret,),
            )
            conn.commit()
            return secret

    def rotate_api_key(self):
        new_key = secrets.token_hex(24)
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO project_meta(meta_key, meta_value) VALUES ('api_key', ?)",
                (new_key,),
            )
            conn.commit()
        self.api_key = new_key
        self._log_activity("API Key Rotated", "New API key generated")
        return new_key

    def rotate_token_secret(self):
        secret = secrets.token_hex(32)
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO project_meta(meta_key, meta_value) VALUES ('api_token_secret', ?)",
                (secret,),
            )
            conn.commit()
        self.token_secret = secret
        self._log_activity("Token Secret Rotated", "API token secret rotated")
        return secret

    def generate_access_token(self, subject: str = "admin", ttl_minutes: int = 120, role: str = "user"):
        if ttl_minutes < 1:
            ttl_minutes = 1
        if ttl_minutes > 10080:
            ttl_minutes = 10080
        now_ts = int(time.time())
        exp_ts = now_ts + int(ttl_minutes * 60)
        payload = {"sub": subject, "role": role, "iat": now_ts, "exp": exp_ts}
        payload_text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        payload_b64 = base64.urlsafe_b64encode(payload_text.encode("utf-8")).decode("ascii").rstrip("=")
        sig = hmac.new(self.token_secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
        sig_b64 = base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")
        token = f"{payload_b64}.{sig_b64}"
        return {
            "token": token,
            "subject": subject,
            "expires_at": datetime.fromtimestamp(exp_ts).strftime("%Y-%m-%d %H:%M:%S"),
            "ttl_minutes": ttl_minutes,
        }

    def decode_access_token(self, token: str):
        if not token or "." not in token:
            return None
        payload_b64, sig_b64 = token.split(".", 1)
        expected_sig = hmac.new(self.token_secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode("ascii").rstrip("=")
        if not hmac.compare_digest(sig_b64, expected_sig_b64):
            return None
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        try:
            payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
        except Exception:
            return None
        now_ts = int(time.time())
        if int(payload.get("exp", 0)) < now_ts:
            return None
        return payload

    def _validate_access_token(self, token: str):
        return self.decode_access_token(token) is not None

    def _hash_password(self, password: str):
        return hashlib.sha256(f"{PASSWORD_SALT}{password}".encode("utf-8")).hexdigest()

    def _verify_password(self, password: str, hashed: str):
        if not hashed:
            return False
        stored = str(hashed)
        if self._hash_password(password) == stored:
            return True
        return password == stored

    def _send_email(self, to_email: str, subject: str, body: str):
        host = os.environ.get("FACESTUDIO_SMTP_HOST", "smtp.gmail.com").strip()
        user = os.environ.get("FACESTUDIO_SMTP_USER", "shishirbhavsar4@gmail.com").strip()
        password = (os.environ.get("FACESTUDIO_SMTP_APP_PASSWORD", "mlyu ajgr zorl foog") or os.environ.get("FACESTUDIO_SMTP_PASS", "")).strip()
        from_email = os.environ.get("FACESTUDIO_SMTP_FROM", "facestudio4@gmail.com").strip() or user
        port_text = os.environ.get("FACESTUDIO_SMTP_PORT", "587").strip()
        use_tls = os.environ.get("FACESTUDIO_SMTP_TLS", "1").strip().lower() not in ("0", "false", "no")
        use_ssl = os.environ.get("FACESTUDIO_SMTP_SSL", "0").strip().lower() in ("1", "true", "yes", "on")
        timeout_text = os.environ.get("FACESTUDIO_SMTP_TIMEOUT", "10").strip()
        total_timeout_text = os.environ.get("FACESTUDIO_SMTP_TOTAL_TIMEOUT", "9").strip()

        if not host or not user or not password or not from_email:
            return {"ok": False, "error": "SMTP is not configured"}

        try:
            port = int(port_text)
        except Exception:
            port = 587

        try:
            smtp_timeout = max(3, min(int(timeout_text), 30))
        except Exception:
            smtp_timeout = 10

        try:
            total_timeout = max(4, min(int(total_timeout_text), 40))
        except Exception:
            total_timeout = 9

        if "gmail.com" in host.lower() and " " in password:
            password = password.replace(" ", "")

        if port == 465 and not use_ssl:
            use_ssl = True
            use_tls = False

        message = EmailMessage()
        message["From"] = from_email
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        attempts = [(port, use_ssl, use_tls)]
        if (587, False, True) not in attempts:
            attempts.append((587, False, True))
        if (465, True, False) not in attempts:
            attempts.append((465, True, False))

        last_error = "unknown"
        started_at = time.time()
        for p, ssl_mode, tls_mode in attempts:
            elapsed = time.time() - started_at
            remaining = total_timeout - elapsed
            if remaining <= 1:
                last_error = "SMTP timeout"
                break
            per_try_timeout = max(3, min(smtp_timeout, int(remaining)))
            try:
                if ssl_mode:
                    smtp_client = smtplib.SMTP_SSL(host, p, timeout=per_try_timeout)
                else:
                    smtp_client = smtplib.SMTP(host, p, timeout=per_try_timeout)
                with smtp_client as smtp:
                    smtp.ehlo()
                    if tls_mode and not ssl_mode:
                        smtp.starttls()
                        smtp.ehlo()
                    smtp.login(user, password)
                    smtp.send_message(message)
                return {"ok": True}
            except smtplib.SMTPAuthenticationError as ex:
                return {
                    "ok": False,
                    "error": "SMTP authentication failed. Use Google App Password in FACESTUDIO_SMTP_APP_PASSWORD.",
                    "detail": str(ex),
                }
            except TimeoutError:
                last_error = "SMTP timeout"
            except OSError as ex:
                last_error = f"SMTP network error: {ex}"
            except Exception as ex:
                last_error = str(ex)

        return {"ok": False, "error": f"Failed to send email: {last_error}"}

    def authenticate_user(self, identifier: str, password: str):
        ident = (identifier or "").strip()
        if not ident or not password:
            return None
        with self._connect() as conn:
            if not self._table_exists(conn, "users"):
                return None
            row = conn.execute(
                """
                SELECT username, email, phone, role, password, created, logins_json,
                       privacy_mode, privacy_allowed_json,
                       privacy_allowed_map_json, privacy_allowed_profile_json
                FROM users
                WHERE lower(username)=lower(?) OR lower(email)=lower(?)
                LIMIT 1
                """,
                (ident, ident),
            ).fetchone()
            if not row:
                return None
            if not self._verify_password(password, row["password"]):
                return None

            if str(row["password"] or "") == password:
                try:
                    conn.execute(
                        "UPDATE users SET password=? WHERE username=?",
                        (self._hash_password(password), row["username"]),
                    )
                    conn.commit()
                except Exception:
                    pass

            username = row["username"]
            role = (row["role"] or "user").lower()
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                logins = json.loads(row["logins_json"] or "[]")
                if not isinstance(logins, list):
                    logins = []
            except Exception:
                logins = []
            logins.append(ts)
            logins = logins[-100:]
            try:
                conn.execute(
                    "UPDATE users SET logins_json=? WHERE username=?",
                    (json.dumps(logins, ensure_ascii=False), username),
                )
                conn.commit()
            except Exception:
                pass

        self._log_activity("Login", f"{username} signed in", username=username, role=role)
        return {
            "username": username,
            "email": row["email"] or "",
            "phone": row["phone"] or "",
            "role": role,
            "created": row["created"] or "",
            "privacy_mode": self._normalize_privacy_mode(row["privacy_mode"]),
            "privacy_allowed": self._parse_allowed_usernames(row["privacy_allowed_json"]),
            "privacy_allowed_map": self._parse_allowed_usernames(row["privacy_allowed_map_json"]),
            "privacy_allowed_profile": self._parse_allowed_usernames(row["privacy_allowed_profile_json"]),
        }

    def register_user(self, username: str, email: str, phone: str, password: str):
        username = (username or "").strip()
        email = (email or "").strip()
        phone = (phone or "").strip()
        password = password or ""

        if not username and email and "@" in email:
            username = email.split("@", 1)[0].strip()
        if not username:
            return {"ok": False, "error": "username or email is required"}
        if len(password) < 4:
            return {"ok": False, "error": "password must be at least 4 characters"}

        with self._connect() as conn:
            if not self._table_exists(conn, "users"):
                return {"ok": False, "error": "users table is missing"}

            exists = conn.execute(
                "SELECT username FROM users WHERE lower(username)=lower(?) OR lower(email)=lower(?) LIMIT 1",
                (username, email),
            ).fetchone()
            if exists:
                return {"ok": False, "error": "Account already exists. Please log in with your username or email."}

            created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                """
                INSERT INTO users(username, password, email, phone, role, created, logins_json, verified_email, data_json, privacy_mode, privacy_allowed_json, privacy_allowed_map_json, privacy_allowed_profile_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    self._hash_password(password),
                    email,
                    phone,
                    "user",
                    created,
                    "[]",
                    1,
                    "{}",
                    "public",
                    "[]",
                    "[]",
                    "[]",
                ),
            )
            conn.commit()

        self._log_activity("Signup", f"{username} created account", username=username, role="user")
        return {
            "ok": True,
            "data": {
                "username": username,
                "email": email,
                "phone": phone,
                "role": "user",
                "created": created,
                "privacy_mode": "public",
                "privacy_allowed": [],
                "privacy_allowed_map": [],
                "privacy_allowed_profile": [],
            },
        }

    def begin_signup_verification(self, username: str, email: str, phone: str, password: str):
        username = (username or "").strip()
        email = (email or "").strip()
        phone = (phone or "").strip()
        password = password or ""

        if not email or "@" not in email:
            return {"ok": False, "error": "valid email is required"}
        if not username:
            username = email.split("@", 1)[0].strip()
        if not username:
            return {"ok": False, "error": "username or email is required"}
        if len(password) < 4:
            return {"ok": False, "error": "password must be at least 4 characters"}

        with self._connect() as conn:
            if not self._table_exists(conn, "users"):
                return {"ok": False, "error": "users table is missing"}
            exists = conn.execute(
                "SELECT username FROM users WHERE lower(username)=lower(?) OR lower(email)=lower(?) LIMIT 1",
                (username, email),
            ).fetchone()
            if exists:
                return {"ok": False, "error": "Account already exists. Please log in with your username or email."}

        code = f"{randint(100000, 999999)}"
        expires_at = time.time() + 600
        email_key = email.lower()
        self._pending_signup_codes[email_key] = {
            "username": username,
            "email": email,
            "phone": phone,
            "password": password,
            "code": code,
            "expires_at": expires_at,
        }
                                                                                                                                                                                                                                                                                                            
        email_result = self._send_email(
            to_email=email,
            subject="Face Studio Email Verification Code",
            body=(
                f"Hello {username},\n\n"
                f"Your Face Studio verification code is: {code}\n"
                "This code will expire in 10 minutes.\n\n"
                "If you did not request this signup, you can ignore this email."
            ),
        )
        if email_result.get("ok") is not True:
            allow_fallback = os.getenv("FACESTUDIO_SIGNUP_ALLOW_SMTP_FALLBACK", "1").strip().lower() in (
                "1",
                "true",
                "yes",
                "on",
            )
            if not allow_fallback:
                self._pending_signup_codes.pop(email_key, None)
                return {"ok": False, "error": email_result.get("error", "Failed to send verification email")}

            smtp_error = str(email_result.get("error", "SMTP send failed"))
            self._log_activity(
                "Signup Verification Fallback",
                f"SMTP failed for {email}: {smtp_error}",
                username=username,
                role="user",
            )
            return {
                "ok": True,
                "data": {
                    "username": username,
                    "email": email,
                    "expires_in_seconds": 600,
                    "mail_sent": False,
                    "verification_code": code,
                    "smtp_error": smtp_error,
                },
            }

        self._log_activity("Signup Verification Requested", f"Verification code sent to {email}", username=username, role="user")
        return {
            "ok": True,
            "data": {
                "username": username,
                "email": email,
                "expires_in_seconds": 600,
                "mail_sent": True,
            },
        }

    def complete_signup_verification(self, email: str, code: str):
        email = (email or "").strip()
        code = (code or "").strip()
        if not email or not code:
            return {"ok": False, "error": "email and code are required"}

        rec = self._pending_signup_codes.get(email.lower())
        if not rec:
            return {"ok": False, "error": "signup verification not requested"}
        if time.time() > float(rec.get("expires_at", 0)):
            self._pending_signup_codes.pop(email.lower(), None)
            return {"ok": False, "error": "verification code expired"}
        if code != str(rec.get("code", "")):
            return {"ok": False, "error": "invalid verification code"}

        result = self.register_user(
            username=str(rec.get("username", "")).strip(),
            email=str(rec.get("email", "")).strip(),
            phone=str(rec.get("phone", "")).strip(),
            password=str(rec.get("password", "")),
        )
        if result.get("ok") is True:
            self._pending_signup_codes.pop(email.lower(), None)
            self._log_activity("Signup Verified", f"Email verified for {email}", username=str(rec.get("username", "")).strip(), role="user")
        return result

    def begin_password_reset(self, identifier: str):
        ident = (identifier or "").strip()
        if not ident:
            return {"ok": False, "error": "identifier is required"}

        with self._connect() as conn:
            if not self._table_exists(conn, "users"):
                return {"ok": False, "error": "users table is missing"}
            row = conn.execute(
                "SELECT username, email FROM users WHERE lower(username)=lower(?) OR lower(email)=lower(?) LIMIT 1",
                (ident, ident),
            ).fetchone()
            if not row:
                return {"ok": False, "error": "user not found"}
            username = str(row["username"])

        code = f"{randint(100000, 999999)}"
        expires_at = time.time() + 600
        self._pending_reset_codes[username.lower()] = {
            "username": username,
            "email": str(row["email"] or "").strip(),
            "code": code,
            "expires_at": expires_at,
        }
        rec_email = str(row["email"] or "").strip()
        if rec_email and "@" in rec_email:
            email_result = self._send_email(
                to_email=rec_email,
                subject="Face Studio Password Reset Code",
                body=(
                    f"Hello {username},\n\n"
                    f"Your Face Studio password reset code is: {code}\n"
                    "This code will expire in 10 minutes.\n\n"
                    "If you did not request a password reset, ignore this email."
                ),
            )
            if email_result.get("ok") is True:
                self._log_activity(
                    "Password Reset Requested",
                    f"Reset code mailed to {rec_email}",
                    username=username,
                    role="user",
                )
                return {
                    "ok": True,
                    "data": {
                        "username": username,
                        "mail_sent": True,
                        "expires_in_seconds": 600,
                    },
                }

            smtp_error = str(email_result.get("error", "SMTP send failed"))
            self._log_activity(
                "Password Reset Fallback",
                f"SMTP failed for {rec_email}: {smtp_error}",
                username=username,
                role="user",
            )
            return {
                "ok": True,
                "data": {
                    "username": username,
                    "mail_sent": False,
                    "code": code,
                    "smtp_error": smtp_error,
                    "expires_in_seconds": 600,
                    "note": "SMTP failed, use this code directly",
                },
            }

        self._log_activity("Password Reset Requested", f"Reset requested for {username}", username=username, role="user")
        return {
            "ok": True,
            "data": {
                "username": username,
                "mail_sent": False,
                "code": code,
                "expires_in_seconds": 600,
                "note": "No email configured for this user, use this code directly",
            },
        }

    def reset_password_with_code(self, username: str, code: str, new_password: str):
        uname = (username or "").strip().lower()
        code = (code or "").strip()
        new_password = new_password or ""
        if len(new_password) < 4:
            return {"ok": False, "error": "new password must be at least 4 characters"}
        rec = self._pending_reset_codes.get(uname)
        if not rec:
            return {"ok": False, "error": "reset not requested"}
        if time.time() > float(rec.get("expires_at", 0)):
            self._pending_reset_codes.pop(uname, None)
            return {"ok": False, "error": "reset code expired"}
        if code != str(rec.get("code", "")):
            return {"ok": False, "error": "invalid reset code"}

        with self._connect() as conn:
            if not self._table_exists(conn, "users"):
                return {"ok": False, "error": "users table is missing"}
            conn.execute(
                "UPDATE users SET password=? WHERE lower(username)=lower(?)",
                (self._hash_password(new_password), rec.get("username", "")),
            )
            conn.commit()

        self._pending_reset_codes.pop(uname, None)
        self._log_activity("Password Reset", f"Password reset for {rec.get('username', '')}", username=rec.get("username", ""), role="user")
        return {"ok": True, "data": {"username": rec.get("username", "")}}

    def get_user_profile(self, username: str):
        uname = (username or "").strip()
        if not uname:
            return None
        with self._connect() as conn:
            if not self._table_exists(conn, "users"):
                return None
            row = conn.execute(
                "SELECT username, email, phone, role, created, logins_json, privacy_mode, privacy_allowed_json, privacy_allowed_map_json, privacy_allowed_profile_json FROM users WHERE username=? LIMIT 1",
                (uname,),
            ).fetchone()
            if not row:
                return None
        try:
            logins = json.loads(row["logins_json"] or "[]")
            if not isinstance(logins, list):
                logins = []
        except Exception:
            logins = []
        return {
            "username": row["username"],
            "email": row["email"] or "",
            "phone": row["phone"] or "",
            "role": (row["role"] or "user").lower(),
            "created": row["created"] or "",
            "recent_logins": list(reversed(logins[-10:])),
            "privacy_mode": self._normalize_privacy_mode(row["privacy_mode"]),
            "privacy_allowed": self._parse_allowed_usernames(row["privacy_allowed_json"]),
            "privacy_allowed_map": self._parse_allowed_usernames(row["privacy_allowed_map_json"]),
            "privacy_allowed_profile": self._parse_allowed_usernames(row["privacy_allowed_profile_json"]),
        }

    def update_user_privacy(self, target_username: str, privacy_mode: str, allowed_usernames, allowed_map_usernames, allowed_profile_usernames, actor_username: str, actor_role: str):
        target = (target_username or "").strip()
        actor = (actor_username or "").strip().lower()
        role = (actor_role or "user").strip().lower()
        if not target:
            return {"ok": False, "error": "target username is required"}
        if role != "admin" and actor != target.lower():
            return {"ok": False, "error": "Only owner or admin can change privacy"}

        mode = self._normalize_privacy_mode(privacy_mode)
        allowed_legacy = self._parse_allowed_usernames(allowed_usernames)
        allowed_map = self._parse_allowed_usernames(allowed_map_usernames)
        allowed_profile = self._parse_allowed_usernames(allowed_profile_usernames)
        if not allowed_map:
            allowed_map = list(allowed_legacy)
        if not allowed_profile:
            allowed_profile = list(allowed_legacy)
        allowed_legacy = [u for u in allowed_legacy if u != target.lower()]
        allowed_map = [u for u in allowed_map if u != target.lower()]
        allowed_profile = [u for u in allowed_profile if u != target.lower()]

        with self._connect() as conn:
            if not self._table_exists(conn, "users"):
                return {"ok": False, "error": "users table is missing"}
            self._ensure_users_privacy_columns(conn)
            exists = conn.execute(
                "SELECT username FROM users WHERE lower(username)=lower(?) LIMIT 1",
                (target,),
            ).fetchone()
            if not exists:
                return {"ok": False, "error": "User not found"}
            conn.execute(
                "UPDATE users SET privacy_mode=?, privacy_allowed_json=?, privacy_allowed_map_json=?, privacy_allowed_profile_json=? WHERE lower(username)=lower(?)",
                (
                    mode,
                    self._encode_allowed_usernames(allowed_legacy),
                    self._encode_allowed_usernames(allowed_map),
                    self._encode_allowed_usernames(allowed_profile),
                    target,
                ),
            )
            conn.commit()

        self._log_activity(
            "Privacy Updated",
            f"{target} set profile to {mode}",
            username=target,
            role=role,
        )
        profile = self.get_user_profile(target)
        return {"ok": True, "data": profile}

    def get_api_docs(self):
        base = f"http://{self.host}:{self.port}"
        return {
            "name": "Face Studio API",
            "base_url": base,
            "auth": {
                "api_key_header": "X-API-Key",
                "bearer_header": "Authorization: Bearer <token>",
                "token_issue": f"{base}/api/auth/token?subject=demo&ttl=120",
            },
            "public_endpoints": [
                {"path": "/api/health", "method": "GET"},
                {"path": "/api/docs", "method": "GET"},
                {"path": "/api/map/view", "method": "GET"},
                {"path": "/api/mobile/app-update", "method": "GET"},
                {"path": "/api/auth/login", "method": "POST", "body": "{identifier, password, ttl?}"},
                {"path": "/api/auth/signup", "method": "POST", "body": "{username?, email?, phone?, password}"},
                {"path": "/api/auth/signup/request", "method": "POST", "body": "{username?, email, phone?, password}"},
                {"path": "/api/auth/signup/verify", "method": "POST", "body": "{email, code, ttl?}"},
                {"path": "/api/auth/password/request", "method": "POST", "body": "{identifier}"},
                {"path": "/api/auth/password/reset", "method": "POST", "body": "{username, code, new_password}"},
            ],
            "secure_endpoints": [
                {"path": "/api/stats", "method": "GET"},
                {"path": "/api/system-info", "method": "GET"},
                {"path": "/api/users?limit=200", "method": "GET"},
                {"path": "/api/activity?limit=200", "method": "GET"},
                {"path": "/api/db/overview", "method": "GET"},
                {"path": "/api/events/stream", "method": "GET"},
                {"path": "/api/mobile/styles", "method": "GET"},
                {"path": "/api/mobile/identify", "method": "POST", "body": "{image_b64, top_k?}"},
                {"path": "/api/mobile/generate", "method": "POST", "body": "{image_b64, filter_name}"},
                {"path": "/api/mobile/compare", "method": "POST", "body": "{left_image_b64, right_image_b64}"},
                {"path": "/api/mobile/recognition-location/save", "method": "POST", "body": "{recognized_name, location_name, latitude?, longitude?, confidence?}"},
                {"path": "/api/mobile/recognition-location/search?name=<username>&limit=50", "method": "GET"},
                {"path": "/api/admin/advanced-lab", "method": "GET"},
                {"path": "/api/admin/enterprise-control", "method": "GET"},
                {"path": "/api/admin/evaluator-bundle", "method": "GET"},
                {"path": "/api/admin/evaluator-bundle/export", "method": "POST"},
                {"path": "/api/admin/judge-mode", "method": "GET"},
                {"path": "/api/admin/demo-launcher", "method": "GET"},
                {"path": "/api/admin/presentation-startup", "method": "GET"},
                {"path": "/api/admin/backup/now", "method": "POST"},
                {"path": "/api/admin/scheduler/start", "method": "POST"},
                {"path": "/api/admin/scheduler/stop", "method": "POST"},
                {"path": "/api/admin/faces/sync", "method": "POST", "body": "{entries:[{person,filename,image_b64}], clear_existing?}"},
                {"path": "/api/auth/token?subject=demo&ttl=120", "method": "GET", "requires": "X-API-Key"},
            ],
        }

    def get_mobile_app_update_info(self):
        latest_version = os.getenv("FACE_STUDIO_MOBILE_LATEST_VERSION", "0.1.0+13").strip()
        minimum_version = os.getenv("FACE_STUDIO_MOBILE_MIN_VERSION", "0.1.0+12").strip()
        apk_url = os.getenv(
            "FACE_STUDIO_MOBILE_APK_URL",
            "https://github.com/facestudio4/facerecognition/releases/latest",
        ).strip()
        notes = os.getenv(
            "FACE_STUDIO_MOBILE_UPDATE_NOTES",
            "A new version is available with performance and stability improvements.",
        ).strip()
        force_update = os.getenv("FACE_STUDIO_MOBILE_FORCE_UPDATE", "false").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        return {
            "latest_version": latest_version,
            "minimum_version": minimum_version,
            "apk_url": apk_url,
            "notes": notes,
            "force_update": force_update,
        }

    def get_world_map_html(self):
        candidate_paths = [
            os.path.join(self.base_dir, "map.html"),
            os.path.join(os.path.dirname(self.base_dir), "map.html"),
        ]
        for path in candidate_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception:
                    continue

        return """
<!doctype html>
<html>
<head>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1'>
    <title>World Map</title>
    <style>
        body { margin: 0; font-family: Arial, sans-serif; background: #11182A; color: #E5EEFF; }
        .box { padding: 16px; }
        h3 { margin: 0 0 8px; }
    </style>
</head>
<body>
    <div class='box'>
        <h3>Map Not Found</h3>
        <p>map.html was not found. Run map.py to regenerate it.</p>
    </div>
</body>
</html>
"""

    def get_db_overview(self):
        overview = {
            "db_path": self.db_path,
            "db_exists": os.path.exists(self.db_path),
            "db_size_mb": round(os.path.getsize(self.db_path) / (1024 * 1024), 4) if os.path.exists(self.db_path) else 0.0,
            "tables": [],
        }
        with self._connect() as conn:
            rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
            for row in rows:
                tname = str(row["name"])
                try:
                    count = conn.execute(f"SELECT COUNT(*) c FROM {tname}").fetchone()["c"]
                except Exception:
                    count = -1
                overview["tables"].append({"name": tname, "rows": count})
        return overview

    def get_system_info_summary(self, role: str = "user"):
        current_role = (role or "user").strip().lower()
        is_admin = current_role == "admin"

        model_roots = [
            os.path.join(self.base_dir, "config", "models"),
            os.path.join(os.path.dirname(self.base_dir), "config", "models"),
        ]

        def _model_path(filename: str):
            for root in model_roots:
                path = os.path.join(root, filename)
                if os.path.exists(path):
                    return path
            return os.path.join(model_roots[0], filename)

        yunet_path = _model_path("face_detection_yunet_2023mar.onnx")
        sface_path = _model_path("face_recognition_sface_2021dec.onnx")

        yunet_kb = (os.path.getsize(yunet_path) / 1024.0) if os.path.exists(yunet_path) else 0.0
        sface_mb = (os.path.getsize(sface_path) / (1024.0 * 1024.0)) if os.path.exists(sface_path) else 0.0

        faces_root_candidates = [
            os.path.join(self.base_dir, "database", "faces"),
            os.path.join(os.path.dirname(self.base_dir), "database", "faces"),
        ]
        faces_root = ""
        for cand in faces_root_candidates:
            if os.path.isdir(cand):
                faces_root = cand
                break
        if not faces_root:
            faces_root = faces_root_candidates[0]

        ignored = {"known_faces", "archive", "__pycache__"}
        image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        people_dirs = []
        total_images = 0
        if os.path.isdir(faces_root):
            for name in os.listdir(faces_root):
                path = os.path.join(faces_root, name)
                if not os.path.isdir(path):
                    continue
                if name.lower() in ignored:
                    continue
                people_dirs.append(name)
                try:
                    total_images += len(
                        [f for f in os.listdir(path) if os.path.splitext(f)[1].lower() in image_exts]
                    )
                except Exception:
                    continue

        threshold = 0.363
        frame_scale = 0.5
        stability_window = 5
        enc_cache_kb = 0.0
        try:
            from frontend import facercognition as legacy

            threshold = float(getattr(legacy, "RECOGNITION_THRESHOLD", threshold))
            frame_scale = float(getattr(legacy, "FRAME_SCALE", frame_scale))
            stability_window = int(getattr(legacy, "STABILITY_WINDOW", stability_window))
            enc_path = str(getattr(legacy, "ENCODINGS_PATH", "")).strip()
            if enc_path and os.path.exists(enc_path):
                enc_cache_kb = os.path.getsize(enc_path) / 1024.0
        except Exception:
            pass

        users_count = 0
        attendance_count = 0
        face_log_count = 0
        activity_count = 0
        with self._connect() as conn:
            if self._table_exists(conn, "users"):
                users_count = int(conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"])
            if self._table_exists(conn, "attendance_entries"):
                attendance_count = int(conn.execute("SELECT COUNT(*) c FROM attendance_entries").fetchone()["c"])
            if self._table_exists(conn, "face_events"):
                face_log_count = int(conn.execute("SELECT COUNT(*) c FROM face_events").fetchone()["c"])
            if self._table_exists(conn, "activity_events"):
                activity_count = int(conn.execute("SELECT COUNT(*) c FROM activity_events").fetchone()["c"])

        total_size_mb = 0.0
        if is_admin:
            for root, _, files in os.walk(self.base_dir):
                for filename in files:
                    fp = os.path.join(root, filename)
                    try:
                        total_size_mb += os.path.getsize(fp)
                    except OSError:
                        continue
            total_size_mb = total_size_mb / (1024.0 * 1024.0)

        rows = [
            {"label": "Python Version", "value": sys.version.split()[0]},
            {"label": "OpenCV Version", "value": cv2.__version__},
            {"label": "NumPy Version", "value": np.__version__},
            {"label": "Platform", "value": sys.platform},
            {"label": "YuNet Model", "value": f"{yunet_kb:.0f} KB"},
            {"label": "SFace Model", "value": f"{sface_mb:.1f} MB"},
        ]

        if is_admin:
            rows.extend(
                [
                    {"label": "Registered People", "value": len(people_dirs)},
                    {"label": "Total Face Images", "value": total_images},
                    {"label": "Encodings Cache", "value": f"{enc_cache_kb:.0f} KB"},
                    {"label": "Face Log Entries", "value": face_log_count},
                    {"label": "Activity Log Entries", "value": activity_count},
                    {"label": "User Accounts", "value": users_count},
                    {"label": "Attendance Sessions", "value": attendance_count},
                    {"label": "Recognition Threshold", "value": threshold},
                    {"label": "Frame Scale", "value": frame_scale},
                    {"label": "Stability Window", "value": stability_window},
                    {"label": "Total Project Size", "value": f"{total_size_mb:.1f} MB"},
                ]
            )
        else:
            rows.extend(
                [
                    {"label": "Mode", "value": "User (restricted view)"},
                    {"label": "Recognition Threshold", "value": threshold},
                    {"label": "Frame Scale", "value": frame_scale},
                    {"label": "Stability Window", "value": stability_window},
                ]
            )

        return {
            "role": current_role,
            "rows": rows,
        }

    def admin_advanced_lab_summary(self):
        stats = self.get_stats()
        db = self.get_db_overview()
        recent = self.list_recent_activity(limit=25)
        return {
            "module": "Advanced Project Lab",
            "stats": stats,
            "db": db,
            "recent_activity": recent,
            "checks": {
                "api_running": bool(self._api_thread and self._api_thread.is_alive()),
                "scheduler_running": self.is_scheduler_running(),
                "last_backup_at": self._last_backup_at,
            },
        }

    def admin_enterprise_control_summary(self):
        users = self.list_users(limit=2000)
        role_breakdown = {"admin": 0, "user": 0, "other": 0}
        for u in users:
            role = str(u.get("role", "user")).lower()
            if role in role_breakdown:
                role_breakdown[role] += 1
            else:
                role_breakdown["other"] += 1
        return {
            "module": "Enterprise Control Center",
            "users_total": len(users),
            "role_breakdown": role_breakdown,
            "pending_approvals": self.get_stats().get("pending_approvals", 0),
            "recent_activity": self.list_recent_activity(limit=30),
        }

    def admin_evaluator_bundle_summary(self):
        kit_dir = os.path.join(self.base_dir, "demo_kit")
        docs_path = os.path.join(kit_dir, "api_docs.json")
        ps1_path = os.path.join(kit_dir, "quick_demo.ps1")
        py_path = os.path.join(kit_dir, "quick_demo.py")
        return {
            "module": "Evaluator Bundle",
            "kit_dir": kit_dir,
            "files": {
                "api_docs_json": {"path": docs_path, "exists": os.path.exists(docs_path)},
                "quick_demo_ps1": {"path": ps1_path, "exists": os.path.exists(ps1_path)},
                "quick_demo_py": {"path": py_path, "exists": os.path.exists(py_path)},
            },
            "stats": self.get_stats(),
        }

    def admin_judge_mode_summary(self):
        recent = self.list_recent_activity(limit=10)
        latest = recent[0] if recent else None
        return {
            "module": "Judge Mode",
            "latest_event": latest,
            "stats": self.get_stats(),
            "db": self.get_db_overview(),
        }

    def admin_demo_launcher_summary(self):
        return {
            "module": "Demo Launcher",
            "health": {"ok": True, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            "stats": self.get_stats(),
            "services": {
                "api_running": bool(self._api_thread and self._api_thread.is_alive()),
                "backup_scheduler_running": self.is_scheduler_running(),
            },
            "next_steps": [
                "Verify mobile login",
                "Run live recognition",
                "Export evaluator bundle",
            ],
        }

    def admin_presentation_startup_summary(self):
        return {
            "module": "Presentation Startup",
            "api_docs": self.get_api_docs(),
            "stats": self.get_stats(),
            "recent_activity": self.list_recent_activity(limit=15),
        }

    def save_recognition_location_event(
        self,
        recognized_name: str,
        location_name: str,
        latitude=None,
        longitude=None,
        confidence=None,
        source: str = "mobile_live",
        requested_by: str = "mobile",
        force_update: bool = False,
    ):
        name = (recognized_name or "").strip()
        location = (location_name or "").strip()
        if not name or name.lower() == "unknown":
            return {"ok": False, "error": "recognized_name is required"}
        if not location:
            return {"ok": False, "error": "location_name is required"}

        def _as_float(value):
            if value is None:
                return None
            try:
                return float(value)
            except Exception:
                return None

        lat = _as_float(latitude)
        lng = _as_float(longitude)
        conf = _as_float(confidence)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self._connect() as conn:
            last = conn.execute(
                """
                SELECT id, event_time
                FROM recognition_location_events
                WHERE lower(recognized_name)=lower(?) AND lower(location_name)=lower(?)
                ORDER BY id DESC
                LIMIT 1
                """,
                (name, location),
            ).fetchone()
            if (not force_update) and last and last["event_time"]:
                try:
                    prev_ts = datetime.strptime(last["event_time"], "%Y-%m-%d %H:%M:%S")
                    if (datetime.now() - prev_ts).total_seconds() < 12:
                        return {
                            "ok": True,
                            "data": {
                                "saved": False,
                                "reason": "deduped_recent_event",
                                "event_id": int(last["id"]),
                            },
                        }
                except Exception:
                    pass

            payload = {
                "event_time": ts,
                "recognized_name": name,
                "location_name": location,
                "latitude": lat,
                "longitude": lng,
                "confidence": conf,
                "source": source,
                "requested_by": requested_by,
            }
            cur = conn.execute(
                """
                INSERT INTO recognition_location_events(
                    event_time, recognized_name, location_name,
                    latitude, longitude, confidence,
                    source, requested_by, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ts,
                    name,
                    location,
                    lat,
                    lng,
                    conf,
                    source,
                    requested_by,
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            conn.commit()
            event_id = int(cur.lastrowid or 0)

        self._log_activity(
            "Recognition Location Saved",
            f"{name} recognized at {location}",
            username=requested_by,
            role="user",
        )
        return {"ok": True, "data": {"saved": True, "event_id": event_id, "event": payload}}

    def search_recognition_locations(self, name: str, limit: int = 100, latest_only: bool = False):
        person = (name or "").strip()
        if not person:
            return []
        limit = max(1, min(int(limit), 2000))
        with self._connect() as conn:
            if latest_only:
                rows = conn.execute(
                    """
                    SELECT
                        id,
                        event_time,
                        recognized_name,
                        location_name,
                        latitude,
                        longitude,
                        confidence,
                        source,
                        requested_by
                    FROM recognition_location_events
                    WHERE lower(recognized_name)=lower(?)
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (person,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT
                        id,
                        event_time,
                        recognized_name,
                        location_name,
                        latitude,
                        longitude,
                        confidence,
                        source,
                        requested_by
                    FROM recognition_location_events
                    WHERE lower(recognized_name)=lower(?)
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (person, limit),
                ).fetchall()
        return [dict(r) for r in rows]

    def _decode_image_b64(self, image_b64: str):
        if not image_b64:
            raise ValueError("image_b64 is required")
        payload = image_b64.strip()
        if "," in payload and payload.lower().startswith("data:image"):
            payload = payload.split(",", 1)[1]
        raw = base64.b64decode(payload)
        arr = np.frombuffer(raw, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Invalid image data")
        return img

    def _encode_image_b64(self, image: np.ndarray, quality: int = 84):
        quality = max(30, min(95, int(quality)))
        ok, buf = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if not ok:
            raise RuntimeError("Failed to encode image")
        return base64.b64encode(buf.tobytes()).decode("ascii")

    def _get_mobile_known_encodings(self):
        now = time.time()
        if self._mobile_known_encodings is not None and (now - self._mobile_known_loaded_at) < 120:
            return self._mobile_known_encodings
        from frontend import facercognition as legacy

        self._mobile_known_encodings = legacy.load_and_train(False)
        self._mobile_known_loaded_at = now
        return self._mobile_known_encodings

    def _sanitize_face_name(self, value: str):
        text = str(value or "").strip()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^A-Za-z0-9 _-]", "", text)
        text = text.strip(" ._")
        if not text:
            raise ValueError("Invalid person name")
        return text[:64]

    def _run_sync_refresh(self):
        try:
            self._mobile_known_encodings = None
            self._mobile_known_loaded_at = 0.0
            try:
                from frontend import facercognition as legacy
                enc_path = getattr(legacy, "ENCODINGS_PATH", "")
                if enc_path and os.path.exists(enc_path):
                    os.remove(enc_path)
            except Exception:
                pass
            self._get_mobile_known_encodings()
            self._sync_refresh_error = ""
        except Exception as ex:
            self._sync_refresh_error = str(ex)
        finally:
            self._sync_refresh_running = False

    def start_sync_refresh(self):
        if self._sync_refresh_running:
            return {"scheduled": False, "running": True, "error": self._sync_refresh_error}
        self._sync_refresh_running = True
        self._sync_refresh_error = ""
        self._sync_refresh_thread = threading.Thread(target=self._run_sync_refresh, daemon=True)
        self._sync_refresh_thread.start()
        return {"scheduled": True, "running": True, "error": ""}

    def sync_known_faces(self, entries, clear_existing: bool = False, refresh_after: bool = False):
        if not isinstance(entries, list) or not entries:
            raise ValueError("entries must be a non-empty list")

        faces_root = os.path.join(self.base_dir, "database", "faces")
        os.makedirs(faces_root, exist_ok=True)
        protected_dirs = {"known_faces", "archive", "__pycache__"}

        if clear_existing:
            for name in os.listdir(faces_root):
                path = os.path.join(faces_root, name)
                if not os.path.isdir(path):
                    continue
                if name.lower() in protected_dirs:
                    continue
                try:
                    shutil.rmtree(path)
                except Exception:
                    pass

        imported_files = 0
        imported_people = set()
        allowed_ext = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

        for item in entries:
            if not isinstance(item, dict):
                continue
            person = self._sanitize_face_name(item.get("person", ""))
            filename = os.path.basename(str(item.get("filename", "")).strip())
            if not filename:
                filename = f"{int(time.time() * 1000)}.jpg"
            root, ext = os.path.splitext(filename)
            if ext.lower() not in allowed_ext:
                ext = ".jpg"
            safe_root = re.sub(r"[^A-Za-z0-9_-]", "_", root).strip("_") or "face"
            out_name = f"{safe_root}{ext.lower()}"

            image_b64 = str(item.get("image_b64", "")).strip()
            if not image_b64:
                continue
            if image_b64.lower().startswith("data:image") and "," in image_b64:
                image_b64 = image_b64.split(",", 1)[1]
            try:
                raw = base64.b64decode(image_b64)
            except Exception:
                continue
            if not raw:
                continue

            person_dir = os.path.join(faces_root, person)
            os.makedirs(person_dir, exist_ok=True)
            out_path = os.path.join(person_dir, out_name)
            with open(out_path, "wb") as f:
                f.write(raw)
            imported_files += 1
            imported_people.add(person)

        self._mobile_known_encodings = None
        self._mobile_known_loaded_at = 0.0
        try:
            from frontend import facercognition as legacy
            enc_path = getattr(legacy, "ENCODINGS_PATH", "")
            if enc_path and os.path.exists(enc_path):
                os.remove(enc_path)
        except Exception:
            pass

        known_count = None
        refresh_state = {"scheduled": False, "running": bool(self._sync_refresh_running), "error": self._sync_refresh_error}
        if refresh_after:
            refresh_state = self.start_sync_refresh()

        return {
            "ok": True,
            "data": {
                "imported_files": imported_files,
                "imported_people": sorted(imported_people),
                "known_people_after_sync": known_count,
                "faces_root": faces_root,
                "refresh_after": bool(refresh_after),
                "refresh_scheduled": bool(refresh_state.get("scheduled", False)),
                "refresh_running": bool(refresh_state.get("running", False)),
                "refresh_error": str(refresh_state.get("error", "") or ""),
            },
        }

    def mobile_styles(self):
        from frontend import facercognition as legacy

        return list(getattr(legacy, "STYLE_LIST", []))

    def _legacy_detect_and_encode(self, legacy, frame):
        try:
            return legacy.detect_and_encode(frame)
        except TypeError as ex:
            if "detector" not in str(ex).lower():
                raise
            h, w = frame.shape[:2]
            detector = legacy._create_yunet(w, h)
            return legacy.detect_and_encode(frame, detector)

    def mobile_identify(self, image_b64: str, top_k: int = 3, tracking=None):
        from frontend import facercognition as legacy

        frame = self._decode_image_b64(image_b64)
        detections = self._legacy_detect_and_encode(legacy, frame)
        if not detections:
            return {
                "detected": False,
                "message": "No face detected",
                "face_count": 0,
                "faces": [],
                "image_width": int(frame.shape[1]),
                "image_height": int(frame.shape[0]),
                "best": {"name": "Unknown", "score": 0.0},
                "matches": [],
            }

        known = self._get_mobile_known_encodings()
        names = []
        encs = []
        for name, e_list in (known or {}).items():
            for e in e_list or []:
                names.append(name)
                encs.append(e)

        if not encs:
            return {
                "detected": True,
                "message": "No registered faces",
                "best": {"name": "Unknown", "score": 0.0},
                "matches": [],
            }

        enc_arr = np.array(encs)
        threshold_default = float(getattr(legacy, "RECOGNITION_THRESHOLD", 0.38))
        threshold_raw = os.getenv(
            "MOBILE_RECOGNITION_THRESHOLD",
            str(threshold_default),
        )
        try:
            threshold = float(threshold_raw)
        except Exception:
            threshold = 0.48
        threshold = max(0.25, min(0.85, threshold))

        margin_raw = os.getenv("MOBILE_RECOGNITION_MARGIN", "0.03")
        try:
            margin = float(margin_raw)
        except Exception:
            margin = 0.06
        margin = max(0.0, min(0.25, margin))
        top_k = max(1, min(int(top_k), 10))

        all_faces = []
        global_best = {"name": "Unknown", "score": 0.0}
        global_top = []
        for (fx, fy, fw, fh, embedding) in detections:
            raw_scores = []
            for i, known_enc in enumerate(enc_arr):
                score = legacy._sface_recognizer.match(
                    embedding.reshape(1, -1),
                    known_enc.reshape(1, -1),
                    cv2.FaceRecognizerSF_FR_COSINE,
                )
                raw_scores.append({"name": names[i], "score": float(score)})

            # Collapse per-image scores into a single best score per person.
            person_best = {}
            for rec in raw_scores:
                n = str(rec["name"])
                s = float(rec["score"])
                if s > float(person_best.get(n, -1.0)):
                    person_best[n] = s

            person_scores = [{"name": n, "score": s} for n, s in person_best.items()]
            person_scores.sort(key=lambda x: x["score"], reverse=True)

            top = person_scores[:top_k]
            best_candidate = top[0] if top else {"name": "Unknown", "score": 0.0}
            second_score = float(top[1]["score"]) if len(top) > 1 else 0.0
            ambiguous = len(top) > 1 and (float(best_candidate["score"]) - second_score) < margin

            if float(best_candidate["score"]) < threshold or ambiguous:
                best = {"name": "Unknown", "score": 0.0}
            else:
                best = best_candidate

            if best["score"] > float(global_best.get("score", 0.0)):
                global_best = best
                global_top = top

            all_faces.append(
                {
                    "bbox": {
                        "x": int(fx),
                        "y": int(fy),
                        "w": int(fw),
                        "h": int(fh),
                    },
                    "best": best,
                    "matches": top,
                }
            )

        result = {
            "detected": True,
            "threshold": threshold,
            "margin": margin,
            "known_people": len(known or {}),
            "known_vectors": len(encs),
            "face_count": len(all_faces),
            "faces": all_faces,
            "image_width": int(frame.shape[1]),
            "image_height": int(frame.shape[0]),
            "best": global_best,
            "matches": global_top,
        }

        track = tracking if isinstance(tracking, dict) else {}
        location_name = str(track.get("location_name", "")).strip()
        requested_by = str(track.get("requested_by", "mobile")).strip() or "mobile"
        if location_name and str(global_best.get("name", "")).strip() and str(global_best.get("name", "")).lower() != "unknown":
            saved = self.save_recognition_location_event(
                recognized_name=str(global_best.get("name", "")).strip(),
                location_name=location_name,
                latitude=track.get("latitude"),
                longitude=track.get("longitude"),
                confidence=global_best.get("score"),
                source="mobile_identify",
                requested_by=requested_by,
                force_update=bool(track.get("force_update", False)),
            )
            if saved.get("ok") is True:
                result["location_tracking"] = saved.get("data", {})
            else:
                result["location_tracking"] = {"saved": False, "error": saved.get("error", "unknown")}

        return result

    def mobile_generate(self, image_b64: str, filter_name: str):
        from frontend import facercognition as legacy

        if not filter_name:
            raise ValueError("filter_name is required")
        if filter_name not in getattr(legacy, "STYLE_LIST", []):
            raise ValueError(f"Unsupported filter_name: {filter_name}")

        frame = self._decode_image_b64(image_b64)
        result = legacy.apply_face_filter(frame, filter_name)
        out_b64 = self._encode_image_b64(result, quality=84)
        return {
            "filter_name": filter_name,
            "image_b64": out_b64,
            "width": int(result.shape[1]),
            "height": int(result.shape[0]),
        }

    def export_demo_kit(self):
        out_dir = os.path.join(self.base_dir, "demo_kit")
        os.makedirs(out_dir, exist_ok=True)
        docs = self.get_api_docs()
        docs_path = os.path.join(out_dir, "api_docs.json")
        with open(docs_path, "w", encoding="utf-8") as f:
            json.dump(docs, f, ensure_ascii=False, indent=2)
        ps1_path = os.path.join(out_dir, "quick_demo.ps1")
        with open(ps1_path, "w", encoding="utf-8") as f:
            f.write(
                "param([string]$Host='127.0.0.1',[int]$Port=8787,[string]$ApiKey='CHANGE_ME')\n"
                "$base = \"http://$Host`:$Port\"\n"
                "Invoke-RestMethod -Uri \"$base/api/health\"\n"
                "$tokenRes = Invoke-RestMethod -Headers @{ 'X-API-Key'=$ApiKey } -Uri \"$base/api/auth/token?subject=demo&ttl=30\"\n"
                "$token = $tokenRes.data.token\n"
                "Invoke-RestMethod -Headers @{ 'Authorization'=(\"Bearer \" + $token) } -Uri \"$base/api/stats\"\n"
                "Invoke-RestMethod -Headers @{ 'Authorization'=(\"Bearer \" + $token) } -Uri \"$base/api/users?limit=5\"\n"
            )
        py_path = os.path.join(out_dir, "quick_demo.py")
        with open(py_path, "w", encoding="utf-8") as f:
            f.write(
                "import urllib.request, json\n"
                "BASE='http://127.0.0.1:8787'\n"
                "API_KEY='CHANGE_ME'\n"
                "print(json.loads(urllib.request.urlopen(BASE + '/api/health').read().decode()))\n"
                "req = urllib.request.Request(BASE + '/api/auth/token?subject=demo&ttl=30', headers={'X-API-Key': API_KEY})\n"
                "token_data = json.loads(urllib.request.urlopen(req).read().decode())\n"
                "token = token_data['data']['token']\n"
                "req2 = urllib.request.Request(BASE + '/api/stats', headers={'Authorization': 'Bearer ' + token})\n"
                "print(json.loads(urllib.request.urlopen(req2).read().decode()))\n"
            )
        self._log_activity("Demo Kit Exported", out_dir)
        return out_dir

    def get_stats(self):
        with self._connect() as conn:
            users = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"] if self._table_exists(conn, "users") else 0
            faces = conn.execute("SELECT COUNT(*) c FROM face_events").fetchone()["c"] if self._table_exists(conn, "face_events") else 0
            activity = conn.execute("SELECT COUNT(*) c FROM activity_events").fetchone()["c"]
            attendance = conn.execute("SELECT COUNT(*) c FROM attendance_entries").fetchone()["c"] if self._table_exists(conn, "attendance_entries") else 0
            pending = conn.execute("SELECT COUNT(*) c FROM approval_requests WHERE status='pending'").fetchone()["c"] if self._table_exists(conn, "approval_requests") else 0
        db_size_mb = 0.0
        if os.path.exists(self.db_path):
            db_size_mb = round(os.path.getsize(self.db_path) / (1024 * 1024), 4)
        return {
            "users": users,
            "face_events": faces,
            "activity_events": activity,
            "attendance_entries": attendance,
            "pending_approvals": pending,
            "db_size_mb": db_size_mb,
            "api_host": self.host,
            "api_port": self.port,
            "backup_scheduler_running": self.is_scheduler_running(),
            "last_backup_at": self._last_backup_at,
        }

    def _table_exists(self, conn, table_name: str):
        row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)).fetchone()
        return bool(row)

    def list_users(self, limit: int = 200, requester_username: str = "", requester_role: str = "admin"):
        if limit < 1:
            limit = 1
        if limit > 2000:
            limit = 2000
        requester = (requester_username or "").strip().lower()
        role = (requester_role or "user").strip().lower()
        with self._connect() as conn:
            if not self._table_exists(conn, "users"):
                return []
            self._ensure_users_privacy_columns(conn)
            rows = conn.execute(
                "SELECT username, email, phone, role, created, privacy_mode, privacy_allowed_json, privacy_allowed_profile_json FROM users ORDER BY username LIMIT ?",
                (limit,),
            ).fetchall()
        out = []
        for row in rows:
            username = str(row["username"] or "")
            uname_l = username.lower()
            privacy_mode = self._normalize_privacy_mode(row["privacy_mode"])
            allowed = self._parse_allowed_usernames(row["privacy_allowed_profile_json"])
            if not allowed:
                allowed = self._parse_allowed_usernames(row["privacy_allowed_json"])

            if role != "admin" and requester != uname_l and privacy_mode == "private" and requester not in set(allowed):
                continue

            email = row["email"] or ""
            phone = row["phone"] or ""
            if role != "admin" and requester != uname_l:
                email = ""
                phone = ""

            out.append(
                {
                    "username": username,
                    "email": email,
                    "phone": phone,
                    "role": row["role"] or "user",
                    "created": row["created"] or "",
                    "privacy_mode": privacy_mode,
                    "private_profile_allowed": requester in set(allowed) if privacy_mode == "private" else True,
                }
            )
        return out

    def mobile_compare(self, left_image_b64: str, right_image_b64: str):
        from frontend import facercognition as legacy

        if not left_image_b64 or not right_image_b64:
            raise ValueError("left_image_b64 and right_image_b64 are required")

        left_frame = self._decode_image_b64(left_image_b64)
        right_frame = self._decode_image_b64(right_image_b64)

        left_det = self._legacy_detect_and_encode(legacy, left_frame)
        right_det = self._legacy_detect_and_encode(legacy, right_frame)
        if not left_det or not right_det:
            return {
                "ok": False,
                "message": "Face not detected in one or both images",
                "same_person": False,
                "similarity": 0.0,
            }

        _, _, _, _, left_emb = left_det[0]
        _, _, _, _, right_emb = right_det[0]
        similarity = legacy._sface_recognizer.match(
            left_emb.reshape(1, -1),
            right_emb.reshape(1, -1),
            cv2.FaceRecognizerSF_FR_COSINE,
        )
        threshold = float(getattr(legacy, "RECOGNITION_THRESHOLD", 0.36))
        similarity = float(similarity)
        return {
            "ok": True,
            "same_person": similarity >= threshold,
            "similarity": similarity,
            "threshold": threshold,
            "message": "Comparison complete",
        }

    def list_recent_activity(self, limit: int = 200):
        if limit < 1:
            limit = 1
        if limit > 5000:
            limit = 5000
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, event_time, username, role, action, detail FROM activity_events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def _log_activity(self, action: str, detail: str, username: str = "system", role: str = "service"):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = {
            "time": ts,
            "user": username,
            "role": role,
            "action": action,
            "detail": detail,
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO activity_events(event_time, username, role, action, detail, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (ts, username, role, action, detail, json.dumps(payload, ensure_ascii=False)),
            )
            conn.commit()

    def _create_backup(self):
        backup_dir = os.path.join(self.base_dir, "database", "artifacts", "backups")
        os.makedirs(backup_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"phase3_auto_backup_{stamp}.db")
        with sqlite3.connect(self.db_path, factory=AutoClosingConnection) as source:
            with sqlite3.connect(backup_path, factory=AutoClosingConnection) as dest:
                source.backup(dest)
        self._last_backup_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._log_activity("Auto Backup", f"Created backup at {backup_path}")
        return backup_path

    def start_backup_scheduler(self, interval_minutes: int = 1440):
        if interval_minutes < 1:
            interval_minutes = 1
        self._scheduler_interval_seconds = int(interval_minutes * 60)
        if self.is_scheduler_running():
            return
        self._scheduler_stop_event.clear()

        def worker():
            next_run = time.time() + self._scheduler_interval_seconds
            while not self._scheduler_stop_event.is_set():
                now = time.time()
                if now >= next_run:
                    try:
                        self._create_backup()
                    except Exception as e:
                        self._log_activity("Auto Backup Error", str(e))
                    next_run = now + self._scheduler_interval_seconds
                time.sleep(1)

        self._scheduler_thread = threading.Thread(target=worker, daemon=True)
        self._scheduler_thread.start()
        self._log_activity("Scheduler Started", f"Interval {interval_minutes} minutes")

    def stop_backup_scheduler(self):
        if not self._scheduler_thread:
            return
        self._scheduler_stop_event.set()
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=2)
        self._scheduler_thread = None
        self._log_activity("Scheduler Stopped", "Backup scheduler stopped")

    def is_scheduler_running(self):
        return bool(self._scheduler_thread and self._scheduler_thread.is_alive())

    def _make_handler(self):
        hub = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def _send_cors(self):
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

            def _send_json(self, code: int, payload: dict):
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self._send_cors()
                self.end_headers()
                self.wfile.write(body)

            def _send_html(self, code: int, html_text: str):
                body = html_text.encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self._send_cors()
                self.end_headers()
                self.wfile.write(body)

            def _read_json(self):
                length = int(self.headers.get("Content-Length", "0") or 0)
                if length <= 0:
                    return {}
                body = self.rfile.read(length)
                try:
                    return json.loads(body.decode("utf-8"))
                except Exception:
                    return {}

            def do_OPTIONS(self):
                self.send_response(204)
                self._send_cors()
                self.send_header("Content-Length", "0")
                self.end_headers()

            def _auth_ok(self):
                key = self.headers.get("X-API-Key", "")
                if key and key == hub.api_key:
                    return True
                auth_header = self.headers.get("Authorization", "")
                if auth_header.lower().startswith("bearer "):
                    token = auth_header[7:].strip()
                    return hub._validate_access_token(token)
                return False

            def _token_payload(self):
                auth_header = self.headers.get("Authorization", "")
                if not auth_header.lower().startswith("bearer "):
                    return None
                token = auth_header[7:].strip()
                return hub.decode_access_token(token)

            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                path = parsed.path
                query = urllib.parse.parse_qs(parsed.query)

                if path == "/api/health":
                    self._send_json(200, {"ok": True, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                    return

                if path == "/api/docs":
                    self._send_json(200, {"ok": True, "data": hub.get_api_docs()})
                    return

                if path == "/api/map/view":
                    try:
                        html_text = hub.get_world_map_html()
                        if not isinstance(html_text, str) or not html_text.strip():
                            html_text = (
                                "<!doctype html><html><head><meta charset='utf-8'><title>Map</title></head>"
                                "<body style='font-family:Arial,sans-serif;background:#0f1728;color:#e6eeff;padding:16px;'>"
                                "<h3>Map Ready</h3><p>Map content is temporarily unavailable.</p></body></html>"
                            )
                        self._send_html(200, html_text)
                    except Exception as e:
                        safe_error = str(e).replace("<", "(").replace(">", ")")
                        self._send_html(
                            200,
                            "<!doctype html><html><head><meta charset='utf-8'><title>Map Error</title></head>"
                            "<body style='font-family:Arial,sans-serif;background:#0f1728;color:#e6eeff;padding:16px;'>"
                            "<h3>Map Error</h3><p>" + safe_error + "</p></body></html>",
                        )
                    return

                if path == "/api/mobile/app-update":
                    self._send_json(200, {"ok": True, "data": hub.get_mobile_app_update_info()})
                    return

                if path == "/api/auth/token":
                    bootstrap_key = self.headers.get("X-API-Key", "")
                    if bootstrap_key != hub.api_key:
                        self._send_json(401, {"ok": False, "error": "Unauthorized for token issue"})
                        return
                    subject = query.get("subject", ["demo"])[0].strip() or "demo"
                    ttl = int(query.get("ttl", ["120"])[0])
                    token_data = hub.generate_access_token(subject=subject, ttl_minutes=ttl)
                    self._send_json(200, {"ok": True, "data": token_data})
                    return

                if path.startswith("/api/") and not self._auth_ok():
                    self._send_json(401, {"ok": False, "error": "Unauthorized"})
                    return

                if path == "/api/stats":
                    self._send_json(200, {"ok": True, "data": hub.get_stats()})
                    return

                if path == "/api/users":
                    limit = int(query.get("limit", ["200"])[0])
                    payload = self._token_payload() or {}
                    role = str(payload.get("role", "user")).strip().lower()
                    requester = str(payload.get("sub", "")).strip()
                    self._send_json(
                        200,
                        {
                            "ok": True,
                            "data": hub.list_users(
                                limit=limit,
                                requester_username=requester,
                                requester_role=role,
                            ),
                        },
                    )
                    return

                if path == "/api/users/me":
                    payload = self._token_payload()
                    if not payload:
                        self._send_json(401, {"ok": False, "error": "Unauthorized"})
                        return
                    profile = hub.get_user_profile(str(payload.get("sub", "")))
                    if not profile:
                        self._send_json(404, {"ok": False, "error": "User not found"})
                        return
                    self._send_json(200, {"ok": True, "data": profile})
                    return

                if path == "/api/activity":
                    limit = int(query.get("limit", ["200"])[0])
                    self._send_json(200, {"ok": True, "data": hub.list_recent_activity(limit=limit)})
                    return

                if path == "/api/db/overview":
                    self._send_json(200, {"ok": True, "data": hub.get_db_overview()})
                    return

                if path == "/api/system-info":
                    payload = self._token_payload() or {}
                    role = str(payload.get("role", "user")).strip().lower()
                    self._send_json(200, {"ok": True, "data": hub.get_system_info_summary(role=role)})
                    return

                if path == "/api/admin/advanced-lab":
                    self._send_json(200, {"ok": True, "data": hub.admin_advanced_lab_summary()})
                    return

                if path == "/api/admin/enterprise-control":
                    self._send_json(200, {"ok": True, "data": hub.admin_enterprise_control_summary()})
                    return

                if path == "/api/admin/evaluator-bundle":
                    self._send_json(200, {"ok": True, "data": hub.admin_evaluator_bundle_summary()})
                    return

                if path == "/api/admin/judge-mode":
                    self._send_json(200, {"ok": True, "data": hub.admin_judge_mode_summary()})
                    return

                if path == "/api/admin/demo-launcher":
                    self._send_json(200, {"ok": True, "data": hub.admin_demo_launcher_summary()})
                    return

                if path == "/api/admin/presentation-startup":
                    self._send_json(200, {"ok": True, "data": hub.admin_presentation_startup_summary()})
                    return

                if path == "/api/mobile/styles":
                    self._send_json(200, {"ok": True, "data": {"styles": hub.mobile_styles()}})
                    return

                if path == "/api/mobile/recognition-location/search":
                    name = query.get("name", [""])[0]
                    limit = int(query.get("limit", ["100"])[0])
                    requested_latest = query.get("latest_only", ["false"])[0].strip().lower() in (
                        "1",
                        "true",
                        "yes",
                    )
                    payload = self._token_payload() or {}
                    role = str(payload.get("role", "user")).strip().lower()
                    requester = str(payload.get("sub", "")).strip()
                    if not hub.can_user_access_person(
                        target_username=name,
                        requester_username=requester,
                        requester_role=role,
                        access_scope="map",
                    ):
                        self._send_json(403, {"ok": False, "error": "Private account is not accessible"})
                        return
                    latest_only = requested_latest or role != "admin"
                    rows = hub.search_recognition_locations(
                        name=name,
                        limit=limit,
                        latest_only=latest_only,
                    )
                    self._send_json(200, {"ok": True, "data": rows})
                    return

                if path == "/api/events/stream":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "keep-alive")
                    self.end_headers()
                    last_id = 0
                    try:
                        for _ in range(90):
                            with hub._connect() as conn:
                                rows = conn.execute(
                                    "SELECT id, event_time, username, role, action, detail FROM activity_events WHERE id>? ORDER BY id ASC LIMIT 100",
                                    (last_id,),
                                ).fetchall()
                            for r in rows:
                                last_id = r["id"]
                                payload = {
                                    "id": r["id"],
                                    "event_time": r["event_time"],
                                    "username": r["username"],
                                    "role": r["role"],
                                    "action": r["action"],
                                    "detail": r["detail"],
                                }
                                msg = f"data: {json.dumps(payload, ensure_ascii=False)}\\n\\n".encode("utf-8")
                                self.wfile.write(msg)
                            self.wfile.flush()
                            time.sleep(1)
                    except Exception:
                        return
                    return

                self._send_json(404, {"ok": False, "error": "Not found"})

            def do_POST(self):
                parsed = urllib.parse.urlparse(self.path)
                path = parsed.path

                if path.startswith("/api/") and path not in (
                    "/api/auth/login",
                    "/api/auth/signup",
                    "/api/auth/signup/request",
                    "/api/auth/signup/verify",
                    "/api/auth/password/request",
                    "/api/auth/password/reset",
                ) and not self._auth_ok():
                    self._send_json(401, {"ok": False, "error": "Unauthorized"})
                    return

                payload = self._read_json()

                try:
                    if path == "/api/auth/login":
                        identifier = str(payload.get("identifier", "")).strip()
                        password = str(payload.get("password", ""))
                        profile = hub.authenticate_user(identifier=identifier, password=password)
                        if not profile:
                            self._send_json(401, {"ok": False, "error": "Invalid credentials"})
                            return
                        token_data = hub.generate_access_token(
                            subject=str(profile.get("username", "")),
                            role=str(profile.get("role", "user")),
                            ttl_minutes=int(payload.get("ttl", 120)),
                        )
                        self._send_json(200, {"ok": True, "data": {"token": token_data["token"], "user": profile}})
                        return

                    if path == "/api/auth/signup":
                        username = str(payload.get("username", "")).strip()
                        email = str(payload.get("email", "")).strip()
                        phone = str(payload.get("phone", "")).strip()
                        password = str(payload.get("password", ""))
                        result = hub.register_user(username=username, email=email, phone=phone, password=password)
                        if result.get("ok") is not True:
                            self._send_json(400, result)
                            return
                        user_data = result.get("data", {})
                        token_data = hub.generate_access_token(
                            subject=str(user_data.get("username", "")),
                            role=str(user_data.get("role", "user")),
                            ttl_minutes=int(payload.get("ttl", 180)),
                        )
                        self._send_json(200, {"ok": True, "data": {"token": token_data["token"], "user": user_data}})
                        return

                    if path == "/api/auth/signup/request":
                        username = str(payload.get("username", "")).strip()
                        email = str(payload.get("email", "")).strip()
                        phone = str(payload.get("phone", "")).strip()
                        password = str(payload.get("password", ""))
                        result = hub.begin_signup_verification(
                            username=username,
                            email=email,
                            phone=phone,
                            password=password,
                        )
                        code = 200 if result.get("ok") is True else 400
                        self._send_json(code, result)
                        return

                    if path == "/api/auth/signup/verify":
                        email = str(payload.get("email", "")).strip()
                        code_in = str(payload.get("code", "")).strip()
                        result = hub.complete_signup_verification(email=email, code=code_in)
                        if result.get("ok") is not True:
                            self._send_json(400, result)
                            return
                        user_data = result.get("data", {})
                        token_data = hub.generate_access_token(
                            subject=str(user_data.get("username", "")),
                            role=str(user_data.get("role", "user")),
                            ttl_minutes=int(payload.get("ttl", 180)),
                        )
                        self._send_json(200, {"ok": True, "data": {"token": token_data["token"], "user": user_data}})
                        return

                    if path == "/api/auth/password/request":
                        identifier = str(payload.get("identifier", "")).strip()
                        result = hub.begin_password_reset(identifier=identifier)
                        code = 200 if result.get("ok") is True else 400
                        self._send_json(code, result)
                        return

                    if path == "/api/auth/password/reset":
                        username = str(payload.get("username", "")).strip()
                        code_in = str(payload.get("code", "")).strip()
                        new_password = str(payload.get("new_password", ""))
                        result = hub.reset_password_with_code(
                            username=username,
                            code=code_in,
                            new_password=new_password,
                        )
                        code = 200 if result.get("ok") is True else 400
                        self._send_json(code, result)
                        return

                    if path == "/api/mobile/identify":
                        image_b64 = str(payload.get("image_b64", ""))
                        top_k = int(payload.get("top_k", 3))
                        tracking = payload.get("tracking") if isinstance(payload.get("tracking"), dict) else None
                        try:
                            data = hub.mobile_identify(image_b64=image_b64, top_k=top_k, tracking=tracking)
                            self._send_json(200, {"ok": True, "data": data})
                        except Exception as e:
                            fallback = {
                                "detected": False,
                                "message": f"Identify failed: {e}",
                                "face_count": 0,
                                "faces": [],
                                "image_width": 0,
                                "image_height": 0,
                                "best": {"name": "Unknown", "score": 0.0},
                                "matches": [],
                            }
                            self._send_json(200, {"ok": False, "error": "identify_failed", "data": fallback})
                        return

                    if path == "/api/mobile/generate":
                        image_b64 = str(payload.get("image_b64", ""))
                        filter_name = str(payload.get("filter_name", ""))
                        data = hub.mobile_generate(image_b64=image_b64, filter_name=filter_name)
                        self._send_json(200, {"ok": True, "data": data})
                        return

                    if path == "/api/mobile/compare":
                        left_image_b64 = str(payload.get("left_image_b64", ""))
                        right_image_b64 = str(payload.get("right_image_b64", ""))
                        data = hub.mobile_compare(
                            left_image_b64=left_image_b64,
                            right_image_b64=right_image_b64,
                        )
                        self._send_json(200, {"ok": True, "data": data})
                        return

                    if path == "/api/mobile/recognition-location/save":
                        result = hub.save_recognition_location_event(
                            recognized_name=str(payload.get("recognized_name", "")).strip(),
                            location_name=str(payload.get("location_name", "")).strip(),
                            latitude=payload.get("latitude"),
                            longitude=payload.get("longitude"),
                            confidence=payload.get("confidence"),
                            source=str(payload.get("source", "mobile_manual")).strip() or "mobile_manual",
                            requested_by=str(payload.get("requested_by", "mobile")).strip() or "mobile",
                            force_update=bool(payload.get("force_update", False)),
                        )
                        code = 200 if result.get("ok") is True else 400
                        self._send_json(code, result)
                        return

                    if path == "/api/users/me/privacy":
                        token_payload = self._token_payload() or {}
                        actor = str(token_payload.get("sub", "")).strip()
                        role = str(token_payload.get("role", "user")).strip().lower()
                        mode = str(payload.get("privacy_mode", "public")).strip()
                        allowed = payload.get("privacy_allowed", [])
                        allowed_map = payload.get("privacy_allowed_map", [])
                        allowed_profile = payload.get("privacy_allowed_profile", [])
                        result = hub.update_user_privacy(
                            target_username=actor,
                            privacy_mode=mode,
                            allowed_usernames=allowed,
                            allowed_map_usernames=allowed_map,
                            allowed_profile_usernames=allowed_profile,
                            actor_username=actor,
                            actor_role=role,
                        )
                        code = 200 if result.get("ok") is True else 400
                        self._send_json(code, result)
                        return

                    if path == "/api/admin/evaluator-bundle/export":
                        out_dir = hub.export_demo_kit()
                        self._send_json(200, {"ok": True, "data": {"out_dir": out_dir}})
                        return

                    if path == "/api/admin/backup/now":
                        backup_path = hub._create_backup()
                        self._send_json(200, {"ok": True, "data": {"backup_path": backup_path}})
                        return

                    if path == "/api/admin/scheduler/start":
                        interval = int(payload.get("interval_minutes", 1440))
                        hub.start_backup_scheduler(interval_minutes=interval)
                        self._send_json(200, {"ok": True, "data": {"running": hub.is_scheduler_running(), "interval_minutes": interval}})
                        return

                    if path == "/api/admin/scheduler/stop":
                        hub.stop_backup_scheduler()
                        self._send_json(200, {"ok": True, "data": {"running": hub.is_scheduler_running()}})
                        return

                    if path == "/api/admin/faces/sync":
                        entries = payload.get("entries")
                        clear_existing = bool(payload.get("clear_existing", False))
                        refresh_after = bool(payload.get("refresh_after", False))
                        result = hub.sync_known_faces(
                            entries=entries,
                            clear_existing=clear_existing,
                            refresh_after=refresh_after,
                        )
                        self._send_json(200, result)
                        return
                except ValueError as e:
                    self._send_json(400, {"ok": False, "error": str(e)})
                    return
                except Exception as e:
                    hub._log_activity("Mobile API Error", f"{path}: {e}")
                    self._send_json(500, {"ok": False, "error": "Internal error", "detail": str(e)})
                    return

                self._send_json(404, {"ok": False, "error": "Not found"})

            def log_message(self, fmt, *args):
                return

        return Handler

    def start_api_server(self):
        if self._api_thread and self._api_thread.is_alive():
            return
        handler = self._make_handler()
        self._api_server = ThreadingHTTPServer((self.host, self.port), handler)

        def run_server():
            self._log_activity("API Started", f"http://{self.host}:{self.port}")
            try:
                self._api_server.serve_forever(poll_interval=0.5)
            finally:
                self._log_activity("API Stopped", "Server stopped")

        self._api_thread = threading.Thread(target=run_server, daemon=True)
        self._api_thread.start()

    def stop_api_server(self):
        if self._api_server:
            try:
                self._api_server.shutdown()
                self._api_server.server_close()
            except Exception:
                pass
            self._api_server = None
        self._api_thread = None

    def start_all_services(self):
        self.start_api_server()
        self.start_backup_scheduler(interval_minutes=1440)

    def stop_all_services(self):
        self.stop_backup_scheduler()
        self.stop_api_server()



def launch_phase3_services_gui(base_dir: str, db_path: str, parent=None, on_close_callback=None):
    if tk is None or ttk is None or filedialog is None or messagebox is None:
        raise RuntimeError("Tkinter GUI is unavailable in this environment. Use API mode for server deployments.")

    hub = Phase3ServiceHub(base_dir, db_path)

    if parent is None:
        win = tk.Tk()
        standalone = True
    else:
        win = tk.Toplevel(parent)
        standalone = False

    win.title("Services Hub")
    win.geometry("1120x760")
    win.configure(bg="#121733")

    tk.Label(win, text="Services Hub", font=("Segoe UI", 24, "bold"), fg="#ff6f91", bg="#121733").pack(anchor="w", padx=14, pady=(12, 2))
    tk.Label(win, text="Secure API, live stream, and auto backup scheduler", font=("Segoe UI", 11), fg="#9cb3ff", bg="#121733").pack(anchor="w", padx=14)

    status_var = tk.StringVar(value="Ready")
    api_state_var = tk.StringVar(value="Stopped")
    scheduler_state_var = tk.StringVar(value="Stopped")
    api_url_var = tk.StringVar(value=f"http://{hub.host}:{hub.port}")
    key_preview_var = tk.StringVar(value=hub.api_key[:16] + "...")
    backup_var = tk.StringVar(value="-")
    traffic_summary_var = tk.StringVar(value="Last 10 min total: 0 | Peak: -")

    cards_frame = tk.Frame(win, bg="#121733")
    cards_frame.pack(fill="x", padx=14, pady=(10, 8))

    card_vars = {
        "users": tk.StringVar(value="0"),
        "activity_events": tk.StringVar(value="0"),
        "pending_approvals": tk.StringVar(value="0"),
        "db_size_mb": tk.StringVar(value="0"),
    }
    card_defs = [
        ("Users", "users"),
        ("Activity Events", "activity_events"),
        ("Pending Approvals", "pending_approvals"),
        ("DB Size (MB)", "db_size_mb"),
    ]
    for idx, (title, key) in enumerate(card_defs):
        card = tk.Frame(cards_frame, bg="#0d1230", bd=1, relief="solid", highlightbackground="#2d3f80", highlightthickness=1)
        card.grid(row=0, column=idx, sticky="nsew", padx=5)
        tk.Label(card, text=title, font=("Segoe UI", 9, "bold"), fg="#9cb3ff", bg="#0d1230").pack(anchor="w", padx=8, pady=(6, 2))
        tk.Label(card, textvariable=card_vars[key], font=("Segoe UI", 16, "bold"), fg="#f5f7ff", bg="#0d1230").pack(anchor="w", padx=8, pady=(0, 8))
    for idx in range(4):
        cards_frame.grid_columnconfigure(idx, weight=1)

    summary_row = tk.Frame(win, bg="#121733")
    summary_row.pack(fill="x", padx=14, pady=(0, 8))
    lower_summary_row = tk.Frame(win, bg="#121733")
    lower_summary_row.pack(fill="x", padx=14, pady=(0, 8))

    runtime_card = tk.LabelFrame(summary_row, text="Runtime", font=("Segoe UI", 10, "bold"), fg="#cfdcff", bg="#121733")
    runtime_card.pack(side="left", fill="both", expand=True, padx=(0, 6))
    auth_card = tk.LabelFrame(summary_row, text="Security", font=("Segoe UI", 10, "bold"), fg="#cfdcff", bg="#121733")
    auth_card.pack(side="left", fill="both", expand=True, padx=(6, 6))
    endpoint_card = tk.LabelFrame(lower_summary_row, text="Endpoints", font=("Segoe UI", 10, "bold"), fg="#cfdcff", bg="#121733")
    endpoint_card.pack(side="left", fill="both", expand=True, padx=(0, 6))
    traffic_card = tk.LabelFrame(lower_summary_row, text="Traffic (Last 10 Minutes)", font=("Segoe UI", 10, "bold"), fg="#cfdcff", bg="#121733")
    traffic_card.pack(side="left", fill="both", expand=True, padx=(6, 0))

    tk.Label(runtime_card, text="API URL", fg="#9cb3ff", bg="#121733", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=8, pady=(6, 2))
    tk.Label(runtime_card, textvariable=api_url_var, fg="#e6edff", bg="#121733", font=("Consolas", 9)).grid(row=0, column=1, sticky="w", padx=8, pady=(6, 2))
    tk.Label(runtime_card, text="API", fg="#9cb3ff", bg="#121733", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", padx=8, pady=2)
    api_state_label = tk.Label(
        runtime_card,
        textvariable=api_state_var,
        fg="#f7fafc",
        bg="#8b1e2f",
        font=("Segoe UI", 8, "bold"),
        padx=8,
        pady=2,
        relief="ridge",
        bd=1,
    )
    api_state_label.grid(row=1, column=1, sticky="w", padx=8, pady=2)
    tk.Label(runtime_card, text="Scheduler", fg="#9cb3ff", bg="#121733", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", padx=8, pady=2)
    scheduler_state_label = tk.Label(
        runtime_card,
        textvariable=scheduler_state_var,
        fg="#f7fafc",
        bg="#8b1e2f",
        font=("Segoe UI", 8, "bold"),
        padx=8,
        pady=2,
        relief="ridge",
        bd=1,
    )
    scheduler_state_label.grid(row=2, column=1, sticky="w", padx=8, pady=2)
    tk.Label(runtime_card, text="Last Backup", fg="#9cb3ff", bg="#121733", font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky="w", padx=8, pady=(2, 8))
    tk.Label(runtime_card, textvariable=backup_var, fg="#e6edff", bg="#121733", font=("Consolas", 9)).grid(row=3, column=1, sticky="w", padx=8, pady=(2, 8))

    tk.Label(auth_card, text="API Key Preview", fg="#9cb3ff", bg="#121733", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(6, 2))
    tk.Label(auth_card, textvariable=key_preview_var, fg="#e6edff", bg="#121733", font=("Consolas", 9)).pack(anchor="w", padx=8, pady=(0, 6))
    tk.Label(
        auth_card,
        text="Use X-API-Key only for token issue.\nUse Bearer token for secure APIs.",
        justify="left",
        fg="#b8c8ef",
        bg="#121733",
        font=("Segoe UI", 9),
    ).pack(anchor="w", padx=8, pady=(0, 8))

    endpoint_tree = ttk.Treeview(endpoint_card, columns=("path", "auth"), show="headings", height=5)
    endpoint_tree.heading("path", text="Path")
    endpoint_tree.heading("auth", text="Auth")
    endpoint_tree.column("path", width=220, anchor="w")
    endpoint_tree.column("auth", width=110, anchor="center")
    endpoint_tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
    endpoint_scroll = ttk.Scrollbar(endpoint_card, orient="vertical", command=endpoint_tree.yview)
    endpoint_scroll.pack(side="right", fill="y", padx=(6, 8), pady=8)
    endpoint_tree.configure(yscrollcommand=endpoint_scroll.set)

    traffic_tree = ttk.Treeview(traffic_card, columns=("minute", "count", "trend"), show="headings", height=5)
    traffic_tree.heading("minute", text="Minute")
    traffic_tree.heading("count", text="Events")
    traffic_tree.heading("trend", text="Trend")
    traffic_tree.column("minute", width=150, anchor="center")
    traffic_tree.column("count", width=100, anchor="center")
    traffic_tree.column("trend", width=90, anchor="center")
    traffic_tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
    traffic_scroll = ttk.Scrollbar(traffic_card, orient="vertical", command=traffic_tree.yview)
    traffic_scroll.pack(side="right", fill="y", padx=(6, 8), pady=8)
    traffic_tree.configure(yscrollcommand=traffic_scroll.set)
    tk.Label(traffic_card, textvariable=traffic_summary_var, fg="#a9bdf0", bg="#121733", font=("Segoe UI", 9)).pack(anchor="w", padx=8, pady=(0, 8))

    info_frame = tk.LabelFrame(win, text="Live Service Console", font=("Segoe UI", 10, "bold"), fg="#cfdcff", bg="#121733")
    info_frame.pack(fill="both", expand=True, padx=14, pady=12)
    info = tk.Text(info_frame, bg="#0d1230", fg="#d7e2ff", font=("Consolas", 10), height=20)
    info.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
    info_scroll = ttk.Scrollbar(info_frame, orient="vertical", command=info.yview)
    info_scroll.pack(side="right", fill="y", padx=(6, 8), pady=8)
    info.configure(yscrollcommand=info_scroll.set)

    controls = tk.LabelFrame(win, text="Controls", font=("Segoe UI", 10, "bold"), fg="#cfdcff", bg="#121733")
    controls.pack(fill="x", padx=14, pady=(0, 10))
    controls_row1 = tk.Frame(controls, bg="#121733")
    controls_row1.pack(fill="x", padx=8, pady=(8, 2))
    controls_row2 = tk.Frame(controls, bg="#121733")
    controls_row2.pack(fill="x", padx=8, pady=(2, 8))
    button_style = {"font": ("Segoe UI", 9, "bold"), "padx": 10, "pady": 4}

    host_var = tk.StringVar(value=hub.host)
    port_var = tk.StringVar(value=str(hub.port))

    tk.Label(controls_row1, text="Host", fg="#d7e2ff", bg="#121733").pack(side="left", padx=4)
    tk.Entry(controls_row1, textvariable=host_var, width=14).pack(side="left", padx=4)
    tk.Label(controls_row1, text="Port", fg="#d7e2ff", bg="#121733").pack(side="left", padx=4)
    tk.Entry(controls_row1, textvariable=port_var, width=8).pack(side="left", padx=4)

    def refresh():
        info.delete("1.0", "end")
        stats = hub.get_stats()
        for key in card_vars:
            card_vars[key].set(str(stats.get(key, 0)))
        api_url_var.set(f"http://{hub.host}:{hub.port}")
        key_preview_var.set((hub.api_key or "")[:16] + "...")
        api_running = bool(hub._api_thread and hub._api_thread.is_alive())
        sched_running = hub.is_scheduler_running()
        api_state_var.set("Running" if api_running else "Stopped")
        scheduler_state_var.set("Running" if sched_running else "Stopped")
        api_state_label.configure(bg="#1f7a4d" if api_running else "#8b1e2f")
        scheduler_state_label.configure(bg="#1f7a4d" if sched_running else "#8b1e2f")
        backup_var.set(hub._last_backup_at or "-")

        for item in endpoint_tree.get_children():
            endpoint_tree.delete(item)
        endpoints = [
            ("/api/health", "Public"),
            ("/api/docs", "Public"),
            ("/api/auth/token", "X-API-Key"),
            ("/api/stats", "Bearer"),
            ("/api/users", "Bearer"),
            ("/api/activity", "Bearer"),
            ("/api/events/stream", "Bearer"),
        ]
        for path, auth in endpoints:
            endpoint_tree.insert("", "end", values=(path, auth))

        for item in traffic_tree.get_children():
            traffic_tree.delete(item)
        minute_counts = {}
        with hub._connect() as conn:
            rows = conn.execute("SELECT event_time FROM activity_events ORDER BY id DESC LIMIT 1200").fetchall()
        now = datetime.now()
        for row in rows:
            ts = row["event_time"]
            if not ts:
                continue
            try:
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            delta = (now - dt).total_seconds()
            if delta < 0 or delta > 600:
                continue
            key = dt.strftime("%H:%M")
            minute_counts[key] = minute_counts.get(key, 0) + 1
        ordered_counts = []
        ordered_minutes = []
        for i in range(9, -1, -1):
            minute_key = (now - timedelta(minutes=i)).strftime("%H:%M")
            ordered_minutes.append(minute_key)
            ordered_counts.append(minute_counts.get(minute_key, 0))

        peak_count = max(ordered_counts) if ordered_counts else 0
        peak_idx = ordered_counts.index(peak_count) if ordered_counts else -1
        peak_minute = ordered_minutes[peak_idx] if peak_idx >= 0 else "-"
        traffic_summary_var.set(f"Last 10 min total: {sum(ordered_counts)} | Peak: {peak_minute} ({peak_count})")

        prev_count = None
        for minute_key, count in zip(ordered_minutes, ordered_counts):
            if prev_count is None:
                trend = "-"
            elif count > prev_count:
                trend = "UP"
            elif count < prev_count:
                trend = "DOWN"
            else:
                trend = "FLAT"
            traffic_tree.insert("", "end", values=(minute_key, count, trend))
            prev_count = count

        info.insert("end", "Service Status\n")
        info.insert("end", "==========================\n")
        info.insert("end", f"API URL: http://{hub.host}:{hub.port}\n")
        info.insert("end", f"API Key: {hub.api_key}\n")
        info.insert("end", f"Token Secret: {hub.token_secret[:10]}...\n")
        info.insert("end", f"Scheduler running: {hub.is_scheduler_running()}\n")
        info.insert("end", f"Last backup: {hub._last_backup_at}\n\n")
        info.insert("end", "Project Stats\n")
        info.insert("end", "==========================\n")
        for k, v in stats.items():
            info.insert("end", f"{k}: {v}\n")
        info.insert("end", "\nAPI Endpoints\n")
        info.insert("end", "==========================\n")
        info.insert("end", "/api/health\n")
        info.insert("end", "/api/docs\n")
        info.insert("end", "/api/auth/token?subject=demo&ttl=120  (X-API-Key required)\n")
        info.insert("end", "/api/stats\n")
        info.insert("end", "/api/users?limit=200\n")
        info.insert("end", "/api/activity?limit=200\n")
        info.insert("end", "/api/events/stream\n")

    def apply_host_port():
        hub.host = host_var.get().strip() or "127.0.0.1"
        try:
            hub.port = int(port_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid", "Port must be integer", parent=win)
            return False
        return True

    def start_api():
        if not apply_host_port():
            return
        hub.start_api_server()
        status_var.set("API started")
        refresh()

    def stop_api():
        hub.stop_api_server()
        status_var.set("API stopped")
        refresh()

    def start_scheduler():
        hub.start_backup_scheduler(interval_minutes=1440)
        status_var.set("Scheduler started")
        refresh()

    def stop_scheduler():
        hub.stop_backup_scheduler()
        status_var.set("Scheduler stopped")
        refresh()

    def backup_now():
        path = hub._create_backup()
        status_var.set(f"Backup created: {path}")
        refresh()

    def save_key_to_file():
        path = filedialog.asksaveasfilename(
            title="Save API key",
            defaultextension=".txt",
            filetypes=[("Text", "*.txt")],
            initialfile="phase3_api_key.txt",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(hub.api_key)
        status_var.set("API key saved")

    def rotate_key():
        hub.rotate_api_key()
        status_var.set("API key rotated")
        refresh()

    def generate_token():
        data = hub.generate_access_token(subject="gui-demo", ttl_minutes=120)
        token = data["token"]
        info.insert("end", "\nGenerated Token\n")
        info.insert("end", "==========================\n")
        info.insert("end", f"subject: {data['subject']}\n")
        info.insert("end", f"expires_at: {data['expires_at']}\n")
        info.insert("end", f"token: {token}\n")
        status_var.set("Bearer token generated")

    def export_demo_kit():
        out = hub.export_demo_kit()
        status_var.set(f"Demo kit exported: {out}")
        refresh()

    def save_docs_to_file():
        path = filedialog.asksaveasfilename(
            title="Save API docs",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="phase4_api_docs.json",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(hub.get_api_docs(), f, ensure_ascii=False, indent=2)
        status_var.set("API docs saved")

    tk.Label(controls_row1, text="Service Runtime", fg="#9cb3ff", bg="#121733", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 8))
    tk.Button(controls_row1, text="Start API", command=start_api, bg="#3050d3", fg="white", width=13, **button_style).pack(side="left", padx=4)
    tk.Button(controls_row1, text="Stop API", command=stop_api, bg="#7a3cb0", fg="white", width=13, **button_style).pack(side="left", padx=4)
    tk.Button(controls_row1, text="Start Scheduler", command=start_scheduler, bg="#0f8c62", fg="white", width=13, **button_style).pack(side="left", padx=4)
    tk.Button(controls_row1, text="Stop Scheduler", command=stop_scheduler, bg="#b03a2e", fg="white", width=13, **button_style).pack(side="left", padx=4)
    tk.Button(controls_row1, text="Backup Now", command=backup_now, bg="#1f6cab", fg="white", width=13, **button_style).pack(side="left", padx=4)

    tk.Label(controls_row2, text="Security / Exports", fg="#9cb3ff", bg="#121733", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 8))
    tk.Button(controls_row2, text="Save API Key", command=save_key_to_file, bg="#0e6655", fg="white", width=13, **button_style).pack(side="left", padx=4)
    tk.Button(controls_row2, text="Rotate API Key", command=rotate_key, bg="#7d6608", fg="white", width=13, **button_style).pack(side="left", padx=4)
    tk.Button(controls_row2, text="Generate Token", command=generate_token, bg="#2e4053", fg="white", width=13, **button_style).pack(side="left", padx=4)
    tk.Button(controls_row2, text="Export Demo Kit", command=export_demo_kit, bg="#7b241c", fg="white", width=13, **button_style).pack(side="left", padx=4)
    tk.Button(controls_row2, text="Save API Docs", command=save_docs_to_file, bg="#512e5f", fg="white", width=13, **button_style).pack(side="left", padx=4)
    tk.Button(controls_row2, text="Refresh", command=refresh, bg="#444", fg="white", width=13, **button_style).pack(side="left", padx=4)

    tk.Label(win, textvariable=status_var, font=("Segoe UI", 10), fg="#7ad0ff", bg="#121733").pack(anchor="w", padx=14, pady=(0, 10))

    refresh()

    auto_refresh_state = {"enabled": True}

    def periodic_refresh():
        if not auto_refresh_state["enabled"]:
            return
        try:
            refresh()
        except Exception:
            pass
        win.after(15000, periodic_refresh)

    win.after(15000, periodic_refresh)

    def on_close():
        auto_refresh_state["enabled"] = False
        hub.stop_all_services()
        win.destroy()
        if on_close_callback:
            on_close_callback()

    win.protocol("WM_DELETE_WINDOW", on_close)
    if standalone:
        win.mainloop()



def run_phase3_cli(base_dir: str, db_path: str, command: str, host: str = "127.0.0.1", port: int = 8787):
    hub = Phase3ServiceHub(base_dir, db_path, host=host, port=port)
    if command == "showapikey":
        print(hub.api_key)
        return
    if command == "rotapikey":
        print(hub.rotate_api_key())
        return
    if command == "gentoken":
        print(json.dumps(hub.generate_access_token(subject="cli-demo", ttl_minutes=120), indent=2))
        return
    if command == "apidocs":
        print(json.dumps(hub.get_api_docs(), indent=2))
        return
    if command == "demokit":
        print(hub.export_demo_kit())
        return
    if command == "snapshot":
        print(json.dumps(hub.get_stats(), indent=2))
        return
    if command == "startapi":
        hub.start_api_server()
        print(f"API started at http://{hub.host}:{hub.port}")
        print(f"X-API-Key: {hub.api_key}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            hub.stop_api_server()
            print("API stopped")
        return
    if command == "startservices":
        hub.start_all_services()
        print(f"Services started at http://{hub.host}:{hub.port}")
        print(f"X-API-Key: {hub.api_key}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            hub.stop_all_services()
            print("Services stopped")
        return
    print(json.dumps(hub.get_stats(), indent=2))
