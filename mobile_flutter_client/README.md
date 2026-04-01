# Face Studio Mobile Client (Flutter Starter)

This is a minimal Flutter starter app that talks to your Face Studio backend API.

## What this client does

- Issues bearer token from API key
- Picks image from gallery
- Calls mobile identify endpoint
- Calls mobile generate endpoint
- Shows generated image

## Prerequisites

- Flutter SDK installed
- Android Studio (or Android SDK + emulator/device)
- Backend API running

## 1) Start Backend API

From project root:

```powershell
python scripts/app_runner.py api --host 0.0.0.0 --port 8787
```

## 2) Run Flutter app

From this folder:

```powershell
flutter pub get
flutter run
```

If `flutter` is still not recognized, use the wrapper included in this folder:

```powershell
./flutterw.ps1 pub get
./flutterw.ps1 run
```

Or from `cmd`:

```bat
flutterw.bat pub get
flutterw.bat run
```

If `flutter` is not recognized on Windows, use this exact setup (copy-paste line by line):

```powershell
# Puro executable installed by winget
$PURO = "C:\Users\shishir\AppData\Local\Microsoft\WinGet\Packages\pingbird.Puro_Microsoft.Winget.Source_8wekyb3d8bbwe\puro.exe"

# Remove broken environment (if any)
& $PURO rm stable

# Recreate stable Flutter environment
& $PURO create stable stable

# Verify Flutter works
& $PURO flutter --version

# Use Flutter via Puro
& $PURO flutter pub get
& $PURO flutter run
```

Important:
- Do not type prose like `Remove broken environment ...` as a command.
- In PowerShell, run only the actual command lines shown above.

## 3) Base URL Notes

- Android emulator to host machine: `http://10.0.2.2:8787`
- Physical device on same Wi-Fi: `http://<your-pc-lan-ip>:8787`
- For internet users and 24x7 use, deploy backend to cloud and use HTTPS URL.

## 4) 24x7 Production Setup

- Follow the deployment guide: `docs/DEPLOY_24X7.md`
- Build release APK with stable backend URL:

```powershell
powershell -ExecutionPolicy Bypass -File ..\scripts\build_mobile_release.ps1 -BackendUrl https://your-api-domain.com
```

## 5) Build APK

```powershell
flutter build apk --release
```

If PATH issue continues:

```powershell
./flutterw.ps1 build apk --release
```

If build says `No Android SDK found`, install and configure Android Studio first:

```powershell
winget install -e --id Google.AndroidStudio
```

Then open Android Studio once and install SDK + Platform Tools from SDK Manager.
After that, set SDK path in a new PowerShell window:

```powershell
[Environment]::SetEnvironmentVariable("ANDROID_HOME", "$env:LOCALAPPDATA\Android\Sdk", "User")
[Environment]::SetEnvironmentVariable("ANDROID_SDK_ROOT", "$env:LOCALAPPDATA\Android\Sdk", "User")
$env:Path += ";$env:LOCALAPPDATA\Android\Sdk\platform-tools;$env:LOCALAPPDATA\Android\Sdk\cmdline-tools\latest\bin"
```

Accept licenses and re-check setup:

```powershell
flutter doctor
flutter doctor --android-licenses
```

If `flutter` is not recognized, run the same checks with the local wrapper:

```powershell
./flutterw.ps1 doctor
./flutterw.ps1 doctor --android-licenses
```

Or from `cmd`:

```bat
flutterw.bat doctor
flutterw.bat doctor --android-licenses
```

Release APK output:

- `build/app/outputs/flutter-apk/app-release.apk`

## 6) Share APK

Share `app-release.apk` via Drive/WhatsApp/Telegram.
Recipients only install APK; they do not need to build UI.

## Security note

Use HTTPS + proper auth in production. Do not hardcode secret keys in app binaries.
