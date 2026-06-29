# Personal AI server (real‑face generation on your own GPU)

Generates a **realistic image with a real person's face baked in** (InstantID‑style
identity, via SD1.5 + IP‑Adapter‑FaceID‑PlusV2). Runs on your PC's GPU so it's free
and private. The mobile app calls it when a prompt names someone in your face DB.

## Why local
Realistic, *properly blended* personalized generation needs an identity‑conditioned
diffusion model. That needs a GPU — it can't run on the free Render backend. SDXL
InstantID needs ~12 GB; on an 8 GB card we use the lighter **SD1.5 + FaceID**
(fits ~4 GB, ~10–16 s/image).

## One‑time setup (Windows, NVIDIA GPU)
Installed under `C:\face_studio_ai\` (kept out of OneDrive). Steps that were run:

```powershell
# Python 3.12 venv (3.14 is too new for the ML stack)
py -3.12 -m venv C:\face_studio_ai\venv
C:\face_studio_ai\venv\Scripts\pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
C:\face_studio_ai\venv\Scripts\pip install "diffusers==0.27.2" "transformers==4.40.2" "huggingface_hub==0.25.2" accelerate safetensors einops opencv-python onnxruntime insightface==0.7.3
# IP-Adapter code -> C:\face_studio_ai\ipa\ip_adapter\  (from github.com/tencent-ailab/IP-Adapter)
# models -> python download_sd15.py   (Realistic Vision SD1.5 + sd-vae-ft-mse + IP-Adapter-FaceID + image_encoder)
```

`server.py` and `download_sd15.py` here are copies for reference; the live ones live
in `C:\face_studio_ai\`.

## Daily use
1. Double‑click **`C:\face_studio_ai\Start Face Studio AI.bat`** (keep the window open).
2. In the app → Face Generation → "Personal AI (your PC)" field, enter your PC's
   address, e.g. `http://192.168.1.5:7860` (phone must be on the same Wi‑Fi).
3. Describe an image that **names a person** in your face DB (e.g. "vraj playing
   with a dog") → the app routes it to your PC for the real‑face result. When the
   PC/server is off, it falls back to the free cloud generator.

## API
- `GET  /health` → `{ ok, ready, people:[...] }`
- `POST /generate` `{ prompt, person, negative_prompt? }` → `{ ok, image_b64, person }`

## Remote access (optional)
Same‑Wi‑Fi uses the LAN IP above. To reach it from anywhere, run a tunnel
(e.g. `cloudflared tunnel --url http://localhost:7860`) and paste that https URL
into the app's Personal AI field instead.
