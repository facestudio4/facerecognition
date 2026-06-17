"""Tiny Supabase Storage client (HTTP only, no SDK) used to persist the SQLite
DB, the face-encodings cache, and face images on hosts with no durable disk
(e.g. Render's free tier, where /var/data is wiped on every redeploy/sleep).

Configured via env vars:
  SUPABASE_URL          e.g. https://xxxx.supabase.co   (a /rest/v1 suffix is OK)
  SUPABASE_SERVICE_KEY  the service_role key
  SUPABASE_BUCKET       defaults to 'facestudio-data'
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request


def _cfg():
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    if url.endswith("/rest/v1"):
        url = url[: -len("/rest/v1")]
    if url.endswith("/storage/v1"):
        url = url[: -len("/storage/v1")]
    key = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
    bucket = os.environ.get("SUPABASE_BUCKET", "facestudio-data").strip() or "facestudio-data"
    return url, key, bucket


def enabled() -> bool:
    url, key, _ = _cfg()
    return bool(url and key)


def _headers(extra=None):
    _, key, _ = _cfg()
    h = {"Authorization": f"Bearer {key}", "apikey": key}
    if extra:
        h.update(extra)
    return h


def _encode_path(remote: str) -> str:
    # Encode each path segment but keep the slashes.
    return "/".join(urllib.parse.quote(seg, safe="") for seg in remote.split("/"))


def upload_bytes(remote: str, data: bytes,
                 content_type: str = "application/octet-stream") -> bool:
    url, _, bucket = _cfg()
    if not enabled():
        return False
    req = urllib.request.Request(
        f"{url}/storage/v1/object/{bucket}/{_encode_path(remote)}",
        data=data,
        method="POST",
        headers=_headers({"Content-Type": content_type, "x-upsert": "true"}),
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return 200 <= r.status < 300
    except Exception:
        return False


def upload_file(remote: str, local_path: str,
                content_type: str = "application/octet-stream") -> bool:
    try:
        with open(local_path, "rb") as f:
            data = f.read()
    except Exception:
        return False
    return upload_bytes(remote, data, content_type)


def delete_file(remote: str) -> bool:
    """Delete a single object. Returns True on success (or if already gone)."""
    url, _, bucket = _cfg()
    if not enabled():
        return False
    req = urllib.request.Request(
        f"{url}/storage/v1/object/{bucket}/{_encode_path(remote)}",
        method="DELETE",
        headers=_headers(),
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return 200 <= r.status < 300
    except urllib.error.HTTPError as e:
        return e.code == 404  # already absent -> treat as success
    except Exception:
        return False


def download_file(remote: str, local_path: str) -> bool:
    """Download remote -> local_path. Returns True only on a successful 200."""
    url, _, bucket = _cfg()
    if not enabled():
        return False
    req = urllib.request.Request(
        f"{url}/storage/v1/object/{bucket}/{_encode_path(remote)}",
        method="GET",
        headers=_headers(),
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            if r.status != 200:
                return False
            data = r.read()
    except Exception:
        return False
    try:
        parent = os.path.dirname(local_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        tmp = f"{local_path}.dl.tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, local_path)
        return True
    except Exception:
        return False


def _list_dir(prefix: str):
    """List immediate children of a 'folder' prefix. Returns list of dicts with
    'name' and 'id' (id is None for sub-folders)."""
    url, _, bucket = _cfg()
    body = json.dumps({
        "prefix": prefix,
        "limit": 1000,
        "offset": 0,
        "sortBy": {"column": "name", "order": "asc"},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{url}/storage/v1/object/list/{bucket}",
        data=body,
        method="POST",
        headers=_headers({"Content-Type": "application/json"}),
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return []


def list_files(prefix: str = "", _depth: int = 0) -> list:
    """Recursively list full object paths under prefix (files only)."""
    if _depth > 6:
        return []
    out = []
    items = _list_dir(prefix)
    if not isinstance(items, list):
        return out
    base = (prefix.rstrip("/") + "/") if prefix else ""
    for it in items:
        name = it.get("name") if isinstance(it, dict) else None
        if not name:
            continue
        full = f"{base}{name}"
        if isinstance(it, dict) and it.get("id"):
            out.append(full)  # a file
        else:
            out.extend(list_files(full, _depth + 1))  # a sub-folder
    return out
