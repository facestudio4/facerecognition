"""Hugging Face Inference API image generation.

Runs the realistic generation OFF the free Render box (which has no GPU) by
calling Hugging Face's hosted models over HTTP:

  - text_to_image(prompt)  -> realistic image from a description (FLUX/SDXL)
  - image_to_image(img, prompt) -> realistic stylisation of a user's photo

Only requires a FREE HF token in env `HF_API_TOKEN` (or `HUGGINGFACE_API_TOKEN`).
Uses urllib only (no extra deps). Handles HF cold-start (503 + estimated_time)
with a few retries. Raises RuntimeError on failure so callers can fall back.
"""

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

_HF_BASE = "https://api-inference.huggingface.co/models/"

# FLUX.1-schnell is free on HF serverless, fast (~4 steps) and very realistic.
_DEFAULT_TXT2IMG = "black-forest-labs/FLUX.1-schnell"
# instruct-pix2pix edits an existing photo from a text instruction.
_DEFAULT_IMG2IMG = "timbrooks/instruct-pix2pix"


def _token() -> str:
    return (os.getenv("HF_API_TOKEN")
            or os.getenv("HUGGINGFACE_API_TOKEN") or "").strip()


def available() -> bool:
    return bool(_token())


def _request_image(model: str, payload: bytes, retries: int = 4,
                   timeout: int = 120) -> bytes:
    """POST JSON, return raw image bytes. Retries HF model cold-starts."""
    token = _token()
    if not token:
        raise RuntimeError("HF_API_TOKEN not set")
    url = _HF_BASE + model.strip()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "image/png",
        # Block until the model is loaded instead of erroring immediately.
        "x-wait-for-model": "true",
    }
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=payload, headers=headers,
                                         method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                ctype = resp.headers.get("Content-Type", "")
                body = resp.read()
                if ctype.startswith("image/"):
                    return body
                # JSON came back -> error or "currently loading".
                try:
                    info = json.loads(body.decode("utf-8", "ignore"))
                except Exception:
                    info = {}
                wait = float(info.get("estimated_time", 8) or 8)
                last_err = RuntimeError(str(info.get("error", "model loading")))
                time.sleep(min(25.0, max(3.0, wait)))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:200]
            if e.code == 503:  # model loading
                try:
                    wait = float(json.loads(detail).get("estimated_time", 8))
                except Exception:
                    wait = 8.0
                last_err = RuntimeError(f"503 loading: {detail}")
                time.sleep(min(25.0, max(3.0, wait)))
                continue
            if e.code == 429:  # rate limited
                last_err = RuntimeError("HF rate limit (429)")
                time.sleep(6.0)
                continue
            raise RuntimeError(f"HF {e.code}: {detail}")
        except Exception as e:  # network/timeout
            last_err = e
            time.sleep(4.0)
    raise last_err or RuntimeError("HF request failed")


def text_to_image(prompt: str, negative_prompt: str = "",
                  width: int = 768, height: int = 768,
                  model: str = "") -> bytes:
    model = model or os.getenv("HF_TXT2IMG_MODEL", _DEFAULT_TXT2IMG)
    params = {"width": int(width), "height": int(height)}
    if negative_prompt:
        params["negative_prompt"] = negative_prompt
    payload = json.dumps({"inputs": prompt, "parameters": params}).encode("utf-8")
    return _request_image(model, payload)


def pollinations_available() -> bool:
    # Keyless public endpoint — always usable unless explicitly disabled.
    return os.getenv("POLLINATIONS_DISABLED", "").strip() not in ("1", "true", "True")


def pollinations_text_to_image(prompt: str, width: int = 1024,
                               height: int = 1024, model: str = "",
                               retries: int = 5) -> bytes:
    """FREE, no-API-key text->image (pollinations.ai). Used as the default so
    realistic generation works with zero server setup. Retries on 429/5xx since
    the keyless endpoint rate-limits shared server IPs."""
    model = model or os.getenv("POLLINATIONS_MODEL", "flux")
    referrer = os.getenv("POLLINATIONS_REFERRER", "facestudio.app")
    token = os.getenv("POLLINATIONS_TOKEN", "").strip()
    enc = urllib.parse.quote(prompt[:1500], safe="")
    headers = {"User-Agent": "FaceStudio/1.0", "Accept": "image/*"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    last = None
    for attempt in range(retries):
        seed = (int(time.time()) + attempt * 7) % 1000000
        url = (f"https://image.pollinations.ai/prompt/{enc}"
               f"?width={int(width)}&height={int(height)}&model={model}"
               f"&seed={seed}&nologo=true&private=true&referrer={referrer}")
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
            if data and len(data) >= 1024:
                return data
            last = RuntimeError("empty image")
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503, 504):
                # Keyless endpoint rate-limits shared IPs; ride out the window.
                time.sleep(min(20.0, 5.0 + attempt * 3.0))
                continue
            raise
        except Exception as e:  # network/timeout
            last = e
            time.sleep(4.0)
    raise last or RuntimeError("pollinations failed")


def image_to_image(image_bytes: bytes, prompt: str,
                   negative_prompt: str = "", model: str = "") -> bytes:
    """Best-effort realistic edit of an existing photo. HF serverless img2img
    support varies by model, so callers should fall back on RuntimeError."""
    model = model or os.getenv("HF_IMG2IMG_MODEL", _DEFAULT_IMG2IMG)
    b64 = base64.b64encode(image_bytes).decode("ascii")
    params = {"prompt": prompt, "guidance_scale": 7.0, "image_guidance_scale": 1.5}
    if negative_prompt:
        params["negative_prompt"] = negative_prompt
    payload = json.dumps({"inputs": b64, "parameters": params}).encode("utf-8")
    return _request_image(model, payload)
