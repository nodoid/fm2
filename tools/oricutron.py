#!/usr/bin/env python3
"""Drive Oricutron from Python on Windows.

Oricutron 1.2 has two very useful properties for automated testing:

  * F11 copies the emulated 40x28 text screen to the Windows clipboard.
  * It processes ordinary WM_KEYDOWN/WM_KEYUP messages, so keys can be
    posted straight to its window without stealing the user's focus.

This module wraps both, plus process launch.  It is used by the end-to-end
tests in tests/e2e_oricutron.py.

Usage:
    python tools/oricutron.py --tape build/fm2.tap --keys "N" --keys "1"
    python tools/oricutron.py --tape build/fm2.tap --script script.txt

A script file contains one command per line:
    wait 0.5
    key N
    keys DOWN
    shot shots/01_title.txt
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import sys
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# 64-bit safe prototypes (ctypes truncates plain ints to 32 bits).
user32.OpenClipboard.argtypes = [wt.HWND]
user32.OpenClipboard.restype = wt.BOOL
user32.CloseClipboard.restype = wt.BOOL
user32.EmptyClipboard.restype = wt.BOOL
user32.GetClipboardData.argtypes = [wt.UINT]
user32.GetClipboardData.restype = wt.HANDLE
user32.IsWindowVisible.argtypes = [wt.HWND]
user32.IsWindowVisible.restype = wt.BOOL
user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.PostMessageW.restype = wt.BOOL
user32.MapVirtualKeyW.argtypes = [wt.UINT, wt.UINT]
user32.MapVirtualKeyW.restype = wt.UINT
kernel32.GlobalLock.argtypes = [wt.HGLOBAL]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [wt.HGLOBAL]
kernel32.GlobalUnlock.restype = wt.BOOL

gdi32 = ctypes.windll.gdi32

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_CHAR = 0x0102
CF_UNICODETEXT = 13

VK = {
    "ENTER": 0x0D,
    "RETURN": 0x0D,
    "SPACE": 0x20,
    "ESC": 0x1B,
    "TAB": 0x09,
    "BACKSPACE": 0x08,
    "UP": 0x26,
    "DOWN": 0x28,
    "LEFT": 0x25,
    "RIGHT": 0x27,
    "F1": 0x70,
    "F2": 0x71,
    "F3": 0x72,
    "F4": 0x73,
    "F5": 0x74,
    "F6": 0x75,
    "F7": 0x76,
    "F8": 0x77,
    "F9": 0x78,
    "F10": 0x79,
    "F11": 0x7A,
    "F12": 0x7B,
}

# Characters whose Windows virtual-key code differs from their ASCII value.
PUNCT = {
    " ": 0x20, "!": 0x31, '"': 0xDE, "#": 0x33, "$": 0x34, "%": 0x35,
    "&": 0x37, "'": 0xDE, "(": 0x39, ")": 0x30, "*": 0x38, "+": 0xBB,
    ",": 0xBC, "-": 0xBD, ".": 0xBE, "/": 0xBF, ":": 0xBA, ";": 0xBA,
    "<": 0xBC, "=": 0xBB, ">": 0xBE, "?": 0xBF, "@": 0x32, "[": 0xDB,
    "\\": 0xDC, "]": 0xDD, "^": 0x36, "_": 0xBD, "`": 0xC0, "{": 0xDB,
    "|": 0xDC, "}": 0xDD, "~": 0xC0,
}
SHIFTED = set('!"#$%&\'()*+<>?@^_{}|~:')


def _window_for_pid(pid):
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, lparam):
        wpid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value == pid and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    user32.EnumWindows(cb, 0)
    return found[0] if found else None


def _clipboard_text():
    for _ in range(20):
        if user32.OpenClipboard(None):
            break
        time.sleep(0.05)
    else:
        raise RuntimeError("could not open clipboard")
    try:
        h = user32.GetClipboardData(CF_UNICODETEXT)
        if not h:
            return ""
        ptr = kernel32.GlobalLock(h)
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(h)
    finally:
        user32.CloseClipboard()


class Oricutron:
    def __init__(self, exe=None, tape=None, machine="atmos", workdir=None,
                 boot_wait=5.0, warp=False):
        if exe is None:
            exe = os.environ.get("ORICUTRON", "")
        if not exe or not os.path.exists(exe):
            raise SystemExit(
                "Oricutron not found. Set ORICUTRON to oricutron.exe "
                "(default: %%USERPROFILE%%\\Downloads\\Oricutron_win32_v12\\oricutron.exe)")
        self.exe = os.path.abspath(exe)
        self.workdir = workdir or os.path.dirname(self.exe)
        args = [self.exe, "--machine", machine]
        if tape:
            args += ["--tape", os.path.abspath(tape)]
        if warp:
            args += ["--turbotape", "on"]
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
            raise RuntimeError("Oricutron window did not appear")
        time.sleep(boot_wait)

    # -- low level -----------------------------------------------------
    def _key(self, vk, down):
        scan = user32.MapVirtualKeyW(vk, 0)
        if down:
            lparam = 1 | (scan << 16)
            msg = WM_KEYDOWN
        else:
            lparam = 0xC0000001 | (scan << 16)
            msg = WM_KEYUP
        user32.PostMessageW(self.hwnd, msg, vk, lparam)

    def tap(self, name, hold=0.10, gap=0.08):
        """Press and release one key (name like 'A', 'ENTER', 'F11')."""
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

    def type(self, text, hold=0.09, gap=0.09):
        for ch in text:
            self.tap(ch, hold, gap)

    def snapshot(self, path=None):
        """Return the emulated text screen (40x28) as a list of 28 strings."""
        user32.OpenClipboard(None)
        user32.EmptyClipboard()
        user32.CloseClipboard()
        self.tap("F11", hold=0.05, gap=0.05)
        text = ""
        for _ in range(30):
            text = _clipboard_text()
            if text:
                break
            time.sleep(0.1)
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if len(lines) > 1 and lines[-1] == "":
            lines.pop()
        lines = [(ln + " " * 40)[:40] for ln in lines[:28]]
        while len(lines) < 28:
            lines.append(" " * 40)
        if path:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        return lines

    def screenshot(self, path):
        """Capture the emulator window as a PNG (Windows GDI, no PIL)."""
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
        gdi32.BitBlt(memdc, 0, 0, w, h, hdc, 0, 0, 0x00CC0020)  # SRCCOPY

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
        bi.biHeight = -h            # top-down
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
        return True

    def run_script(self, commands):
        """commands: iterable of (op, arg) tuples, or a script file name."""
        for op, arg in commands:
            if op == "wait":
                time.sleep(float(arg))
            elif op == "key":
                self.tap(arg)
            elif op == "type":
                self.type(arg)
            elif op == "shot":
                self.snapshot(arg)
            elif op == "text":
                print("\n".join(self.snapshot()))

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


def _write_png(path, w, h, rgb):
    """Minimal PNG writer (8-bit RGB, no interlacing)."""
    import struct
    import zlib

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(rgb, 6))
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)


def parse_script(path):
    cmds = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            op, _, arg = line.partition(" ")
            cmds.append((op, arg.strip()))
    return cmds


def default_exe():
    base = os.environ.get("USERPROFILE", "")
    p = os.path.join(base, "Downloads", "Oricutron_win32_v12", "oricutron.exe")
    return p if os.path.exists(p) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=default_exe())
    ap.add_argument("--tape")
    ap.add_argument("--machine", default="atmos")
    ap.add_argument("--keys", action="append", default=[])
    ap.add_argument("--type", action="append", default=[])
    ap.add_argument("--shot", action="append", default=[])
    ap.add_argument("--wait", type=float, default=1.0,
                    help="seconds to wait after the last key")
    ap.add_argument("--script")
    ap.add_argument("--boot-wait", type=float, default=5.0)
    args = ap.parse_args()

    o = Oricutron(args.exe, args.tape, args.machine, boot_wait=args.boot_wait)
    try:
        if args.script:
            o.run_script(parse_script(args.script))
        for k in args.keys:
            o.tap(k)
        for t in args.type:
            o.type(t)
        time.sleep(args.wait)
        if not args.shot:
            print("\n".join(o.snapshot()))
        for s in args.shot:
            o.snapshot(s)
            print("wrote", s)
    finally:
        o.close()


if __name__ == "__main__":
    main()
