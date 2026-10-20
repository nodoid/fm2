#!/usr/bin/env python3
"""Print a captured emulator screenshot as ASCII art (no PIL needed).

Usage:
    python tools/pngascii.py build/anim/f00.png [width]
"""

import sys
import zlib
import struct


def load(path):
    d = open(path, "rb").read()
    pos = 8
    w = h = None
    idat = b""
    while pos < len(d):
        ln = struct.unpack(">I", d[pos:pos + 4])[0]
        tag = d[pos + 4:pos + 8]
        data = d[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            w, h = struct.unpack(">II", data[:8])
        elif tag == b"IDAT":
            idat += data
        pos += 12 + ln
    raw = zlib.decompress(idat)
    stride = w * 3 + 1
    rows = []
    for y in range(h):
        row = raw[y * stride + 1:(y + 1) * stride]
        rows.append([(row[x * 3] + row[x * 3 + 1] + row[x * 3 + 2]) // 3
                     for x in range(w)])
    return w, h, rows


def main():
    path = sys.argv[1]
    cols = int(sys.argv[2]) if len(sys.argv) > 2 else 80
    w, h, rows = load(path)
    if len(sys.argv) > 6:
        x0, y0, x1, y1 = (int(v) for v in sys.argv[3:7])
        rows = [r[x0:x1] for r in rows[y0:y1]]
        w, h = x1 - x0, y1 - y0
    step = max(1, w // cols)
    ramp = " .:-=+*#%@"
    for y in range(0, h, step * 2):
        line = ""
        for x in range(0, w, step):
            v = rows[y][x]
            line += ramp[min(9, v * 10 // 256)]
        print(line.rstrip())


if __name__ == "__main__":
    main()
