#!/usr/bin/env python3
"""Drive Fuse (ZX Spectrum) from Python on Windows.

Same approach as tools/oricutron.py: post WM_KEYDOWN/WM_KEYUP to the
emulator window and grab the window bitmap with GDI, so the reference
Spectrum game can be inspected without taking over the user's desktop.

Usage:
    python tools/fuse.py --tape ref/FOOTMNG2.TAP --shot ref/title.png
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oricutron import (_window_for_pid, _write_png, VK, PUNCT,  # noqa: E402
                       SHIFTED, user32, gdi32)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Fuse:
    def __init__(self, exe=None, tape=None, machine="48", speed=None,
                 boot_wait=4.0, autoload=True):
        if exe is None:
            exe = os.environ.get("FUSE") or os.path.join(
                ROOT, "tools", "fuse", "fuse.exe")
        if not os.path.exists(exe):
            raise SystemExit("Fuse not found: %s" % exe)
        self.exe = os.path.abspath(exe)
        self.workdir = os.path.dirname(self.exe)
        args = [self.exe, "--machine", machine, "--traps", "--no-sound"]
        if speed:
            args += ["--speed", str(speed)]
        if tape:
            args += ["--tape", os.path.abspath(tape)]
        if autoload:
            args += ["--auto-load"]
        self.proc = subprocess.Popen(args, cwd=self.workdir)
        self.hwnd = None
        deadline = time.time() + 15
        while time.time() < deadline:
            self.hwnd = _window_for_pid(self.proc.pid)
            if self.hwnd:
                break
            time.sleep(0.1)
        if not self.hwnd:
            self.close()
            raise RuntimeError("Fuse window did not appear")
        time.sleep(boot_wait)

    # -- input ---------------------------------------------------------
    def _key(self, vk, down):
        scan = user32.MapVirtualKeyW(vk, 0)
        if down:
            user32.PostMessageW(self.hwnd, 0x0100, vk, 1 | (scan << 16))
        else:
            user32.PostMessageW(self.hwnd, 0x0101, vk,
                                0xC0000001 | (scan << 16))

    def tap(self, name, hold=0.12, gap=0.12):
        if name.upper() in VK:
            vk = VK[name.upper()]
            shift = False
        else:
            ch = name
            vk = PUNCT.get(ch)
            if vk is None:
                vk = ord(ch.upper())
            shift = ch in SHIFTED
        if shift:
            self._key(0x10, True)
        self._key(vk, True)
        time.sleep(hold)
        self._key(vk, False)
        if shift:
            time.sleep(0.03)
            self._key(0x10, False)
        time.sleep(gap)

    def type(self, text, hold=0.1, gap=0.1):
        for ch in text:
            self.tap(ch, hold, gap)

    # -- output --------------------------------------------------------
    def screenshot(self, path):
        # Fuse renders through SDL2, so the window has to be on top for a
        # GDI grab to see it.  Put it there, capture, then hand focus back.
        prev = user32.GetForegroundWindow()
        user32.BringWindowToTop(self.hwnd)
        user32.SetForegroundWindow(self.hwnd)
        time.sleep(0.35)

        rect = wt.RECT()
        user32.GetClientRect(self.hwnd, ctypes.byref(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w <= 0 or h <= 0:
            return False
        hdc = user32.GetDC(self.hwnd)
        memdc = gdi32.CreateCompatibleDC(hdc)
        bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
        gdi32.SelectObject(memdc, bmp)
        gdi32.BitBlt(memdc, 0, 0, w, h, hdc, 0, 0, 0x00CC0020)

        class BIH(ctypes.Structure):
            _fields_ = [
                ("biSize", wt.DWORD), ("biWidth", wt.LONG),
                ("biHeight", wt.LONG), ("biPlanes", wt.WORD),
                ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", wt.LONG),
                ("biYPelsPerMeter", wt.LONG), ("biClrUsed", wt.DWORD),
                ("biClrImportant", wt.DWORD),
            ]

        bi = BIH()
        bi.biSize = ctypes.sizeof(BIH)
        bi.biWidth = w
        bi.biHeight = -h
        bi.biPlanes = 1
        bi.biBitCount = 32
        bi.biCompression = 0
        buf = ctypes.create_string_buffer(w * h * 4)
        gdi32.GetDIBits(memdc, bmp, 0, h, buf, ctypes.byref(bi), 0)

        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(memdc)
        user32.ReleaseDC(self.hwnd, hdc)

        raw = buf.raw
        rows = []
        for y in range(h):
            row = raw[y * w * 4:(y + 1) * w * 4]
            rows.append(b"\x00" + bytes(
                b for i in range(w)
                for b in (row[i * 4 + 2], row[i * 4 + 1], row[i * 4])))
        _write_png(path, w, h, b"".join(rows))
        try:
            if prev and prev != self.hwnd:
                user32.SetForegroundWindow(prev)
        except Exception:
            pass
        return True

    def close(self):
        try:
            if self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tape", default=os.path.join(ROOT, "ref", "FOOTMNG2.TAP"))
    ap.add_argument("--wait", type=float, default=8.0)
    ap.add_argument("--keys", action="append", default=[])
    ap.add_argument("--shot", default="ref/fuse-shot.png")
    args = ap.parse_args()

    f = Fuse(tape=args.tape, speed=400)
    try:
        time.sleep(args.wait)
        for k in args.keys:
            f.tap(k)
        time.sleep(1.0)
        f.screenshot(args.shot)
        print("wrote", args.shot)
    finally:
        f.close()


if __name__ == "__main__":
    main()
