/* HIRES fill probe: check h_fill's masks and row loop.
 *
 *   cl65 -t sim6502 -O -I src -o build/test_fill.prg tests/test_fill.c \
 *        src/hires.c src/hires.s src/font.s
 *   sim65 build/test_fill.prg > build/fill.bin
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

int main(void)
{
    h_clear();
    h_fill(40, 98, 46, 102);    /* bytes 6..7, rows 98..102 */
    h_fill(0, 120, 5, 120);     /* exactly byte 0, one row  */
    h_fill(234, 130, 239, 130); /* exactly the last byte    */
    write(1, (void *)0xA000, 8000);
    return 0;
}
