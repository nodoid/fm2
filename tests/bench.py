#!/usr/bin/env python3
"""Cycle benchmark for the match screen.

    python tests/bench.py [--save NAME]

Builds tests/bench_draw.c for sim65 and runs each workload with
`sim65 --cycles`, so the numbers are exact CPU cycles rather than wall
clock.  Prints the raw runs and the costs derived from them; with --save
the numbers are also written to build/bench/NAME.json for comparison.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
TOOLS = os.path.join(ROOT, "tools", "bin")


def tool(name):
    exe = name + (".exe" if os.name == "nt" else "")
    path = os.path.join(TOOLS, exe)
    return path if os.path.exists(path) else name


SOURCES = ["tests/bench_draw.c", "src/action.c", "src/game.c",
           "src/match.c", "src/hires.c", "src/hires.s", "src/font.s"]

MODES = {0: "setup + pitch", 1: "+8 frames", 2: "+3 camera changes",
         3: "+200x152 row lines", 4: "+100x15 erase rows",
         5: "+20 screen clears", 6: "+20 pitch repaints",
         7: "+40 sets of markings", 8: "+20 header bands",
         9: "+100 nine letter strings"}


def build():
    os.makedirs(BUILD, exist_ok=True)
    exe = os.path.join(BUILD, "bench_draw.prg")
    cmd = [tool("cl65"), "-t", "sim6502", "-O", "-I", "src", "-o", exe] + SOURCES
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        sys.exit("build failed")
    return exe


def cycles(exe, mode):
    result = subprocess.run([tool("sim65"), "--cycles", exe, str(mode)],
                            cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit("sim65 failed for mode %d: %s" % (mode, result.stderr))
    for line in result.stdout.splitlines():
        if line.strip().endswith("cycles"):
            return int(line.split()[0])
    sys.exit("no cycle count for mode %d" % mode)


def main():
    exe = build()
    runs = {m: cycles(exe, m) for m in MODES}
    base = runs[0]
    print("mode                                 cycles      delta")
    for m, label in MODES.items():
        print("%-32s %10d %10d" % (label, runs[m], runs[m] - base))

    steps = 8 * 9
    print()
    print("per animation step          %8d cycles  (%4.1f frames)"
          % ((runs[1] - base) // steps, (runs[1] - base) / steps / 20000.0))
    print("per camera repaint          %8d cycles  (%4.1f frames)"
          % ((runs[2] - base) // 3, (runs[2] - base) / 3 / 20000.0))
    print("header crowd band           %8d cycles"
          % ((runs[8] - base) // 20))
    print("nine letter string          %8d cycles"
          % ((runs[9] - base) // 100))
    print("one full-width line call    %8d cycles"
          % ((runs[3] - base) // (200 * 152)))
    print("one 9x15 erase box          %8d cycles"
          % ((runs[4] - base) // 100))
    print("screen clear                %8d cycles  (%4.1f frames)"
          % ((runs[5] - base) // 20, (runs[5] - base) / 20 / 20000.0))
    print("pitch repaint               %8d cycles  (%4.1f frames)"
          % ((runs[6] - base) // 20, (runs[6] - base) / 20 / 20000.0))
    print("markings (any view)         %8d cycles"
          % ((runs[7] - base) // 40))

    if "--save" in sys.argv:
        name = sys.argv[sys.argv.index("--save") + 1]
        path = os.path.join(BUILD, "bench", name + ".json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as out:
            json.dump(runs, out, indent=2)
        print("\nsaved", os.path.relpath(path, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
