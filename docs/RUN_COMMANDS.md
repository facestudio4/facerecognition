# Run Commands

This file is the quick command index for local development, previews, and builds.
All commands are run from the repository root unless stated otherwise.

## Backend API (local)

```powershell
python scripts/app_runner.py api --host 0.0.0.0 --port 8787
```

Shortcut:

```bat
scripts\start_api.bat
```

Health check:

```powershell
curl http://127.0.0.1:8787/api/health
```

## Desktop GUI (Kivy)

```powershell
python scripts/app_runner.py gui
```

Shortcuts:

```bat
scripts\start_app.bat
scripts\run_kivy_launcher.bat
```

## Mobile (Flutter) dev on device

One-command helper (starts backend + runs Flutter on an Android device):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_mobile_dev.ps1
```

Useful flags:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_mobile_dev.ps1 -ApiHost 0.0.0.0 -Port 8787
powershell -ExecutionPolicy Bypass -File scripts\start_mobile_dev.ps1 -BaseUrl http://192.168.1.20:8787
powershell -ExecutionPolicy Bypass -File scripts\start_mobile_dev.ps1 -SkipBackend
```

Batch shortcut:

```bat
scripts\start_mobile_dev.bat
```

Manual Flutter run (from mobile_flutter_client):

```powershell
cd mobile_flutter_client
flutter pub get
flutter run
```

If Flutter is not in PATH:

```powershell
cd mobile_flutter_client
./flutterw.ps1 pub get
./flutterw.ps1 run
```

## Mobile preview (Windows or Web)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_mobile_preview.ps1
```

Common options:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_mobile_preview.ps1 -Web
powershell -ExecutionPolicy Bypass -File scripts\start_mobile_preview.ps1 -InitWindows
powershell -ExecutionPolicy Bypass -File scripts\start_mobile_preview.ps1 -SkipBackend
```

Batch shortcut:

```bat
scripts\start_mobile_preview.bat
```

## Free public tunnel (Cloudflare)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_free_mobile_tunnel.ps1
```

Options:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_free_mobile_tunnel.ps1 -Port 8787 -ApiHost 0.0.0.0
powershell -ExecutionPolicy Bypass -File scripts\start_free_mobile_tunnel.ps1 -SkipBackend
```

## Build Android APK (release)

```powershell
cd mobile_flutter_client
flutter build apk --release `
	--dart-define=FACE_STUDIO_BASE_URL=https://your-api-domain.com `
	--dart-define=FACE_STUDIO_API_KEY=YOUR_API_KEY
```

If Flutter is not in PATH:

```powershell
cd mobile_flutter_client
./flutterw.ps1 build apk --release `
	--dart-define=FACE_STUDIO_BASE_URL=https://your-api-domain.com `
	--dart-define=FACE_STUDIO_API_KEY=YOUR_API_KEY
```

APK output:

- mobile_flutter_client/build/app/outputs/flutter-apk/app-release.apk

## Render deploy start command

```bash
python scripts/app_runner.py api --host 0.0.0.0 --port $PORT
```

## Quick quality checks (mobile)

```powershell
cd mobile_flutter_client
flutter analyze
flutter test
```

## Full dev (backend + GUI)

Start backend API and desktop GUI together (opens two terminals):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_dev_all.ps1
```

Options:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_dev_all.ps1 -SkipBackend
powershell -ExecutionPolicy Bypass -File scripts\start_dev_all.ps1 -SkipGui
```
