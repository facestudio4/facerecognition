from __future__ import annotations

from pathlib import Path
import cv2


def save_frames(video_path: Path, out_dir: Path, times_sec: list[float]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    for t in times_sec:
        frame_idx = int(round(t * fps))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        out_path = out_dir / f"t_{t:.2f}s.png"
        cv2.imwrite(str(out_path), frame)

    cap.release()


if __name__ == "__main__":
    root = Path(r"c:\Users\shishir\OneDrive\Documents\Python\facerecognition")
    src = root / "error photos"

    wrong = src / "Android Emulator - Medium_Phone_API_36.1_5554 2026-04-13 00-04-31.mp4"
    correct = src / "Android Emulator - Medium_Phone_API_36.1_5554 2026-04-13 00-05-46.mp4"

    # Capture key states: assemble start, mid-form, hold, travel/settle
    marks = [0.20, 0.80, 1.40, 2.20, 3.00, 4.20]

    save_frames(wrong, src / "frames_wrong", marks)
    save_frames(correct, src / "frames_correct", marks)
