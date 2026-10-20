#!/usr/bin/env python3
"""Watch a video without seeing it: print ASCII thumbnails of its screens.

A reference video is the only description of some screens, and this
reader has no eyes, so the video is decoded with ffmpeg into raw frames
and every frame is turned into a small brightness map.  A frame whose map
differs enough from the last one printed is shown as text art, which is
enough to tell a drawn pitch, a grid of cards or a page of text apart.

    python tools/vidscan.py build/video/fm2.mp4 [--fps 1] [--every SEC]
        [--cols 96] [--diff 6] [--from SEC] [--to SEC]
"""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


SHADES = " .:-=+*#%@"

# Palette letters for --colour: hue, with capital meaning bright.
COLOURS = [(0, 0, 0, "k"), (0, 0, 255, "b"), (255, 0, 0, "r"),
           (255, 0, 255, "m"), (0, 255, 0, "g"), (0, 255, 255, "c"),
           (255, 255, 0, "y"), (255, 255, 255, "w")]


def colour_letter(r, g, b, bright):
    if r + g + b < 90:
        return "."
    best = min(COLOURS, key=lambda c: (c[0] - r) ** 2 + (c[1] - g) ** 2 +
               (c[2] - b) ** 2)
    ch = best[3]
    return ch.upper() if bright else ch


def colour_thumbnail(px, w, h, cols):
    """Mean colour per block, as palette letters (brightness = capital)."""
    rows = max(1, cols * h // w // 2)
    out = []
    for ry in range(rows):
        y0 = ry * h // rows
        y1 = max(y0 + 1, (ry + 1) * h // rows)
        line = []
        for rx in range(cols):
            x0 = rx * w // cols
            x1 = max(x0 + 1, (rx + 1) * w // cols)
            n = r = g = b = 0
            for y in range(y0, y1):
                base = y * w * 3
                for x in range(x0, x1):
                    i = base + x * 3
                    r += px[i]
                    g += px[i + 1]
                    b += px[i + 2]
                    n += 1
            r, g, b = r // n, g // n, b // n
            line.append(colour_letter(r, g, b, (r + g + b) > 400))
        out.append(line)
    return out


def thumbnail(px, w, h, cols):
    """Mean brightness per block, as a small 2-D list of 0..len(SHADES)."""
    rows = max(1, cols * h // w // 2)
    out = []
    for ry in range(rows):
        y0 = ry * h // rows
        y1 = max(y0 + 1, (ry + 1) * h // rows)
        line = []
        for rx in range(cols):
            x0 = rx * w // cols
            x1 = max(x0 + 1, (rx + 1) * w // cols)
            n = 0
            s = 0
            for y in range(y0, y1):
                base = y * w * 3
                for x in range(x0, x1):
                    i = base + x * 3
                    s += px[i] + px[i + 1] + px[i + 2]
                    n += 3
            line.append(s // (n * 26) if n else 0)
        out.append(line)
    return out


def render(thumb):
    if thumb and isinstance(thumb[0][0], str):
        return "\n".join("".join(row) for row in thumb)
    return "\n".join("".join(SHADES[min(len(SHADES) - 1, v)] for v in row)
                     for row in thumb)


def diff(a, b):
    def val(v):
        return SHADES.index(v) * 10 if isinstance(v, str) and v in SHADES \
            else v

    n = sum(abs(val(x) - val(y))
            for ra, rb in zip(a, b) for x, y in zip(ra, rb))
    cells = sum(len(r) for r in a)
    return n / max(1, cells)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--fps", type=float, default=1.0)
    ap.add_argument("--every", type=float, default=0.0,
                    help="also print every SEC seconds")
    ap.add_argument("--cols", type=int, default=96)
    ap.add_argument("--diff", type=float, default=4.0,
                    help="mean brightness change that counts as a new screen")
    ap.add_argument("--from", dest="start", type=float, default=0.0)
    ap.add_argument("--to", dest="stop", type=float, default=1e9)
    ap.add_argument("--size", default="960x540")
    ap.add_argument("--colour", action="store_true")
    ap.add_argument("--stats", action="store_true",
                    help="one line per frame: colour shares, not pictures")
    ap.add_argument("--crop", default=None,
                    help="x:y:w:h inside the frame, applied by ffmpeg")
    args = ap.parse_args()

    w, h = (int(v) for v in args.size.split("x"))
    cmd = [ffmpeg(), "-hide_banner", "-loglevel", "error"]
    if args.start:
        cmd += ["-ss", str(args.start)]
    vf = "fps=%g" % args.fps
    if args.crop:
        x, y, cw, ch = (int(v) for v in args.crop.split(":"))
        vf += ",crop=%d:%d:%d:%d" % (cw, ch, x, y)
        w, h = cw, ch
    vf += ",scale=%dx%d" % (w, h)
    cmd += ["-i", args.video, "-vf", vf,
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    if args.stop < 1e8:
        cmd += []
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=10 ** 8)
    size = w * h * 3
    n = 0
    last = None
    last_sig = None
    last_shown = -1e9
    try:
        while True:
            px = proc.stdout.read(size)
            if len(px) < size:
                break
            t = args.start + n / args.fps
            n += 1
            if t < args.start or t > args.stop:
                continue
            if args.stats:
                counts = {}
                npx = w * h
                for i in range(0, len(px), 3):
                    r, g, b = px[i], px[i + 1], px[i + 2]
                    k = colour_letter(r, g, b, (r + g + b) > 400).lower()
                    counts[k] = counts.get(k, 0) + 1
                share = " ".join("%s%2d" % (k, 100 * counts.get(k, 0) // npx)
                                 for k in "kwrgbcmy")
                sig = " ".join(str(counts.get(k, 0) * 20 // npx)
                               for k in "kwrgbcmy")
                if sig != last_sig:
                    print("%6.1fs %s" % (t, share), flush=True)
                    last_sig = sig
                continue
            grey = thumbnail(px, w, h, args.cols)
            th = (colour_thumbnail(px, w, h, args.cols) if args.colour
                  else grey)
            d = 100.0 if last is None else diff(grey, last)
            show = d >= args.diff or t - last_shown >= args.every > 0
            if show:
                print("=== %6.1fs  (change %.1f) ===" % (t, d), flush=True)
                print(render(th), flush=True)
                last_shown = t
            last = grey
    finally:
        proc.stdout.close()
        proc.wait()


if __name__ == "__main__":
    main()
