#!/usr/bin/env python3
"""Capture the HIRES screens from Oricutron.

The bitmap pages have no text screen for Oricutron's F11 copy, so this
uses the emulator window instead.  Oricutron shows the 240x200 bitmap at
2x inside its 640x480 window, centred horizontally and 14 pixels down:

    window_x = 80 + 2 * x
    window_y = 14 + 2 * y

The script crops to that area and writes plain 480x400 PNGs.

    python tests/hires_shots.py            # into docs/screens
"""

import os
import struct
import sys
import time
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from oricutron import Oricutron, default_exe  # noqa: E402

BOX = (80, 14, 80 + 480, 14 + 400)


def read_png(path):
    data = open(path, "rb").read()
    pos, idat, w, h = 8, b"", 0, 0
    while pos < len(data):
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + n]
        pos += 12 + n
        if tag == b"IHDR":
            w, h = struct.unpack(">II", body[:8])
        elif tag == b"IDAT":
            idat += body
    raw = zlib.decompress(idat)
    stride = w * 3 + 1
    return w, h, [raw[y * stride + 1:(y + 1) * stride] for y in range(h)]


def write_png(path, w, h, rows):
    def chunk(tag, body):
        return (struct.pack(">I", len(body)) + tag + body +
                struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))

    out = b"\x89PNG\r\n\x1a\n"
    out += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    out += chunk(b"IDAT", zlib.compress(
        b"".join(b"\x00" + r for r in rows), 6))
    out += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(out)


def crop(src, dst):
    x0, y0, x1, y1 = BOX
    w, h, rows = read_png(src)
    out = [rows[y][x0 * 3:x1 * 3] for y in range(y0, min(y1, h))]
    write_png(dst, x1 - x0, len(out), out)
    os.remove(src)


def settle(o, timeout=40.0):
    deadline = time.time() + timeout
    prev = o.snapshot()
    same = 0
    while time.time() < deadline:
        time.sleep(0.4)
        cur = o.snapshot()
        if cur == prev and any(l.strip() for l in cur):
            same += 1
            if same >= 2:
                return cur
        else:
            same = 0
        prev = cur
    return prev


def wait_for(o, needle, timeout=60.0):
    deadline = time.time() + timeout
    lines = o.snapshot()
    while time.time() < deadline:
        if needle in "\n".join(lines):
            return settle(o)
        time.sleep(0.4)
        lines = o.snapshot()
    return lines


def shot(o, name):
    tmp = os.path.join(ROOT, "build", "shots", "_crop.png")
    o.screenshot(tmp)
    crop(tmp, os.path.join(ROOT, "docs", "screens", name))
    print("wrote docs/screens/%s" % name)


def main():
    o = Oricutron(default_exe(), os.path.join(ROOT, "build", "fm2.tap"),
                  boot_wait=5)
    try:
        o.type("CLOAD")
        o.tap('"')
        o.tap('"')
        o.tap("ENTER")
        wait_for(o, "FOOTBALL MANAGER 2", timeout=90)
        time.sleep(1.5)
        o.tap("1")
        time.sleep(1.5)
        wait_for(o, "CHOOSE YOUR CLUB", timeout=30)
        o.tap("ENTER")
        time.sleep(2.0)
        wait_for(o, "NEXT:", timeout=30)
        o.tap("2")
        time.sleep(5.0)
        shot(o, "05-team-selection.png")
        o.tap("P")
        time.sleep(3.0)
        shot(o, "06-selection-attack.png")
        o.tap("ESC")
        time.sleep(1.0)
        o.tap("6")
        time.sleep(4.0)
        shot(o, "10-match-action.png")
    finally:
        o.close()


if __name__ == "__main__":
    main()
