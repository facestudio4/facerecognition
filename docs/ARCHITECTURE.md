# FaceRecognitionStudio Folder Architecture

## Top-level Structure

- frontend/: Desktop UI launchers and UI entry modules.
- backend/: Business logic, orchestration, and service wrappers.
- database/: SQLite connection layer and future repositories.
- api/: API start points and external interface modules.
- config/: Environment-based settings and app configuration.
- scripts/: Windows scripts for common run commands.
- docs/: Design and architecture documentation.

Unit tests are organized under backend/tests/.

## Current Code Layout

- frontend/facercognition.py: Main legacy-compatible UI and command entry file.
- frontend/kivy_laptop_app.py: Kivy launcher UI.
- backend/phase*_pack.py and backend/advanced_project_pack.py: Feature modules and services.
- database/faces/: Person folders and known_faces dataset.
- database/artifacts/: Generated bundles, backups, manifests, and reports.

## New Unified Entry Point

Use scripts/app_runner.py instead of calling many different scripts directly.

Examples:

- python scripts/app_runner.py gui
- python scripts/app_runner.py kivy
- python scripts/app_runner.py api
- python scripts/app_runner.py services
- python scripts/app_runner.py showcase
- python scripts/app_runner.py bundle
- python scripts/app_runner.py judge
- python scripts/app_runner.py demo
- python scripts/app_runner.py presentation

## Migration Plan

1. Continue splitting frontend/facercognition.py into smaller frontend and backend modules.
2. Move direct sqlite3 and JSON operations into database repositories.
3. Keep all generated outputs under database/artifacts or docs.
4. Standardize launcher scripts under scripts/ only.
5. Expand backend/tests for all moved modules.
