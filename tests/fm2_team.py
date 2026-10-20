#!/usr/bin/env python3
"""Pick an FM2 team the way the manual describes, then watch the match.

The team selection controls, from the manual:

  * the reserve pool slot is at the top of the screen; FIRE while
    pointing at it shows FIRE TO QUIT,
  * with FIRE TO QUIT showing, UP/DOWN scroll the reserves and FIRE
    selects one, LEFT/RIGHT change the defence/midfield/attack screens
    and FIRE again ends selection once eleven players are picked,
  * the pointer walks the pitch slots with UP/DOWN, and FIRE on an empty
    slot puts the reserve shown at the top into it,
  * FIRE on a filled slot sends that player back to the reserves.

Each screen has four outfield slots; the defence screen also has the
goalkeeper's slot over the goal, three steps down.  Walking from the
pool, an outfield player's walk reaches rows 5, 9, 17 and 21, while a
goalkeeper reaches 5, 9, 13 (the goal), 17 and 21.

The display takes a couple of seconds to redraw after a placement, so
every fire is followed by a wait before the screen is read.

Usage:
    python tests/fm2_team.py [seconds-to-watch]
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "team")
T0 = time.time()

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

OUTFIELD = [5, 9, 17, 21]
KEEPER_ROW = 13


def log(*a):
    print("[%6.1f]" % (time.time() - T0), *a, flush=True)


def rows_of(s):
    """Rows whose right-hand half holds one of our player cards."""
    rows = []
    for i, ln in enumerate(s.lines()):
        k = ln.find("SK.")
        while k >= 0:
            if k >= 12:
                rows.append(i)
                break
            k = ln.find("SK.", k + 1)
    return rows


class Team:
    def __init__(self, r, out):
        self.r = r
        self.out = out
        self.tmp = os.path.join(out, "_now.png")
        self.n = 0

    def grab(self):
        s = None
        for _ in range(4):
            self.r.f.screenshot(self.tmp)
            s = zxcap.Screen(self.tmp)
            if s.ok:
                return s
            time.sleep(0.15)
        return s

    def press(self, keys, gap=0.7):
        if isinstance(keys, str):
            keys = [keys]
        self.r.press(keys, gap=0.3)
        time.sleep(gap)

    def fire(self, settle=2.2):
        self.press(["ENTER"], settle)
        return self.grab()

    def pool(self, s):
        return s.lines()[0].strip()

    def save(self, s, tag):
        self.n += 1
        name = "%02d-%s" % (self.n, tag)
        with open(os.path.join(self.out, name + ".txt"), "w") as fh:
            fh.write(s.text() + "\n")
        self.r.f.screenshot(os.path.join(self.out, name + ".png"))

    def to_pool(self):
        for _ in range(7):
            self.press("Q", 0.5)
        return self.grab()

    def idle(self):
        """Pointer on the reserve slot with FIRE TO QUIT showing."""
        s = self.to_pool()
        for _ in range(4):
            if "FIRE TO QUIT" in self.pool(s):
                return s
            s = self.fire()
        return s

    def take(self, want=None):
        """Scroll the reserves and select one; True when one is held."""
        s = self.idle()
        for _ in range(40):
            self.press("S", 0.6)
            s = self.grab()
            if want is not None:
                stat = s.lines()[1] if len(s.lines()) > 1 else ""
                if want + " SK." not in stat:
                    continue
            s = self.fire()
            if "FIRE TO QUIT" not in self.pool(s):
                return s
        return s


def main():
    watch = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith((".png", ".txt")):
            os.remove(os.path.join(OUT, f))
    r = fm2_ref.Ref()
    t = Team(r, OUT)
    total = [0]

    try:
        for _ in range(80):
            s = t.grab()
            if "MANAGEMENT RECORD" in s.text():
                break
            for needle, kk in RULES:
                if needle in s.text():
                    r.press(kk)
                    break
            else:
                r.press(["SPACE"], gap=0.4)
        s = None
        for _ in range(8):
            s = t.grab()
            if "OPPONENT" in s.text():
                break
            t.press(["ENTER"], 1.6)
        log("team display: pool %r rows %s" % (t.pool(s), rows_of(s)))

        def current_rows():
            return rows_of(t.grab())

        walk_for = {5: 1, 9: 2, 17: 3, 21: 4, KEEPER_ROW: 3}

        def fill_row(target, want=None):
            """Put a player into the slot that shows as row `target`."""
            first = walk_for.get(target, 1)
            order = [first, first + 1, first - 1, first + 2, first - 2]
            for walk in [w for w in order if 1 <= w <= 5]:
                if target in current_rows():
                    return True
                s = t.take(want)
                if "FIRE TO QUIT" in t.pool(s):
                    log("    no reserve held")
                    continue
                for _ in range(walk):
                    t.press("S", 0.5)
                before = current_rows()
                s = t.fire()
                after = rows_of(s)
                log("    walk %d: before %s after %s (pool %r)"
                    % (walk, before, after, t.pool(s)))
                if len(after) > len(before):
                    total[0] += 1
                if target in after:
                    return True
                if len(after) < len(before):
                    t.fire()                       # undo the lift
            return False

        for screen, wanted in (("DEF", OUTFIELD), ("MID", OUTFIELD),
                               ("ATT", [5, 9, 17])):
            for row in wanted:
                if total[0] >= 11:
                    break
                fill_row(row)
                t.save(t.grab(), "%s-%d" % (screen, row))
            log("%s: %d placed, rows %s" % (screen, total[0],
                                            current_rows()))
            if total[0] >= 11:
                break
            t.idle()
            t.press("P", 1.8)
            s = t.grab()
            log("  right: pool %r rows %s" % (t.pool(s), rows_of(s)))
            if rows_of(s):
                log("  still a filled screen; pressing left")
                t.idle()
                t.press("I", 1.8)
                log("  left: rows %s" % rows_of(t.grab()))

        # Back to the defence screen with a goalkeeper: the keeper's slot
        # over the goal may only open up once the outfield places are taken.
        def is_defence(s):
            return any("G SK." in s.lines()[i] for i in (12, 13, 14)
                       if i < len(s.lines()))

        for _ in range(3):
            if is_defence(t.grab()):
                break
            t.idle()
            t.press("P", 1.8)
        log("defence screen: %s rows %s" % (is_defence(t.grab()),
                                            current_rows()))
        s = t.take("G")
        log("  keeper held: %r / %r" % (s.lines()[0].strip(),
                                         s.lines()[1].strip()))
        for walk in (1, 2, 3, 4, 5):
            before = current_rows()
            for _ in range(walk):
                t.press("S", 0.5)
            s = t.fire()
            after = rows_of(s)
            log("  keeper walk %d: %s -> %s" % (walk, before, after))
            if len(after) > len(before):
                total[0] += 1
                break
            if len(after) < len(before):
                t.fire()

        t.save(t.grab(), "filled")
        log("total placed: %d" % total[0])

        s = t.idle()
        for i in range(3):
            s = t.fire(1.8)
            log("  end %d: %s | %s" % (i, " / ".join(s.lines()[:2]),
                                       t.pool(s)))
            t.save(s, "end%d" % i)
            if "OPPONENT" not in s.text():
                break
        for i in range(2):
            s = t.fire(1.8)
            log("  sub %d: %s | %s" % (i, " / ".join(s.lines()[:2]),
                                       t.pool(s)))
            t.save(s, "sub%d" % i)

        log("watching %ds" % watch)
        last = s.text()
        t.save(s, "match0")
        for i in range(watch):
            time.sleep(1.0)
            s = t.grab()
            if s.text() != last:
                last = s.text()
                log("  +%ds: %s" % (i + 1, " / ".join(s.lines()[:3])))
                t.save(s, "m%02d" % (i + 1))
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
