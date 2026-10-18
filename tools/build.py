#!/usr/bin/env python3
"""Build script for Football Manager 2 (Oric Atmos).

Examples:
    python tools/build.py game       # build build/fm2.tap      (the game)
    python tools/build.py selftest   # build build/selftest.tap (on-machine tests)
    python tools/build.py unit       # build + run the sim65 unit tests
    python tools/build.py all        # everything

The cc65 toolchain is picked up from tools/bin (see BUILD.md) or from the
CC65 environment variable / PATH.
"""

import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
TOOLS_BIN = os.path.join(ROOT, "tools", "bin")

CORE = ["src/game.c", "src/match.c"]
ASM = ["src/scr.s", "src/kbd.s", "src/snd.s", "src/sys.s"]
GAME = ["src/main.c", "src/ui.c"] + CORE + ASM + ["src/tape.s"]
SELFTEST = ["tests/test_core.c"] + CORE + ["src/ui.c"] + ASM


def tool(name):
    exe = name + (".exe" if os.name == "nt" else "")
    local = os.path.join(TOOLS_BIN, exe)
    if os.path.exists(local):
        return local
    found = shutil.which(exe)
    if found:
        return found
    sys.exit("cannot find %s - install cc65 or put it in tools/bin "
             "(see BUILD.md)" % exe)


def run(cmd, cwd=ROOT):
    print("+", " ".join(os.path.basename(c) if i == 0 else c
                        for i, c in enumerate(cmd)))
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def cl65(*args):
    return run([tool("cl65")] + list(args))


def build_game():
    os.makedirs(BUILD, exist_ok=True)
    rc = cl65("-t", "atmos", "-O", "-C", "oric.cfg",
              "-m", "build/fm2.map", "-o", "build/fm2.tap", *GAME)
    if rc == 0:
        print("built build/fm2.tap (%d bytes)" % os.path.getsize(
            os.path.join(BUILD, "fm2.tap")))
    return rc


def build_selftest():
    os.makedirs(BUILD, exist_ok=True)
    rc = cl65("-t", "atmos", "-O", "-C", "oric.cfg", "-D", "ORIC_TEST=1",
              "-I", "src", "-m", "build/selftest.map",
              "-o", "build/selftest.tap", *SELFTEST)
    if rc == 0:
        print("built build/selftest.tap (%d bytes)" % os.path.getsize(
            os.path.join(BUILD, "selftest.tap")))
    return rc


def build_unit():
    os.makedirs(BUILD, exist_ok=True)
    return cl65("-t", "sim6502", "-O", "-I", "src",
                "-o", "build/test_core.prg", "tests/test_core.c", *CORE)


def run_unit():
    rc = build_unit()
    if rc != 0:
        return rc
    sim = tool("sim65")
    print("+ sim65 build/test_core.prg")
    result = subprocess.run([sim, "build/test_core.prg"], cwd=ROOT)
    out = result.stdout
    text = out.decode("utf-8", "replace") if isinstance(out, bytes) else out
    if text:
        lines = text.splitlines()
        for line in lines:
            if "FAILED" in line or "WANTED" in line or "checks" in line:
                print(line)
    print("unit tests exit code %d" % result.returncode)
    return result.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", nargs="?", default="all",
                    choices=["game", "selftest", "unit", "all", "clean"])
    args = ap.parse_args()

    if args.what == "clean":
        if os.path.isdir(BUILD):
            for name in os.listdir(BUILD):
                if name != "shots":
                    p = os.path.join(BUILD, name)
                    shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
        return 0

    rc = 0
    if args.what in ("game", "all"):
        rc |= build_game()
    if args.what in ("selftest", "all"):
        rc |= build_selftest()
    if args.what in ("unit", "all"):
        rc |= run_unit()
    return rc


if __name__ == "__main__":
    sys.exit(main())
