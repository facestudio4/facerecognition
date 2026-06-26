# Security-First Vibe Coding Rules

Every change in this project must follow these rules, no exceptions. When in
doubt, err on the side of security over convenience.

> Stack note: this project is a **Python `http.server` backend** (no Express/
> FastAPI) + a **Flutter** mobile client + **SQLite** + **Supabase Storage** +
> **Render** hosting. JS-specific advice below maps to the Python/Flutter
> equivalent (e.g. `zod` → manual/`pydantic`-style validation, `helmet` →
> manual security headers, `bcrypt` → `hashlib.pbkdf2_hmac`).

## 1. Secrets & environment variables
- All API keys, tokens, DB URLs and credentials live in env vars / `.env` only.
- `.env`, `.env.local`, `.env.*.local`, `config/secrets/` are git-ignored.
  Templates (`.env.render.example`, `config/.env.example`) are committed.
- No raw secret literals in client code. The Flutter app reads
  `FACE_STUDIO_API_KEY` via `--dart-define` (empty default) — never hardcode it.
- Backend secrets are read from env first: `FACESTUDIO_API_KEY`,
  `FACESTUDIO_TOKEN_SECRET` (fall back to the DB only for local dev).

## 2. Rate limiting
- Per-IP limiting in `Phase3ServiceHub._rate_limit_check`, applied in `do_POST`.
  Auth endpoints: `FACESTUDIO_RL_AUTH_MAX` (default 15) / 15 min. Other API:
  `FACESTUDIO_RL_API_MAX` (default 300) / min. Returns `429` + `Retry-After`.
- Keep general limits high enough not to break live recognition / gallery scan.

## 3. Input validation & sanitization
- Validate on the server. Face/person names go through `_sanitize_face_name`
  (allowlist `[A-Za-z0-9 _-]`, blocks path traversal); filenames via
  `os.path.basename`. Request bodies are capped (`_MAX_BODY_BYTES`, 16 MB).
- All SQL uses `?` parameterization — never f-string/format/% with user input.

## 4. Authentication & authorization
- Passwords: `hashlib.pbkdf2_hmac("sha256", ...)` with a unique per-user salt and
  200k iterations (`_hash_password`). Legacy static-salt SHA-256 hashes still
  verify and are upgraded on next login. NO plaintext fallback.
- Tokens: HMAC-SHA256 signed with `token_secret`, short TTL, expiry checked.
- Admin/sensitive routes check role (`_token_payload` / actor_role).
- (Future) add account lockout; rate limiting on auth is the current mitigation.

## 5. SQL & database security
- SQLite via parameterized queries. Don't return raw DB errors to the client.

## 6. CORS
- No wildcard in production. `_send_cors` echoes an Origin only if it is in
  `FACESTUDIO_ALLOWED_ORIGINS` (comma list). Empty default = no ACAO header
  (native mobile clients send no Origin and are unaffected).

## 7. HTTP security headers
- `_send_security_headers` sets `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy`, `Strict-Transport-Security`.
  JSON responses get a strict CSP (`default-src 'none'`); the map HTML page gets
  a relaxed CSP so leaflet works. Server version string is suppressed.

## 8. File upload security
- Only small face crops are accepted (never whole photos/videos). Validate size,
  sanitize the person folder, basename the filename, write under the faces root
  (not web root). Prefer timestamp/UUID names.

## 9. Error handling & logging
- Never leak stack traces / internals to the client in production. Generic
  `"Internal error"` to the client; detail only when `FACESTUDIO_DEBUG=1`.
  Log server-side via `_log_activity`.

## 10. Dependency security
- Pin versions in `config/requirements.txt`. Review before bumping; prefer
  versions with prebuilt cp311 wheels (free-tier memory is tight).

## 11. XSS / CSP
- Flutter client has no `innerHTML`/`eval`. The only server HTML is the leaflet
  map; user-derived strings are escaped before embedding.

## 12. Deployment checklist (before every ship)
- [ ] No real `.env` committed; secrets set in Render env config.
- [ ] `FACESTUDIO_DEBUG` unset/false in production.
- [ ] HTTPS enforced (Render terminates TLS; clients use `https://`).
- [ ] Rate limiting active; CORS restricted (set `FACESTUDIO_ALLOWED_ORIGINS`).
- [ ] Supabase service key & backend secrets rotated if ever exposed.

## 13. AI / LLM
- Recognition uses local CV models (YuNet + SFace) — no LLM, no prompt-injection
  surface there.
- Image generation (`/api/mobile/generate` → `backend/services/hf_image_gen.py`)
  calls the **Hugging Face Inference API** for text→image / img2img. Keep the key
  server-side only (`HF_API_TOKEN` env, never in the client). The user prompt is
  capped by `_MAX_BODY_BYTES`; output is an image (no code/HTML execution). If a
  text LLM is ever added: key server-side, set `max_tokens`, sanitize I/O.

---

## Known accepted risks (require user action — see audit)
- `database/facestudio.db`, `database/face_encodings.pkl`, `database/faces/**`
  are committed as the Render free-tier **seed**. The DB still contains the
  backend `api_key`/`token_secret` and biometric data in git history. Mitigation:
  set `FACESTUDIO_API_KEY` / `FACESTUDIO_TOKEN_SECRET` as Render env vars (now
  supported), rotate them, and treat the committed DB as non-secret seed data.
- The Supabase `service_role` key was shared in chat → rotate it in Supabase →
  Settings → API and update the Render env var.
