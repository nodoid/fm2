#!/usr/bin/env python3
"""Coarse colour map of a PNG, for eyeballing reference screenshots."""
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
    bpp = 3 if ct == 2 else 4
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


def klass(r, g, b):
    if r < 60 and g < 60 and b < 60:
        return "."
    if r > 200 and g > 200 and b > 200:
        return "#"
    if g > 120 and r < 120 and b < 120:
        return "G"
    if r > 120 and g > 120 and b < 100:
        return "Y"
    if r > 120 and g < 100 and b < 100:
        return "R"
    if b > 120 and g > 120 and r < 120:
        return "C"
    if b > 120 and r < 100:
        return "B"
    if r > 100 and b > 100:
        return "M"
    return "o"


def main():
    step = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    w, h, bpp, rows = read_png(sys.argv[1])
    print("%dx%d bpp=%d" % (w, h, bpp))
    for y in range(0, h, step):
        print("".join(klass(rows[y][x * bpp], rows[y][x * bpp + 1],
                            rows[y][x * bpp + 2])
                      for x in range(0, w, step)))


if __name__ == "__main__":
    main()
