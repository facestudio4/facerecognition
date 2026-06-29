import os
os.environ.setdefault("HF_HOME", r"C:\face_studio_ai\hf_cache")
from huggingface_hub import hf_hub_download, snapshot_download

ROOT = r"C:\face_studio_ai"
DIFF = ["*.json", "*.txt", "*.safetensors", "**/*.json", "**/*.safetensors",
        "**/*.txt"]

print("[1/4] SD1.5 photoreal base (Realistic Vision V5.1)…", flush=True)
snapshot_download("SG161222/Realistic_Vision_V5.1_noVAE",
                  local_dir=os.path.join(ROOT, "RealisticVision"),
                  allow_patterns=DIFF)

print("[2/4] Better VAE (sd-vae-ft-mse)…", flush=True)
snapshot_download("stabilityai/sd-vae-ft-mse",
                  local_dir=os.path.join(ROOT, "sd-vae-ft-mse"),
                  allow_patterns=["*.json", "*.safetensors"])

print("[3/4] IP-Adapter FaceID PlusV2 weights…", flush=True)
for fn in ["ip-adapter-faceid-plusv2_sd15.bin",
           "ip-adapter-faceid-plusv2_sd15_lora.safetensors"]:
    hf_hub_download("h94/IP-Adapter-FaceID", fn,
                    local_dir=os.path.join(ROOT, "IP-Adapter-FaceID"))

print("[4/4] CLIP image encoder (FaceID-Plus)…", flush=True)
snapshot_download("h94/IP-Adapter",
                  allow_patterns=["models/image_encoder/*"],
                  local_dir=os.path.join(ROOT, "IP-Adapter"))

print("SD1.5 FaceID models downloaded.")
