#!/usr/bin/env python3
"""Render an 8000-byte Oric HIRES bitmap dump.

    python tools/hiresview.py build/hires.bin            # ASCII
    python tools/hiresview.py build/hires.bin out.png    # PNG

Each byte holds six pixels, bit 5 leftmost; bit 6 must be set for a
pixel byte.  The bitmap is 40 bytes per scanline, 200 lines.
"""

import struct
import sys
import zlib


def px(data, x, y):
    b = data[y * 40 + x // 6]
    if not (b & 0x40):
        return 0
    return 1 if (b & (0x20 >> (x % 6))) else 0


def ascii_art(data, step=2):
    for y in range(0, 200, step):
        line = []
        for x in range(0, 240, step):
            line.append("#" if px(data, x, y) else ".")
        print("%3d %s" % (y, "".join(line)))


def png(data, path, scale=3):
    w = 240 * scale
    h = 200 * scale
    rows = []
    for y in range(h):
        row = bytearray(b"\x00")
        for x in range(w):
            v = 255 if px(data, x // scale, y // scale) else 0
            row += bytes((v, v, v))
        rows.append(bytes(row))

    def chunk(tag, body):
        return (struct.pack(">I", len(body)) + tag + body +
                struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))

    out = b"\x89PNG\r\n\x1a\n"
    out += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    out += chunk(b"IDAT", zlib.compress(b"".join(rows), 6))
    out += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(out)


def main():
    data = open(sys.argv[1], "rb").read()
    if len(data) < 8000:
        sys.exit("%s is %d bytes, want 8000" % (sys.argv[1], len(data)))
    if len(sys.argv) > 2:
        png(data, sys.argv[2])
        print("wrote", sys.argv[2])
    else:
        ascii_art(data)


if __name__ == "__main__":
    main()
