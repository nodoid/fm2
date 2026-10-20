/* Minimal HIRES line probe: one horizontal run per scanline, so an
 * off-by-one in the drawing drivers is obvious in the dump.
 *
 *   cl65 -t sim6502 -O -I src -o build/test_line.prg tests/test_line.c \
 *        src/hires.c src/hires.s src/font.s
 *   sim65 build/test_line.prg > build/line.bin
 */
#include <unistd.h>
#include "hires.h"

char *u2s(unsigned int v, char *buf)
{
    (void)v;
    buf[0] = 0;
    return buf;
}

void str_append(char *dst, const char *src)
{
    while (*src)
        *dst++ = *src++;
    *dst = 0;
}

static void fill_rows(unsigned char y0, unsigned char y1)
{
    unsigned char y, x;

    for (y = y0; y < y1; ++y) {
        for (x = (unsigned char)((y & 1) ? 2 : 0); x < 240; x += 6) {
            if (!(x >= 48 && x <= 192))
                h_hline(x, (unsigned char)(x + 2), y);
        }
    }
}

int main(void)
{
    unsigned char y;

    h_clear();
    h_hline(0, 2, 10);          /* single byte, left edge */
    h_hline(0, 239, 11);        /* full width            */
    h_hline(6, 8, 12);          /* one byte at x=6       */
    h_hline(0, 5, 13);          /* exactly byte 0        */
    h_hline(234, 239, 14);      /* exactly the last byte */
    h_hline(3, 9, 15);          /* two bytes             */
    h_dark = 1;
    h_hline(0, 239, 16);
    h_hline(0, 239, 17);
    h_dark = 0;

    for (y = 48; y < 200; ++y)  /* the pitch fill */
        h_hline(0, 239, y);

    h_dark = 1;
    h_hline(60, 62, 74);        /* dark 3px run, direct */
    h_hline(60, 64, 75);
    h_vline(80, 74, 78);        /* dark column, direct  */
    h_dark = 0;
    h_bline(60, 62, 70);        /* dark 3px run  */
    h_bline(60, 64, 71);        /* dark 5px run  */
    h_bline(60, 60, 72);        /* dark 1px run  */
    h_bvline(84, 70, 73);       /* dark column   */

    fill_rows(24, 32);          /* the crowd pattern */
    write(1, (void *)0xA000, 8000);
    return 0;
}
