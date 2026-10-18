# Football Manager 2 — Oric Atmos port

A from-scratch port of **Football Manager 2** (Addictive Software, 1988,
by Kevin Toms) to the Tangerine Oric Atmos.  The game is written in C
with 6502 assembly for everything that touches the hardware, and runs on
a real 1 MHz Oric or in Oricutron.

It follows the Spectrum sequel rather than the 1982 original:

* **Four divisions of twenty clubs** (80 clubs), one meeting with every
  other club, three up and three down at the end of the season.  You
  start in Division 4.
* **FM2 player attributes** — name, position (G/D/M/A), skill 3–9 and
  value in thousands, plus fitness out of 100.  A player used out of
  position counts as skill 2.
* **Twelve outfield zones** laid out over defence, midfield and attack.
  You place ten outfield players into those zones, so a 4-4-2, 4-3-3 or
  4-2-4 falls out of where you put them; leaving a zone empty gives the
  opposition space, filling it marks their man.
* **Passing-height and passing-length training**, as in the original.
* **The action**: the match is played out as a series of animated
  sequences on a text-mode pitch, with the ball, a running scoreboard
  and one-line commentary, and a half-time team talk where you can
  change the side.
* **Two cups** — the FA Cup and the League Cup — drawn as 32-club
  knockouts during the season.
* Sponsorship, gate receipts, wages, board confidence, the manager's
  record, and cassette save/load.

## Screens

![Title screen](docs/screens/01-title.png)

| | |
|---|---|
| ![Management screen](docs/screens/03-office.png) | ![Team display](docs/screens/04-team-display.png) |
| ![Team selection](docs/screens/05-team-selection.png) | ![Training](docs/screens/07-training.png) |
| ![League table](docs/screens/08-league-table.png) | ![Finance](docs/screens/09-finance.png) |

![Match action](docs/screens/10-match-action.png)

Regenerate them at any time with `python tests/make_screenshots.py`.

## Controls

| Key | Action |
|-----|--------|
| `Q` / `A` (or 8 / 2) | up / down |
| `I` / `P` | left / right, and the defence/midfield/attack views |
| `ENTER` | confirm |
| `SPACE` | clear a zone, advance the action |
| `A`–`P` | pick a squad player in team selection |
| `H` / `L` | passing height / length in training |
| `ESC` | back |

## Building

The build uses [cc65](https://cc65.github.io/); see [BUILD.md](BUILD.md).

```
python tools/build.py all       # game, self-test tape and the unit tests
python tools/build.py game      # build/fm2.tap
python tools/build.py unit      # sim65 unit tests
```

`build/fm2.tap` autostarts: `CLOAD""` in BASIC and the game is running.

## Testing

* **Unit tests** (`tests/test_core.c`) run on the host under `sim65` and
  cover the fixture generator, the tables, the zone selection, the
  action engine, the cups, transfers, finances and save/restore.
* **On-machine self test** (`build/selftest.tap`) runs the same tests on
  the real 6502 and prints the results on screen.
* **End-to-end tests** (`tests/e2e_oricutron.py`) drive the real game in
  Oricutron, typing on its keyboard and reading the 40x28 text screen
  back through the emulator's clipboard copy.

```
python tools/build.py all
python tests/e2e_oricutron.py            # the game
python tests/e2e_oricutron.py --selftest # the on-machine tests
```

## Source layout

| File | What it does |
|------|--------------|
| `src/game.c` | divisions, round-robin fixtures, tables, squads, zones, cups, finances, save block |
| `src/match.c` | the action engine: possession, passes, tackles, shots, goals, half time |
| `src/main.c` | every screen and the game flow |
| `src/ui.c` | line builder, page furniture, the text-mode pitch |
| `src/scr.s` | 40x28 text driver (cursor, strings, attributes, inverse video) |
| `src/kbd.s` | 50 Hz interrupt-driven keyboard scanner and key queue |
| `src/snd.s` | AY-3-8912 clicks, goal jingle and whistle |
| `src/tape.s` | cassette save/load through the Atmos ROM routines |
| `src/sys.s` | soft reset back to BASIC |
| `oric.cfg` | ld65 config: autostart tape header, 1K stack |

## Notes on the port

* The text screen at `$BB80` is written directly; serial attributes give
  the coloured bars.
* The keyboard is scanned from the 50 Hz VIA interrupt, so a key pressed
  while a screen is being drawn is still waiting when the menu returns
  for input.
* Fixtures are generated arithmetically (circle method) rather than
  stored, which keeps the game inside 37K of RAM.
* Football Manager 2 is a trademark of Addictive Software; this is an
  unofficial tribute port, written from scratch.
