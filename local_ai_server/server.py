"""Face Studio local AI server — SD1.5 + IP-Adapter FaceID on your own GPU.

Generates a realistic image with a real person's likeness baked in (no paste).
Fits an 8GB GPU, ~10-20s per image.

POST /generate { "prompt": "...", "person": "vraj", "negative_prompt": "..." }
  -> { ok, image_b64, person }
GET  /health -> { ok, ready, people:[...] }

Run:  double-click "Start Face Studio AI.bat"  (or run server.py with the venv)
"""
import os
os.environ.setdefault("HF_HOME", r"C:\face_studio_ai\hf_cache")
import sys
sys.path.insert(0, r"C:\face_studio_ai\ipa")     # IP-Adapter repo's ip_adapter
import io
import json
import base64
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
import torch

ROOT = r"C:\face_studio_ai"
FACES_ROOT = os.environ.get(
    "FACES_ROOT",
    r"c:\Users\shishir\OneDrive\Documents\Python\facerecognition\database\faces")
PORT = int(os.environ.get("PORT", "7860"))
_FACE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

_pipe = None
_ip = None
_app = None


def _load():
    global _pipe, _ip, _app
    if _ip is not None:
        return
    from diffusers import (StableDiffusionPipeline, AutoencoderKL,
                           DDIMScheduler)
    from insightface.app import FaceAnalysis
    from ip_adapter.ip_adapter_faceid import IPAdapterFaceIDPlus
    print("Loading face model (buffalo_l)…", flush=True)
    app = FaceAnalysis(name="buffalo_l", root=ROOT,
                       providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(640, 640))
    print("Loading SD1.5 + IP-Adapter FaceID…", flush=True)
    vae = AutoencoderKL.from_pretrained(os.path.join(ROOT, "sd-vae-ft-mse"),
                                        torch_dtype=torch.float16)
    sched = DDIMScheduler(num_train_timesteps=1000, beta_start=0.00085,
                          beta_end=0.012, beta_schedule="scaled_linear",
                          clip_sample=False, set_alpha_to_one=False,
                          steps_offset=1)
    pipe = StableDiffusionPipeline.from_pretrained(
        os.path.join(ROOT, "RealisticVision"), torch_dtype=torch.float16,
        scheduler=sched, vae=vae, safety_checker=None, feature_extractor=None)
    pipe.to("cuda")
    ip = IPAdapterFaceIDPlus(
        pipe, os.path.join(ROOT, "IP-Adapter", "models", "image_encoder"),
        os.path.join(ROOT, "IP-Adapter-FaceID",
                     "ip-adapter-faceid-plusv2_sd15.bin"), "cuda")
    _pipe, _ip, _app = pipe, ip, app
    if torch.cuda.is_available():
        print(f"  VRAM: {torch.cuda.memory_allocated()/1e9:.2f} GB", flush=True)
    print("READY — server can generate now.", flush=True)


def _people():
    if not os.path.isdir(FACES_ROOT):
        return []
    return [e for e in os.listdir(FACES_ROOT)
            if os.path.isdir(os.path.join(FACES_ROOT, e))
            and e.lower() not in {"known_faces", "archive", "__pycache__"}]


_GEN_STOPWORDS = {
    "playing", "with", "dog", "cat", "the", "and", "of", "make", "picture",
    "image", "photo", "generate", "create", "in", "on", "at", "is", "to", "for",
    "me", "my", "him", "her", "them", "person", "people", "man", "woman", "boy",
    "girl", "scene", "background", "wearing", "holding", "a", "an"}


def _detect_person_in_prompt(prompt):
    """Find a known person (face folder) named anywhere in the prompt."""
    import re
    text = " " + (prompt or "").lower() + " "
    names = sorted(_people(), key=len, reverse=True)
    for nm in names:
        if nm and re.search(r"\b" + re.escape(nm.lower()) + r"\b", text):
            return nm
    for nm in names:
        for w in nm.lower().split():
            if len(w) >= 3 and w not in _GEN_STOPWORDS and \
                    re.search(r"\b" + re.escape(w) + r"\b", text):
                return nm
    return ""


def _find_person_dir(person):
    safe = person.strip().lower()
    if not safe or not os.path.isdir(FACES_ROOT):
        return ""
    people = _people()
    for e in people:
        if e.lower() == safe:
            return os.path.join(FACES_ROOT, e)
    for e in people:
        if safe in e.lower().split() or safe in e.lower():
            return os.path.join(FACES_ROOT, e)
    return ""


