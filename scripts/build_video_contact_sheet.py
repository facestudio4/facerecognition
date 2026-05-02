from __future__ import annotations

from pathlib import Path
import math
import cv2
import numpy as np


def make_sheet(video_path: Path, out_png: Path, sample_step_sec: float = 1.0) -> None:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 24.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps else 0.0

    times = []
    t = 0.0
    while t < duration:
        times.append(round(t, 2))
        t += sample_step_sec

    thumbs = []
    for t in times:
        idx = int(round(t * fps))
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        frame = cv2.resize(frame, (220, 390), interpolation=cv2.INTER_AREA)
        cv2.putText(
            frame,
            f"t={t:.1f}s",
            (8, 26),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        thumbs.append(frame)

    cap.release()

    if not thumbs:
        raise RuntimeError(f"No frames extracted for {video_path}")

    cols = 4
    rows = math.ceil(len(thumbs) / cols)
    cell_w, cell_h = 220, 390
    header_h = 60

    sheet = np.full((header_h + rows * cell_h, cols * cell_w, 3), 22, dtype=np.uint8)
    title = f"{video_path.name} | dur={duration:.2f}s | fps={fps:.2f}"
    cv2.putText(sheet, title, (12, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (220, 220, 220), 2, cv2.LINE_AA)

    for i, img in enumerate(thumbs):
        r = i // cols
        c = i % cols
        y0 = header_h + r * cell_h
        x0 = c * cell_w
        sheet[y0:y0 + cell_h, x0:x0 + cell_w] = img

    out_png.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_png), sheet)


if __name__ == "__main__":
    root = Path(r"c:\Users\shishir\OneDrive\Documents\Python\facerecognition\error photos")
    wrong_video = root / "Android Emulator - Medium_Phone_API_36.1_5554 2026-04-13 00-04-31.mp4"
    correct_video = root / "Android Emulator - Medium_Phone_API_36.1_5554 2026-04-13 00-05-46.mp4"

    make_sheet(wrong_video, root / "sheet_wrong.png", sample_step_sec=1.0)
    make_sheet(correct_video, root / "sheet_correct.png", sample_step_sec=1.0)
