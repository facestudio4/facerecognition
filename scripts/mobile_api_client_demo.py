import argparse
import base64
import json
import pathlib
import urllib.error
import urllib.parse
import urllib.request


def http_get_json(url: str, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_post_json(url: str, body: dict, headers: dict | None = None) -> dict:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def to_b64(path: pathlib.Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description="Mobile API demo client")
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--style", default="Anime")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--out", default="generated_mobile.jpg")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    image_path = pathlib.Path(args.image)
    if not image_path.exists():
        print(f"Image not found: {image_path}")
        return 1

    try:
        token_res = http_get_json(
            f"{base_url}/api/auth/token?subject=mobile_demo&ttl=120",
            headers={"X-API-Key": args.api_key},
        )
        token = token_res["data"]["token"]
        auth = {"Authorization": f"Bearer {token}"}

        styles_res = http_get_json(f"{base_url}/api/mobile/styles", headers=auth)
        styles = styles_res.get("data", {}).get("styles", [])
        print("Available styles:", ", ".join(styles))

        image_b64 = to_b64(image_path)

        identify_res = http_post_json(
            f"{base_url}/api/mobile/identify",
            {"image_b64": image_b64, "top_k": args.top_k},
            headers=auth,
        )
        print("Identify result:")
        print(json.dumps(identify_res.get("data", {}), ensure_ascii=False, indent=2))

        generate_res = http_post_json(
            f"{base_url}/api/mobile/generate",
            {"image_b64": image_b64, "filter_name": args.style},
            headers=auth,
        )
        out_b64 = generate_res.get("data", {}).get("image_b64", "")
        if not out_b64:
            print("No generated image returned")
            return 2

        pathlib.Path(args.out).write_bytes(base64.b64decode(out_b64))
        print(f"Generated image saved: {args.out}")
        return 0

    except urllib.error.HTTPError as e:
        try:
            payload = e.read().decode("utf-8")
        except Exception:
            payload = str(e)
        print("HTTP Error:", e.code, payload)
        return 3
    except Exception as e:
        print("Error:", e)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