def _detect(img):
    """Detect a face; if the crop is too tight (face fills frame), pad + retry."""
    faces = _app.get(img)
    if faces:
        return img, faces
    h, w = img.shape[:2]
    pad = int(0.35 * max(h, w))
    padded = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
    return padded, _app.get(padded)


def _reference(person_dir):
    """Best face across the photos -> (faceid_embeds, aligned crop, gender)."""
    from insightface.utils import face_align
    best = None
    best_score = -1.0
    files = [f for f in sorted(os.listdir(person_dir))
             if os.path.splitext(f)[1].lower() in _FACE_EXTS]
    for fn in files[:24]:
        img = cv2.imread(os.path.join(person_dir, fn))
        if img is None:
            continue
        img, faces = _detect(img)
        if not faces:
            continue
        fc = max(faces, key=lambda x: (x.bbox[2]-x.bbox[0])*(x.bbox[3]-x.bbox[1]))
        score = float((fc.bbox[2]-fc.bbox[0]) * (fc.bbox[3]-fc.bbox[1]))
        if score > best_score:
            best_score = score
            emb = torch.from_numpy(fc.normed_embedding).unsqueeze(0)
            crop = face_align.norm_crop(img, landmark=fc.kps, image_size=224)
            g = getattr(fc, "sex", None)
            gender = "man" if g == "M" else ("woman" if g == "F" else "person")
            best = (emb, crop, gender)
    return best


def generate(prompt, person="", negative=""):
    import re
    _load()
    # If no person was passed, detect one named in the prompt itself.
    if not person:
        person = _detect_person_in_prompt(prompt)
    if not person:
        return None, "no_person", ""      # app falls back to cloud for generics
    pdir = _find_person_dir(person)
    if not pdir:
        return None, "not_found", ""
    ref = _reference(pdir)
    if ref is None:
        return None, "no_face", ""
    emb, crop, gender = ref
    # The identity comes from the face embedding, so use a GENERIC subject noun
    # in the text (a model doesn't know the person's name, and naming-as-subject
    # makes FaceID fuse the face with scene objects). Strip the name, prepend
    # "a man/woman".
    action = re.sub(r"\b" + re.escape(person) + r"\b", "", prompt,
                    flags=re.I).strip(" ,.")
    full = (f"a {gender} {action}, solo, one person, front view, looking at the "
            "camera, photorealistic, natural lighting, sharp focus, highly "
            "detailed, 8k").replace("  ", " ")
    neg = negative or ("cartoon, anime, blurry, deformed, disfigured, extra "
                       "fingers, bad anatomy, watermark, text, back of head, "
                       "facing away, multiple people, animal face")
    images = _ip.generate(
        prompt=full, negative_prompt=neg, face_image=crop, faceid_embeds=emb,
        shortcut=True, s_scale=1.0, num_samples=1, width=512, height=640,
        num_inference_steps=int(os.environ.get("GEN_STEPS", "30")),
        guidance_scale=6.0)
    buf = io.BytesIO()
    images[0].save(buf, format="JPEG", quality=92)
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return base64.b64encode(buf.getvalue()).decode("ascii"), "ok", person


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        b = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.startswith("/health"):
            self._send(200, {"ok": True, "ready": _ip is not None,
                             "people": _people()[:300]})
        else:
            self._send(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(n) or b"{}")
            if self.path.startswith("/generate"):
                img_b64, msg, person = generate(
                    str(body.get("prompt", "")).strip(),
                    str(body.get("person", "")).strip(),
                    str(body.get("negative_prompt", "")).strip())
                if img_b64:
                    self._send(200, {"ok": True, "image_b64": img_b64,
                                     "person": person})
                else:
                    self._send(200, {"ok": False, "error": msg})
            else:
                self._send(404, {"ok": False, "error": "not found"})
        except Exception as e:
            traceback.print_exc()
            self._send(500, {"ok": False, "error": str(e)})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"Faces root : {FACES_ROOT}")
    print(f"People     : {_people()[:20]}")
    print(f"Starting Face Studio AI server on http://0.0.0.0:{PORT} …",
          flush=True)
    _load()
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
