import argparse
import base64
import json
import os
import re
import urllib.request
from urllib.error import HTTPError


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SKIP_DIRS = {"known_faces", "archive", "__pycache__"}


def normalize_base_url(url: str) -> str:
    value = (url or "").strip().rstrip("/")
    if not value:
        raise ValueError("base-url is required")
    if not (value.startswith("http://") or value.startswith("https://")):
        value = "https://" + value
    return value


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "_", value or "").strip("_")
    return cleaned or "person"


def post_json(url: str, api_key: str | None, token: str | None, payload: dict):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["X-API-Key"] = api_key
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(
        url=url,
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except HTTPError as e:
        details = ""
        try:
            details = e.read().decode("utf-8", errors="replace")
        except Exception:
            details = ""
        if details:
            raise RuntimeError(f"HTTP {e.code} {e.reason}: {details}") from e
        raise RuntimeError(f"HTTP {e.code} {e.reason}") from e


def write_entries(entries: list, dest_dir: str, clear_existing: bool):
    if not os.path.isdir(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)

    if clear_existing:
        for name in os.listdir(dest_dir):
            path = os.path.join(dest_dir, name)
            if not os.path.isdir(path):
                continue
            if name.lower() in SKIP_DIRS:
                continue
            try:
                for root, _, files in os.walk(path):
                    for fname in files:
                        try:
                            os.remove(os.path.join(root, fname))
                        except Exception:
                            pass
                os.rmdir(path)
            except Exception:
                pass

    imported = 0
    for item in entries:
        if not isinstance(item, dict):
            continue
        person = safe_name(item.get("person", ""))
        filename = os.path.basename(str(item.get("filename", "")).strip())
        if not filename:
            filename = "face.jpg"
        root, ext = os.path.splitext(filename)
        if ext.lower() not in IMAGE_EXTS:
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

        person_dir = os.path.join(dest_dir, person)
        os.makedirs(person_dir, exist_ok=True)
        out_path = os.path.join(person_dir, out_name)
        with open(out_path, "wb") as f:
            f.write(raw)
        imported += 1

    return imported


def main():
    parser = argparse.ArgumentParser(description="Pull face images from cloud backend to local database")
    parser.add_argument("--base-url", required=True, help="Example: https://facerecognition-4.onrender.com")
    parser.add_argument("--api-key", default="", help="X-API-Key from backend")
    parser.add_argument("--token", default="", help="Bearer token from /api/auth/login")
    parser.add_argument("--dest-dir", default="database/faces", help="Local destination folder")
    parser.add_argument("--person", default="", help="Optional person filter")
    parser.add_argument("--limit", type=int, default=0, help="Limit entries (0 = all)")
    parser.add_argument("--clear-existing", action="store_true", help="Clear local faces before sync")
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)
    endpoint = f"{base_url}/api/admin/faces/export"
    api_key = (args.api_key or "").strip()
    token = (args.token or "").strip()

    if not api_key and not token:
        raise SystemExit("Provide either --api-key or --token")
    if api_key.upper() == "YOUR_RENDER_API_KEY":
        raise SystemExit("Replace placeholder YOUR_RENDER_API_KEY with your real API key")

    payload = {
        "person": args.person,
        "limit": int(args.limit or 0),
    }
    result = post_json(endpoint, api_key, token, payload)
    if result.get("ok") is not True:
        raise SystemExit(f"Export failed: {result}")

    data = result.get("data") or {}
    entries = data.get("entries") or []
    imported = write_entries(entries, args.dest_dir, bool(args.clear_existing))
    print(f"imported {imported} files to {args.dest_dir}")


if __name__ == "__main__":
    main()
