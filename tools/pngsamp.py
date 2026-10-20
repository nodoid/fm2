#!/usr/bin/env python3
"""Sample an Oric screenshot as a 240x200 HIRES grid.

    python tools/pngsamp.py build/action.png            # ASCII, 2x1
    python tools/pngsamp.py build/action.png --box 80,14,560,414

The emulator window shows the bitmap at 2x inside 640x480, at (80, 14).
"""

import struct
import sys
import zlib


def read_png(path):
    data = open(path, "rb").read()
    pos, idat, w, h, ct = 8, b"", 0, 0, 2
    while pos < len(data):
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + n]
        pos += 12 + n
        if tag == b"IHDR":
            w, h = struct.unpack(">II", body[:8])
            ct = body[9]
        elif tag == b"IDAT":
            idat += body
    raw = zlib.decompress(idat)
    bpp = 3 if ct == 2 else 4 if ct == 6 else 1
    stride = w * bpp
    rows, prev, i = [], bytearray(stride), 0
    for _ in range(h):
        f = raw[i]
        i += 1
        line = bytearray(raw[i:i + stride])
        i += stride
        if f == 1:
            for x in range(bpp, stride):
                line[x] = (line[x] + line[x - bpp]) & 255
        elif f == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 255
        elif f == 3:
            for x in range(stride):
                left = line[x - bpp] if x >= bpp else 0
                line[x] = (line[x] + ((left + prev[x]) >> 1)) & 255
        elif f == 4:
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0
                b = prev[x]
                c = prev[x - bpp] if x >= bpp else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        rows.append(line)
        prev = line
    return w, h, bpp, rows


def sample(path, box="80,14,560,414"):
    x0, y0, x1, y1 = (int(v) for v in box.split(","))
    w, h, bpp, rows = read_png(path)
    x1, y1 = min(x1, w), min(y1, h)
    grid = []
    for y in range(200):
        sy = y0 + (y1 - y0) * y // 200
        line = []
        for x in range(240):
            sx = x0 + (x1 - x0) * x // 240
            line.append(1 if rows[sy][sx * bpp] > 128 else 0)
        grid.append(line)
    return grid


def art(grid, step=2):
    for y in range(0, 200, step):
        print("%3d %s" % (y, "".join(
            "#" if grid[y][x] else "." for x in range(0, 240, step))))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    box = "80,14,560,414"
    for a in sys.argv[1:]:
        if a.startswith("--box"):
            box = a.split("=", 1)[1] if "=" in a else box
    step = 2
    for a in sys.argv[1:]:
        if a.startswith("--step="):
            step = int(a.split("=", 1)[1])
    art(sample(args[0], box), step)


if __name__ == "__main__":
    main()
