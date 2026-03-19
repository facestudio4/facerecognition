Face Studio 24x7 Deployment Guide

Goal
- Keep API always online.
- Use one stable HTTPS backend URL in the mobile app.
- Share APK with users.

Important
- A laptop cannot run 24x7 if it is closed, asleep, shut down, or without internet.
- Ngrok free URLs are temporary and change.
- For real 24x7, deploy backend to cloud hosting.

Option A: Render deployment (recommended)

1. Push this project to GitHub.
2. Create account on Render.
3. New service -> Web Service.
4. Connect your GitHub repository.
5. Configure service:
- Runtime: Docker
- Dockerfile path: Dockerfile
- Region: nearest to your users
- Health check path: /api/health
6. Environment variables:
- API_HOST = 0.0.0.0
- APP_ENV = prod
- APP_NAME = FaceRecognitionStudio
7. Deploy service.
8. After deploy, copy your Render URL:
- Example: https://face-studio-api.onrender.com
9. Test in browser:
- https://face-studio-api.onrender.com/api/health
10. If health returns ok true, backend is 24x7 online.

Build Android app with stable backend URL

From project root run:

powershell -ExecutionPolicy Bypass -File scripts/build_mobile_release.ps1 -BackendUrl https://face-studio-api.onrender.com

APK output:
- mobile_flutter_client/build/app/outputs/flutter-apk/app-release.apk

Share app to users

1. Upload APK to Google Drive or similar.
2. Share download link.
3. Users install APK and login.
4. If app should update automatically and be public, publish on Google Play.

Update backend URL in future

If backend domain changes, build a new APK with the new URL:

powershell -ExecutionPolicy Bypass -File scripts/build_mobile_release.ps1 -BackendUrl https://new-api-domain.com

Production checklist

- Backend URL uses HTTPS.
- API health endpoint is reachable.
- Mobile login works.
- Recognition and map endpoints work.
- Keep database backups.
- Rotate API keys and secrets regularly.
