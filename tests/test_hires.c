/* Draw the HIRES primitives on the sim65 6502 simulator and write the
 * bitmap to stdout, so the drawing code can be checked without an
 * emulator:
 *
 *   python tools/build.py hires > build/hires.bin
 *   python tools/hiresview.py build/hires.bin
 */
#include <unistd.h>
#include "hires.h"

char *u2s(unsigned int v, char *buf)
{
    char t[6];
    unsigned char n = 0;

    if (!v) {
        buf[0] = '0';
        buf[1] = 0;
        return buf;
    }
    while (v) {
        t[n++] = (char)('0' + v % 10);
        v /= 10;
    }
    {
        unsigned char i = 0;
        while (n)
            buf[i++] = t[--n];
        buf[i] = 0;
    }
    return buf;
}

void str_append(char *dst, const char *src)
{
    while (*dst)
        ++dst;
    while (*src)
        *dst++ = *src++;
    *dst = 0;
}

int main(void)
{
    h_clear();
    h_rect(24, 16, 216, 150);
    h_hline(24, 216, 83);
    h_circle(120, 83, 14);
    h_rect(74, 16, 166, 34);
    h_rect(100, 16, 140, 25);
    h_rect(74, 132, 166, 150);
    h_rect(100, 141, 140, 150);
    h_text(0, 0, "TEAM SELECTION");
    h_text(20, 0, "MIDFIELD");
    h_texti(0, 1, "RESERVE POOL - FIRE TO PICK A PLAYER");
    h_text(5, 7, "SMITH");
    h_text(5, 8, "D7 88");
    h_spot(100, 60, 1);
    h_spot(140, 60, 2);
    h_spot(120, 94, 0);
    h_text(0, 24, "Q/S SLOT  I/P VIEW  SPACE FIRE  ESC");
    write(1, (void *)0xA000, 8000);
    return 0;
}
