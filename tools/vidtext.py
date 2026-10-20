#!/usr/bin/env python3
"""OCR every Nth second of the reference video and index the text found.

    python tools/vidtext.py [--from 0] [--to 604] [--step 2] [--grep WORD]

Each sampled second is decoded with ffmpeg into a raw frame, read with
tools/vidocr.py, and its text saved under build/video/ocr/.  The index at
build/video/ocr/index.txt lists, for every sample, the first non-blank
line, so the whole playthrough can be searched without watching it.
"""

import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import vidocr                                      # noqa: E402


def ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="t0", type=float, default=0)
    ap.add_argument("--to", dest="t1", type=float, default=604)
    ap.add_argument("--step", type=float, default=2)
    ap.add_argument("--grep", default=None)
    a = ap.parse_args()

    vid = os.path.join(ROOT, "build", "video", "fm2.mp4")
    out = os.path.join(ROOT, "build", "video", "ocr")
    os.makedirs(out, exist_ok=True)
    raw = os.path.join(out, "_f.raw")
    ff = ffmpeg()

    t = a.t0
    while t <= a.t1:
        name = os.path.join(out, "%04d.txt" % int(t))
        if not os.path.exists(name):
            subprocess.run([ff, "-v", "quiet", "-ss", str(t), "-i", vid,
                            "-frames:v", "1", "-f", "rawvideo",
                            "-pix_fmt", "rgb24", raw, "-y"], check=False)
            if os.path.exists(raw) and os.path.getsize(raw) >= 1280 * 720 * 3:
                f = vidocr.Frame(raw, 1280, 720)
                text = "\n".join(f.text())
            else:
                text = ""
            with open(name, "w", encoding="utf-8") as fh:
                fh.write(text + "\n")
        with open(name, encoding="utf-8") as fh:
            text = fh.read()
        if a.grep:
            if a.grep.upper() in text.upper():
                print("=== %ds ===" % int(t))
                print(text, flush=True)
        else:
            head = " | ".join(ln for ln in text.splitlines() if ln.strip())[:160]
            print("%5ds  %s" % (int(t), head), flush=True)
        t += a.step


if __name__ == "__main__":
    main()
