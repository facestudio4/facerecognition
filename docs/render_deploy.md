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

Optional (email OTP/reset):
- `FACESTUDIO_SMTP_HOST`
- `FACESTUDIO_SMTP_USER`
- `FACESTUDIO_SMTP_APP_PASSWORD`
- `FACESTUDIO_SMTP_FROM`
- `FACESTUDIO_SMTP_PORT`
- `FACESTUDIO_SMTP_TLS`
- `FACESTUDIO_SMTP_SSL`
- `FACESTUDIO_SMTP_TIMEOUT`
- `FACESTUDIO_SMTP_TOTAL_TIMEOUT`

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
