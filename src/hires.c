/*
 * hires.c - shapes for the HIRES screens.
 *
 * Every pixel goes through the assembly driver; the loops here are only
 * for outlines, markers and little filled patches.
 */
#include <string.h>
#include "fm2.h"
#include "hires.h"

/* The HIRES font, seven rows a glyph, already in the six pixel cell
 * layout the text screen wants (see font.s). */
extern const unsigned char font6[];

/*
 * Rebuild the text mode character set that the bitmap covers.  The ULA
 * indexes the set by the character code itself -- glyph for 'A' sits at
 * $B400 + 65*8 -- so the 32 control codes before the space take a blank
 * glyph each and the font starts at $B500.  A text cell is eight rows,
 * so each glyph is the font's seven rows and a blank row after it.
 */
void scr_charset(void)
{
    unsigned char g, r;
    unsigned char *dst = (unsigned char *)0xB400;

    for (g = 0; g < 128; ++g) {
        for (r = 0; r < 8; ++r) {
            if (g >= 32 && g < 96 && r < 7)
                *dst++ = font6[(unsigned int)(g - 32) * 7 + r];
            else
                *dst++ = 0;
        }
    }
}

void h_rect(unsigned char x0, unsigned char y0, unsigned char x1,
            unsigned char y1)
{
    h_hline(x0, x1, y0);
    h_hline(x0, x1, y1);
    h_vline(x0, y0, y1);
    h_vline(x1, y0, y1);
}

void h_thick(unsigned char x0, unsigned char y0, unsigned char x1,
             unsigned char y1)
{
    h_rect(x0, y0, x1, y1);
    if (x1 > x0 + 2 && y1 > y0 + 2)
        h_rect((unsigned char)(x0 + 1), (unsigned char)(y0 + 1),
               (unsigned char)(x1 - 1), (unsigned char)(y1 - 1));
}

/* Dark ink on the bright pitch: the line drivers honour this flag. */
void h_bline(unsigned char x0, unsigned char x1, unsigned char y)
{
    h_dark = 1;
    h_hline(x0, x1, y);
    h_dark = 0;
}

void h_bvline(unsigned char x, unsigned char y0, unsigned char y1)
{
    h_dark = 1;
    h_vline(x, y0, y1);
    h_dark = 0;
}

/* Small markers: 0 ball, 1 user player, 2 opponent. */
void h_spot(unsigned char x, unsigned char y, unsigned char kind)
{
    unsigned char i, j;

    if (kind == 0) {
        h_plot(x, y);
        h_plot((unsigned char)(x + 1), y);
        h_plot(x, (unsigned char)(y + 1));
        h_plot((unsigned char)(x + 1), (unsigned char)(y + 1));
        return;
    }
    for (i = 0; i < 3; ++i) {
        for (j = 0; j < 3; ++j) {
            if (kind == 1 || i == 0 || i == 2 || j == 0 || j == 2)
                h_plot((unsigned char)(x + i), (unsigned char)(y + j));
        }
    }
}

void h_circle(unsigned char cx, unsigned char cy, unsigned char r)
{
    signed char x = 0, y = (signed char)r;
    signed char d = (signed char)(1 - r);

    while (x <= y) {
        h_plot((unsigned char)(cx + x), (unsigned char)(cy + y));
        h_plot((unsigned char)(cx - x), (unsigned char)(cy + y));
        h_plot((unsigned char)(cx + x), (unsigned char)(cy - y));
        h_plot((unsigned char)(cx - x), (unsigned char)(cy - y));
        h_plot((unsigned char)(cx + y), (unsigned char)(cy + x));
        h_plot((unsigned char)(cx - y), (unsigned char)(cy + x));
        h_plot((unsigned char)(cx + y), (unsigned char)(cy - x));
        h_plot((unsigned char)(cx - y), (unsigned char)(cy - x));
        ++x;
        if (d < 0)
            d = (signed char)(d + 2 * x + 1);
        else {
            --y;
            d = (signed char)(d + 2 * (x - y) + 1);
        }
    }
}

void h_num(unsigned char col, unsigned char row, unsigned int v,
           unsigned char width)
{
    char b[6];
    char t[6];
    unsigned char n, i;

    u2s(v, b);
    n = (unsigned char)strlen(b);
    i = 0;
    while (n + i < width) {
        t[i++] = ' ';
    }
    t[i] = 0;
    str_append(t, b);
    h_text(col, row, t);
}
