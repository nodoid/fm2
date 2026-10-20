/* Draw the match action screen under sim65 and dump the bitmap for each
 * of the three camera views, so the match screen can be inspected without
 * booting the emulator:
 *
 *   cl65 -t sim6502 -O -I src -o build/test_action.prg tests/test_action.c \
 *        src/action.c src/game.c src/match.c src/hires.c src/hires.s \
 *        src/font.s
 *   sim65 build/test_action.prg > build/action.bin
 *
 * The three 8000 byte bitmaps follow one another in the output; a 16 byte
 * marker says which view each one is.
 */
#include <unistd.h>
#include "fm2.h"
#include "action.h"

void ui_pause(unsigned int n)
{
    (void)n;
}

static void dump(char which)
{
    write(1, &which, 1);
    write(1, (void *)0xA000, 8000);
}

int main(void)
{
    rng_seed(1234);
    league_setup();
    new_game(62);
    shirt = 1;
    action_begin(62, 63, 0);
    dump('b');                       /* straight after begin */
    action_frame(20, 4, 33, 0, 0, 0);      /* centre circle */
    dump('m');
    action_frame(6, 5, 55, 1, 0, 0);       /* left goal */
    dump('l');
    action_frame(34, 2, 90, 2, 1, 0);      /* right goal */
    dump('r');
    return 0;
}
