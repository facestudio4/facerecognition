# Mobile API Quickstart

This project now exposes mobile-ready endpoints from the backend API.

## 1) Start API Server

Run from project root:

```powershell
python scripts/app_runner.py api --host 0.0.0.0 --port 8787
```

If testing from same machine, use `http://127.0.0.1:8787`.

## 2) Get API Key

Open the Services Hub UI once, or read your API key from the `project_meta` table in your SQLite DB.

## 3) Issue Bearer Token

```powershell
curl -H "X-API-Key: YOUR_API_KEY" "http://127.0.0.1:8787/api/auth/token?subject=mobile&ttl=720"
```

Response contains `data.token`.

## 4) Mobile Endpoints

### Styles list

```powershell
curl -H "Authorization: Bearer YOUR_TOKEN" "http://127.0.0.1:8787/api/mobile/styles"
```

### Identify face

POST JSON body:

```json
{
  "image_b64": "<base64 encoded image>",
  "top_k": 3
}
```

Endpoint:

```powershell
curl -X POST "http://127.0.0.1:8787/api/mobile/identify" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d "{\"image_b64\":\"...\",\"top_k\":3}"
```

### Generate stylized image

POST JSON body:

```json
{
  "image_b64": "<base64 encoded image>",
  "filter_name": "Anime"
}
```

Endpoint:

```powershell
curl -X POST "http://127.0.0.1:8787/api/mobile/generate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d "{\"image_b64\":\"...\",\"filter_name\":\"Anime\"}"
```

Response contains `data.image_b64` (generated JPG).

## 5) Fast Local Test Script

Use:

```powershell
python scripts/mobile_api_client_demo.py --api-key YOUR_API_KEY --image path\to\face.jpg
```

Optional arguments:

- `--base-url http://127.0.0.1:8787`
- `--style Anime`
- `--top-k 3`
- `--out generated_mobile.jpg`
