import base64
import io
import os
import threading

try:
    import torch
except Exception:
    torch = None

try:
    from diffusers import StableDiffusionXLImg2ImgPipeline
except Exception:
    StableDiffusionXLImg2ImgPipeline = None

try:
    from PIL import Image
except Exception:
    Image = None

_STYLE_PROMPTS = {
    "Sketch": "pencil sketch portrait, graphite texture, high detail",
    "Cartoon": "semi realistic cartoon portrait, clean outlines, smooth shading",
    "Oil Painting": "realistic oil painting portrait, painterly texture, soft brush strokes",
    "HDR": "hyper realistic portrait, high dynamic range, crisp detail",
    "Ghibli Art": "hand painted animation portrait, warm colors, soft lighting",
    "Anime": "high quality anime portrait, clean shading, detailed eyes",
    "Ghost": "ethereal portrait, translucent glow, soft haze",
    "Emboss": "embossed relief portrait, metallic highlights, realistic depth",
    "Watercolor": "watercolor portrait, soft washes, paper texture",
    "Pop Art": "pop art portrait, bold color blocks, halftone texture",
    "Neon Glow": "neon lit portrait, cyberpunk glow, vivid highlights",
    "Vintage": "vintage film portrait, muted tones, subtle grain",
    "Pixel Art": "retro pixel portrait, crisp pixel edges, limited palette",
    "Thermal": "thermal vision portrait, heatmap palette, high contrast",
    "Glitch": "glitch portrait, digital artifacts, scanline accents",
    "Pencil Color": "colored pencil portrait, fine strokes, paper texture",
}

_NEGATIVE_PROMPT = (
    "low quality, blurry, deformed, extra fingers, bad anatomy, "
    "overexposed, underexposed, watermark, text, logo"
)


def _decode_image(image_b64: str):
    if Image is None:
        raise RuntimeError("Pillow not available")
    payload = image_b64.strip()
    if payload.lower().startswith("data:image") and "," in payload:
        payload = payload.split(",", 1)[1]
    raw = base64.b64decode(payload)
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    return img


def _encode_image(img):
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return base64.b64encode(buf.getvalue()).decode("ascii")


class FaceGenerationEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self._pipe = None
        self._loaded = False

    def available(self) -> bool:
        return torch is not None and StableDiffusionXLImg2ImgPipeline is not None and Image is not None

    def _load(self):
        if self._loaded:
            return
        if not self.available():
            raise RuntimeError("diffusers/torch/Pillow not available")
        model_id = os.getenv("FACE_GEN_MODEL_ID", "stabilityai/stable-diffusion-xl-base-1.0")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32
        pipe = StableDiffusionXLImg2ImgPipeline.from_pretrained(
            model_id,
            torch_dtype=dtype,
            variant="fp16" if dtype == torch.float16 else None,
            use_safetensors=True,
        )
        if device == "cuda":
            pipe = pipe.to(device)
        pipe.enable_attention_slicing()
        lora_paths = os.getenv("FACE_GEN_LORA_PATHS", "").strip()
        if lora_paths:
            for path in [p.strip() for p in lora_paths.split(",") if p.strip()]:
                pipe.load_lora_weights(path)
        self._pipe = pipe
        self._loaded = True

    def generate(self, image_b64: str, style_name: str) -> dict:
        with self._lock:
            if not self._loaded:
                self._load()
        if self._pipe is None:
            raise RuntimeError("Generator not available")
        prompt = _STYLE_PROMPTS.get(style_name, f"realistic portrait, {style_name}")
        strength = float(os.getenv("FACE_GEN_STRENGTH", "0.35"))
        guidance = float(os.getenv("FACE_GEN_GUIDANCE", "6.5"))
        steps = int(os.getenv("FACE_GEN_STEPS", "24"))
        size = int(os.getenv("FACE_GEN_IMAGE_SIZE", "768"))
        img = _decode_image(image_b64)
        if img.width != size or img.height != size:
            img = img.resize((size, size), Image.LANCZOS)
        out = self._pipe(
            prompt=prompt,
            negative_prompt=_NEGATIVE_PROMPT,
            image=img,
            strength=strength,
            guidance_scale=guidance,
            num_inference_steps=steps,
        ).images[0]
        return {
            "filter_name": style_name,
            "image_b64": _encode_image(out),
            "width": out.width,
            "height": out.height,
        }


_ENGINE = FaceGenerationEngine()


def generate_face_variant(image_b64: str, style_name: str):
    if not _ENGINE.available():
        return None
    return _ENGINE.generate(image_b64, style_name)
