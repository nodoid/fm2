#!/usr/bin/env python3
"""Pick all eleven FM2 players, then follow the game into the match.

Every placement is checked against the card rows, because a single lost or
doubled DOWN press shifts the whole walk.  A failed attempt is undone with
FIRE on the same slot and retried one stop either side.

The goalkeeper goes three stops down from the reserve card, into the slot
over the goal.  That slot is drawn apart from the four outfield card rows,
so a keeper placement shows up as the reserve card moving on with no card
gained and none lost.

Usage:
    python tests/fm2_eleven.py [seconds-to-watch]
"""

import hashlib
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "eleven")
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
            fh.write(s.text() + "\n\n" + "\n".join(s.colours()) + "\n")
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

    # -- placement with verification -----------------------------------
    def put(self, walk, row):
        s = self.ready()
        before = self.mine(s)
        pool = self.pool(s)
        held = "%s %s" % (self.pool(s), self.stat(s))
        s = self.walk(walk)
        after = self.mine(s)
        gained = [x for x in after if x not in before]
        lost = [x for x in before if x not in after]
        log("    walk %d (%r): gained %s lost %s" % (walk, held, gained, lost))
        if row in gained:
            return True
        if lost:
            s = self.fire()          # put him back
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

    def put_keeper(self, first=3):
        for walk in [first, first + 1, first - 1, first + 2, first - 2]:
            if walk < 1 or walk > 5:
                continue
            s = self.ready()
            s = self.seek_goalkeeper()
            if not self.stat(s).startswith("G "):
                log("    no goalkeeper in the reserves")
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
            moved = self.pool(s) != pool
            log("    keeper walk %d (%r): gained %s lost %s, pool -> %r"
                % (walk, held, gained, lost, self.pool(s)))
            if not lost and not gained and moved:
                log("    goalkeeper is over the goal")
                return True
            if lost:
                s = self.fire()
                log("      undone, mine %s" % self.mine(s))
        return False


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
        log("record screen")

        s = p.fire(1.6)
        for _ in range(6):
            if "OPPONENT" in s.text():
                break
            s = p.fire(1.6)
        log("team display: pool %r %r" % (p.pool(s), p.stat(s)))

        log("defence")
        for i, row in enumerate((4, 8, 16, 20), 1):
            ok = p.put_any(row, i)
            log("  row %d: %s, mine %s" % (row, "ok" if ok else "FAILED",
                                           p.mine(p.grab())))
            p.save(p.grab(), "def-%d" % i)

        log("midfield")
        s = p.next_screen()
        log("  screen: pool %r %r" % (p.pool(s), p.stat(s)))
        p.save(s, "mid")
        for i, row in enumerate((4, 8, 16, 20), 1):
            ok = p.put_any(row, i)
            log("  row %d: %s, mine %s" % (row, "ok" if ok else "FAILED",
                                           p.mine(p.grab())))
            p.save(p.grab(), "mid-%d" % i)

        log("attack")
        s = p.next_screen()
        log("  screen: pool %r %r" % (p.pool(s), p.stat(s)))
        p.save(s, "att")
        for i, row in enumerate((4, 8, 16), 1):
            ok = p.put_any(row, i)
            log("  row %d: %s, mine %s" % (row, "ok" if ok else "FAILED",
                                           p.mine(p.grab())))
            p.save(p.grab(), "att-%d" % i)

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
        last = hashlib.md5(s.text().encode()).hexdigest()
        while time.time() - t0 < watch:
            time.sleep(1.0)
            s = p.grab()
            t = hashlib.md5(s.text().encode()).hexdigest()
            if t != last:
                last = t
                log("  changed at +%ds:\n%s" % (time.time() - t0, s.text()))
                p.save(s, "watch%02d" % int(time.time() - t0))
        p.save(s, "final")
        log("final:\n" + s.text())
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
