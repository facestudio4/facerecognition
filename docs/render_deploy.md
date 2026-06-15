# Render Deployment (Mobile Backend API)

## 1. Create the web service

1. Push this repository to GitHub.
2. In Render, click New + -> Blueprint.
3. Select your repository.
4. Render will detect `render.yaml` and create `face-studio-api`.

## 2. Environment variables

Use the values in `.env.render.example`.

Minimum required:
- `APP_ENV=production`
- `API_HOST=0.0.0.0`
- `SQLITE_PATH=/var/data/facestudio.db`

Recommended mobile update vars:
- `FACE_STUDIO_MOBILE_LATEST_VERSION`
- `FACE_STUDIO_MOBILE_MIN_VERSION`
- `FACE_STUDIO_MOBILE_APK_URL`
- `FACE_STUDIO_MOBILE_UPDATE_NOTES`
- `FACE_STUDIO_MOBILE_FORCE_UPDATE`

Main 5 env vars for app update:

```env
FACE_STUDIO_MOBILE_LATEST_VERSION=0.1.0+33
FACE_STUDIO_MOBILE_MIN_VERSION=0.1.0+33
FACE_STUDIO_MOBILE_APK_URL=https://github.com/facestudio4/facerecognition/releases/download/v0.1.0%2B33/mobile_0.1.0%2B33.apk
FACE_STUDIO_MOBILE_UPDATE_NOTES=Face Studio mobile v0.1.0+33 improves recognition reliability, smoother card visuals, and behind-the-scenes performance and stability fixes.
FACE_STUDIO_MOBILE_FORCE_UPDATE=false
```

## Email (verification codes) — REQUIRED for signup OTP

**Render blocks outbound SMTP** (you'll see `SMTP network error: [Errno 101]
Network is unreachable`), so Gmail/SMTP can never send from Render. Use an HTTP
email API instead. Recommended: **Brevo** (free 300 emails/day, no domain needed).

Setup:
1. Create a free account at brevo.com.
2. Settings → Senders: add and **verify** your sender email (the same value you
   use for `FACESTUDIO_SMTP_FROM`, e.g. your Gmail). Click the confirmation link.
3. Settings → SMTP & API → **API Keys**: create a key.
4. On Render set:
   - `FACESTUDIO_BREVO_API_KEY=<the key>`
   - `FACESTUDIO_SMTP_FROM=<your verified sender email>`
   - `FACESTUDIO_EMAIL_FROM_NAME=Face Studio` (optional)
5. Redeploy. When `FACESTUDIO_BREVO_API_KEY` is set, the backend sends via Brevo's
   HTTPS API (port 443, not blocked) instead of SMTP.

Optional (SMTP — local-dev fallback only, does NOT work on Render):
- `FACESTUDIO_SMTP_HOST`
- `FACESTUDIO_SMTP_USER`
- `FACESTUDIO_SMTP_APP_PASSWORD`
- `FACESTUDIO_SMTP_FROM`
- `FACESTUDIO_SMTP_PORT`
- `FACESTUDIO_SMTP_TLS`
- `FACESTUDIO_SMTP_SSL`
- `FACESTUDIO_SMTP_TIMEOUT`
- `FACESTUDIO_SMTP_TOTAL_TIMEOUT`

Main values to set on Render:

```env
APP_ENV=production
API_HOST=0.0.0.0
SQLITE_PATH=/var/data/facestudio.db

FACESTUDIO_SMTP_HOST=smtp.gmail.com
FACESTUDIO_SMTP_USER=<your-gmail-address>
FACESTUDIO_SMTP_APP_PASSWORD=<your-16-char-google-app-password>
FACESTUDIO_SMTP_FROM=<your-gmail-address>
FACESTUDIO_SMTP_PORT=587
FACESTUDIO_SMTP_TLS=1
FACESTUDIO_SMTP_SSL=0
FACESTUDIO_SMTP_TIMEOUT=15
FACESTUDIO_SMTP_TOTAL_TIMEOUT=18
FACESTUDIO_SIGNUP_ALLOW_SMTP_FALLBACK=1
```

## 3. Start command used on Render

`python scripts/app_runner.py api --host 0.0.0.0 --port $PORT`

## 4. Verify deployment

1. Open health endpoint:
   - `https://<your-render-service>.onrender.com/api/health`
2. Open docs endpoint:
   - `https://<your-render-service>.onrender.com/api/docs`

## 5. Connect Flutter app to Render backend

Build with dart defines:

```powershell
flutter build apk --release `
  --dart-define=FACE_STUDIO_BASE_URL=https://<your-render-service>.onrender.com `
  --dart-define=FACE_STUDIO_API_KEY=<your-api-key>
```

Notes:
- Your app currently defaults to a Render URL in code, but release builds should set `FACE_STUDIO_BASE_URL` explicitly.
- API key is generated/stored in SQLite `project_meta` as `api_key`.
