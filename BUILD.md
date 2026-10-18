# Building Football Manager 2 for the Oric

## What you need

| Tool | Purpose |
|------|---------|
| [cc65](https://cc65.github.io/) 2.19+ | C compiler, assembler, linker (`cl65`) and the 6502 simulator (`sim65`) |
| Python 3.8+ | build driver and the Oricutron test harness |
| [Oricutron](https://github.com/pete-gordon/oricutron) | the emulator used by the end-to-end tests |

The build script looks for the toolchain in `tools/bin` first, then on
`PATH`, or wherever `CC65` points, so a plain checkout plus an unpacked
cc65 will work without touching the system.

## Build

```
python tools/build.py all        # everything
python tools/build.py game       # build/fm2.tap      (the game)
python tools/build.py selftest   # build/selftest.tap  (on-machine tests)
python tools/build.py unit       # build/test_core.prg + run under sim65
python tools/build.py clean
```

`build/fm2.tap` is an autostarting Atmos tape.  In BASIC:

```
CLOAD""
```

and the game starts.  The tape header carries `$C7` in the autorun field
(see `oric.cfg`), so no `RUN` is needed.

## Running in Oricutron

```
python tools/oricutron.py --tape build/fm2.tap
```

The helper reads the emulated text screen back through Oricutron's own
`F11` screen copy, so scripts can wait for a page and check what is on it.
To drive the game by hand:

```
python tools/oricutron.py --tape build/fm2.tap \
    --type 'CLOAD"' --keys ENTER --wait 20
```

## Tests

```
python tools/build.py all
python tests/e2e_oricutron.py             # full game tour
python tests/e2e_oricutron.py --selftest  # on-machine unit tests
```

The end-to-end script loads the tape the way a player would, then walks
the management screens and plays a match, asserting on the text the Oric
actually displays.  Screenshots of each page land in `build/shots/`.

The host used for the reference run emulates the Oric well below real
speed (every screen capture is a clipboard round trip), so the tests wait
for pages to settle rather than assuming fixed timings.

## Memory map

| Range | Use |
|-------|-----|
| `$0501`–… | BASIC header and the program (linked from `oric.cfg`) |
| … up to `$9400` | code, read-only data and BSS |
| `$9400`–`$9800` | 1K C stack |
| `$BB80` | 40x28 text screen |
| `$BFDF` | ULA control register (not touched: the ROM already sets 1 MHz text) |

The linker will fail with *memory area overflow* if the program grows
past the stack, which is the intended safety net.
