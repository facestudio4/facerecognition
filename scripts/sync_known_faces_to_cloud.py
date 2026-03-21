import argparse
import base64
import json
import os
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


def resolve_source_dir(source_dir: str):
    raw = (source_dir or "").strip()
    if not raw:
        raw = "database/faces"

    candidates = []
    if os.path.isabs(raw):
        candidates.append(raw)
    else:
        cwd = os.getcwd()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        candidates.extend(
            [
                os.path.join(cwd, raw),
                os.path.join(script_dir, raw),
                os.path.join(project_root, raw),
            ]
        )

    for path in candidates:
        full = os.path.abspath(path)
        if os.path.isdir(full):
            return full

    raise ValueError(f"source directory not found: {os.path.abspath(candidates[0]) if candidates else raw}")


def collect_entries(source_dir: str):
    entries = []
    source_dir = resolve_source_dir(source_dir)

    for person in sorted(os.listdir(source_dir)):
        person_dir = os.path.join(source_dir, person)
        if not os.path.isdir(person_dir):
            continue
        if person.lower() in SKIP_DIRS:
            continue

        for fname in sorted(os.listdir(person_dir)):
            fpath = os.path.join(person_dir, fname)
            if not os.path.isfile(fpath):
                continue
            _, ext = os.path.splitext(fname)
            if ext.lower() not in IMAGE_EXTS:
                continue
            with open(fpath, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            entries.append(
                {
                    "person": person,
                    "filename": fname,
                    "image_b64": b64,
                }
            )
    return entries


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


def main():
    parser = argparse.ArgumentParser(description="Sync local known face images to cloud backend")
    parser.add_argument("--base-url", required=True, help="Example: https://facerecognition-4.onrender.com")
    parser.add_argument("--api-key", default="", help="X-API-Key from backend")
    parser.add_argument("--token", default="", help="Bearer token from /api/auth/login")
    parser.add_argument("--source-dir", default="database/faces", help="Local source folder")
    parser.add_argument("--batch-size", type=int, default=25, help="Entries per request")
    parser.add_argument("--clear-existing", action="store_true", help="Clear cloud person folders before first upload")
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)
    endpoint = f"{base_url}/api/admin/faces/sync"
    api_key = (args.api_key or "").strip()
    token = (args.token or "").strip()

    if not api_key and not token:
        raise SystemExit("Provide either --api-key or --token")
    if api_key.upper() == "YOUR_RENDER_API_KEY":
        raise SystemExit("Replace placeholder YOUR_RENDER_API_KEY with your real API key")

    entries = collect_entries(args.source_dir)
    if not entries:
        raise SystemExit("No valid face images found to upload")

    batch_size = max(1, int(args.batch_size))
    total = len(entries)
    sent = 0
    batch_index = 0
    first = True

    while sent < total:
        batch = entries[sent : sent + batch_size]
        payload = {
            "entries": batch,
            "clear_existing": bool(args.clear_existing and first),
        }
        result = post_json(endpoint, api_key, token, payload)
        sent += len(batch)
        batch_index += 1
        first = False
        print(f"batch {batch_index}: uploaded {sent}/{total}")
        print(json.dumps(result, ensure_ascii=False))

    print("sync completed")


if __name__ == "__main__":
    main()
