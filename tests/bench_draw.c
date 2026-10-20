/* Cycle benchmark for the match screen, run under sim65 --cycles.
 *
 *   cl65 -t sim6502 -O -I src -o build/bench_draw.prg tests/bench_draw.c \
 *        src/action.c src/game.c src/match.c src/hires.c src/hires.s \
 *        src/font.s
 *   sim65 --cycles build/bench_draw.prg <mode>
 *
 * Modes, from cheapest to most work, so the runner can report the cost of
 * each part by subtraction:
 *   0  boot, new game and paint the centre view
 *   1  mode 0 + eight animation frames that stay in the same view
 *   2  mode 0 + three camera changes, each a full pitch repaint
 *   3  mode 0 + two hundred full-width lines (the line primitive itself)
 *   4  mode 0 + a hundred 9x15 erase rows (the erase primitive)
 *   5  mode 0 + twenty whole screen clears
 *   6  mode 0 + twenty pitch repaints (grass, wedge and crowd)
 *   7  mode 0 + forty sets of pitch markings
 *   8  mode 0 + twenty header crowd bands
 *   9  mode 0 + a hundred nine letter strings
 *
 * tests/bench.py compiles this and prints the deltas.
 */
#include <stdlib.h>
#include "fm2.h"
#include "action.h"
#include "hires.h"

void ui_pause(unsigned int n)
{
    (void)n;
}

int main(int argc, char **argv)
{
    unsigned char mode = 0;
    unsigned char i;

    if (argc > 1)
        mode = (unsigned char)atoi(argv[1]);

    rng_seed(1234);
    league_setup();
    new_game(62);
    shirt = 4;
    action_begin(62, 63, 0);            /* centre view: paints the pitch */

    switch (mode) {
    case 1:
        /* Eight frames in the centre view: nine animation steps each. */
        for (i = 0; i < 8; ++i)
            action_frame((unsigned char)(16 + i), (unsigned char)(3 + i),
                         10, 0, 0, 0);
        break;
    case 2:
        /* One trip through all three cameras. */
        action_frame(4, 4, 20, 0, 0, 0);
        action_frame(34, 4, 30, 0, 0, 0);
        action_frame(20, 5, 40, 0, 0, 0);
        break;
    case 3:
        for (i = 0; i < 200; ++i) {
            unsigned char y;

            for (y = 48; y < 200; ++y)
                h_hline(0, 239, y);
        }
        break;
    case 4:
        for (i = 0; i < 100; ++i) {
            unsigned char y;

            for (y = 60; y < 75; ++y)
                h_hline(100, 108, y);
        }
        break;
    case 5:
        for (i = 0; i < 20; ++i)
            h_clear();
        break;
    case 6:
        for (i = 0; i < 20; ++i)
            h_pitch((unsigned char)(i % 3));
        break;
    case 7:
        for (i = 0; i < 40; ++i)
            h_marks((unsigned char)(i % 3));
        break;
    case 8:
        for (i = 0; i < 20; ++i)
            h_band();
        break;
    case 9:
        for (i = 0; i < 100; ++i)
            h_text(5, 10, "TEAM NAME");
        break;
    default:
        break;
    }
    return 0;
}
