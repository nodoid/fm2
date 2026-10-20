#!/usr/bin/env python3
"""Pick ten outfield players, then put the goalkeeper over the goal.

The attack screen only offers two slots once eight outfield players are
picked, so the game takes ten outfield players and one goalkeeper.  The
goal slot may only open once the ten are in place, so this fills the
outfield first, walks back to the defence screen and then tries the
goalkeeper walks, finishing selection if one of them takes him.

Usage:
    python tests/fm2_last.py [seconds-to-watch]
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "last")
T0 = time.time()
ROWS = (4, 8, 12, 16, 20)

RULES = [
    ("PRESS 1 = KEMPSTON", ["2", "ENTER"]),
    ("PRESS FIRE", ["ENTER"]),
    ("PRESS SPACE TO CONTINUE", ["SPACE"]),
    ("MANAGE THIS TEAM", ["S", "ENTER"]),
    ("CHOOSE TEAM COLOUR", ["S", "ENTER"]),
    ("ACCEPT THE OFFER", ["S", "ENTER"]),
    ("BANK BALANCE", ["ENTER"]),
    ("SKILL LEVEL", ["ENTER"]),
    ("LOAD/SAVE GAME", ["ENTER"]),
]


def log(*a):
    print("[%6.1f]" % (time.time() - T0), *a, flush=True)


class Pad:
    def __init__(self, r, out):
        self.r = r
        self.out = out
        self.tmp = os.path.join(out, "_now.png")
        self.n = 0

    def grab(self):
        return zxcap.capture(self.r.f, self.tmp)

    def press(self, keys, gap=0.4):
        if isinstance(keys, str):
            keys = [keys]
        self.r.press(keys, gap=0.25)
        time.sleep(gap)

    def fire(self, settle=1.4):
        self.press(["ENTER"], settle)
        return self.grab()

    def save(self, s, tag):
        self.n += 1
        name = "%02d-%s" % (self.n, tag)
        with open(os.path.join(self.out, name + ".txt"), "w") as fh:
            fh.write(s.text() + "\n")
        self.r.f.screenshot(os.path.join(self.out, name + ".png"))
        return name

    def pool(self, s):
        return s.lines()[0].strip(" ?")

    def stat(self, s):
        return s.lines()[1].strip(" ?")

    def message(self, s):
        return "FIRE TO QUIT" in self.pool(s)

    def mine(self, s):
        lines = s.lines()
        return {r: lines[r][15:29].strip(" ?") for r in ROWS
                if len(lines[r][15:29].strip(" ?")) >= 3}

    def ready(self):
        s = self.grab()
        for _ in range(4):
            if not self.message(s):
                return s
            s = self.fire()
        return s

    def walk(self, n):
        for _ in range(n):
            self.press("S", 0.5)
        return self.fire()

    def next_screen(self):
        s = self.grab()
        if not self.message(s):
            s = self.fire()
        self.press("P", 1.3)
        return self.grab()

    def prev_screen(self):
        s = self.grab()
        if not self.message(s):
            s = self.fire()
        self.press("I", 1.3)
        return self.grab()

    def seek_goalkeeper(self, tries=12):
        s = self.grab()
        if not self.message(s):
            s = self.fire()
        for _ in range(tries):
            if self.stat(s).startswith("G "):
                s = self.fire()
                return s
            self.press("Q", 0.55)
            s = self.grab()
        return s

    def put(self, walk, row):
        s = self.ready()
        before = self.mine(s)
        held = "%s %s" % (self.pool(s), self.stat(s))
        s = self.walk(walk)
        after = self.mine(s)
        gained = [x for x in after if x not in before]
        lost = [x for x in before if x not in after]
        log("    walk %d (%r): gained %s lost %s" % (walk, held, gained, lost))
        if row in gained:
            return True
        if lost:
            s = self.fire()
            log("      undone, mine %s" % self.mine(s))
        return False

    def put_any(self, row, first):
        for walk in [first, first + 1, first - 1, first + 2, first - 2]:
            if walk < 1 or walk > 4:
                continue
            if row in self.mine(self.ready()):
                return True
            if self.put(walk, row):
                return True
        return False

    def put_keeper(self):
        for walk in (3, 2, 4, 5, 1):
            s = self.ready()
            s = self.seek_goalkeeper()
            if not self.stat(s).startswith("G "):
                log("    no goalkeeper on the card (%r)" % self.pool(s))
                return False
            if self.message(s):
                s = self.fire()
            before = self.mine(s)
            pool = self.pool(s)
            held = "%s %s" % (pool, self.stat(s))
            s = self.walk(walk)
            after = self.mine(s)
            lost = [x for x in before if x not in after]
            gained = [x for x in after if x not in before]
            log("    keeper walk %d (%r): gained %s lost %s, pool -> %r"
                % (walk, held, gained, lost, self.pool(s)))
            if not lost and not gained and self.pool(s) != pool:
                log("    the goalkeeper is over the goal")
                return True
            if lost:
                s = self.fire()
                log("      undone, mine %s" % self.mine(s))
        return False


def fill(p, screen, rows):
    log(screen)
    for i, row in enumerate(rows, 1):
        ok = p.put_any(row, i)
        log("  row %d: %s" % (row, "ok" if ok else "FAILED"))


def main():
    watch = int(sys.argv[1]) if len(sys.argv) > 1 else 45
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith((".png", ".txt")):
            os.remove(os.path.join(OUT, f))
    r = fm2_ref.Ref()
    p = Pad(r, OUT)

    try:
        for _ in range(90):
            s = p.grab()
            if "MANAGEMENT RECORD" in s.text():
                break
            for needle, kk in RULES:
                if needle in s.text():
                    r.press(kk)
                    break
            else:
                r.press(["SPACE"], gap=0.4)
        s = p.fire(1.6)
        for _ in range(6):
            if "OPPONENT" in s.text():
                break
            s = p.fire(1.6)
        log("team display: pool %r %r" % (p.pool(s), p.stat(s)))

        fill(p, "defence", (4, 8, 16, 20))
        p.save(p.grab(), "def-done")
        s = p.next_screen()
        fill(p, "midfield", (4, 8, 16, 20))
        p.save(p.grab(), "mid-done")
        s = p.next_screen()
        fill(p, "attack", (4, 8))
        p.save(p.grab(), "att-done")

        s = p.prev_screen()
        log("back on: pool %r %r, mine %s" % (p.pool(s), p.stat(s),
                                              p.mine(s)))
        p.save(s, "back")

        ok = p.put_keeper()
        p.save(p.grab(), "keeper")
        log("goalkeeper: %s" % ("ok" if ok else "FAILED"))

        s = p.ready()
        log("ending: pool %r %r" % (p.pool(s), p.stat(s)))
        for i in range(1, 4):
            s = p.fire(1.8)
            log("  fire %d: %r | %r" % (i, s.lines()[0].strip(" ?"),
                                        s.lines()[1].strip(" ?")))
            p.save(s, "end%d" % i)
            if not p.message(s):
                break

        log("watching %ds" % watch)
        t0 = time.time()
        last = s.text()
        while time.time() - t0 < watch:
            time.sleep(1.0)
            s = p.grab()
            if s.text() != last:
                last = s.text()
                log("  changed at +%ds:\n%s" % (time.time() - t0, s.text()))
                p.save(s, "watch%02d" % int(time.time() - t0))
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
