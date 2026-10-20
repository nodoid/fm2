/* Draw two players on a blank pitch and dump the bitmap.
 *
 *   cl65 -t sim6502 -O -DACTION_TRACE -I src -o build/test_fig.prg \
 *        tests/test_fig.c src/action.c src/game.c src/match.c src/hires.c \
 *        src/hires.s src/font.s
 *   sim65 build/test_fig.prg > build/fig.bin
 */
#include <unistd.h>
#include "fm2.h"
#include "hires.h"

void ui_pause(unsigned int n)
{
    (void)n;
}

void action_test_fig(unsigned char x, unsigned char y, unsigned char s,
                     unsigned char p);

int main(void)
{
    unsigned char y;

    rng_seed(99);
    league_setup();
    new_game(62);
    h_clear();
    for (y = 48; y < 200; ++y)
        h_hline(0, 239, y);
    action_test_fig(60, 70, 1, 0);
    action_test_fig(100, 70, 1, 1);
    action_test_fig(140, 70, 0, 0);
    action_test_fig(180, 70, 0, 1);
    write(1, (void *)0xA000, 8000);
    return 0;
}
