# Face Studio

Face‑recognition + social mobile app: a Python `http.server` backend (on Render),
a Flutter Android client, SQLite + Supabase Storage for persistence, Firebase Cloud
Messaging for push, and JaaS (8x8) for sign‑in‑free video/voice calls.

## Repository layout

| Path | What's inside |
|------|---------------|
| `api/` | HTTP API entrypoint (`http_api.py`) |
| `backend/` | Core services — recognition, gallery scan, social, push, calls (`phase3_services_pack.py` + tests) |
| `frontend/` | Desktop UI (Kivy / Tkinter) |
| `mobile_flutter_client/` | Flutter Android app (the shipped client) |
| `scripts/` | Run helpers, dev tools, and `app_runner.py` (the real entrypoint) |
| `config/` | `requirements.txt`, settings, env templates |
| `database/` | SQLite DB, encodings, and enrolled faces (Render free‑tier seed) |
| `docs/` | Architecture, deploy, and run guides |
| `assets/` | Brand images / logo |
| `archive/` | Superseded prototypes — not used by the app (see `archive/README.md`) |
| `secrets/` | Local‑only keys (git‑ignored, never committed) |

## Running

```bash
pip install -r config/requirements.txt
python scripts/app_runner.py api --host 0.0.0.0 --port 8787
```

See [docs/RUN_COMMANDS.md](docs/RUN_COMMANDS.md) for all commands,
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design, and
[docs/render_deploy.md](docs/render_deploy.md) for deployment.

## Security

Secrets live only in environment variables / the git‑ignored `secrets/` folder.
See [CLAUDE.md](CLAUDE.md) for the project's security rules.
