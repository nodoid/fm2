/* Pixel-level checks for the sprite blitter and the erase box.
 *
 * A serial attribute colours the rest of its scanline, so a figure has to
 * put its shirt colour in the byte to the left of its pixels and a white
 * one back in the byte to the right.  Getting that wrong is not a crash,
 * it is a match screen with the manager's colour streaking over the crowd
 * and the goal lines, which is exactly what this catches:
 *
 *   python tools/build.py unit
 */
#include <stdio.h>
#include "hires.h"

#define SCR ((unsigned char *)0xA000)

static int fails;

static void check(int ok, const char *what, int a, int b)
{
    if (!ok) {
        ++fails;
        printf("FAILED: %s (%d vs %d)\n", what, a, b);
    }
}

static const unsigned char fig[] = {
    0x1C, 0x1C, 0x3E, 0x3E, 0x7F, 0x3E, 0x3E, 0x1C, 0x22, 0x22, 0x41, 0x41,
    0x1C, 0x1C, 0x3E, 0x3E, 0x63, 0x3E, 0x3E, 0x1C, 0x08, 0x08, 0x1C, 0x1C
};
static const unsigned char ball[] = { 0x1C, 0x3E, 0x1C };

/* Blank the bitmap without h_clear's text footer, which is itself a run of
 * space cells in the last three rows and would be counted as attributes. */
static void blank(void)
{
    int y, x;

    for (y = 0; y < 200; ++y)
        for (x = 0; x < 40; ++x)
            SCR[y * 40 + x] = 0x40;
}

/* Count the attribute bytes on the screen and report where they are. */
static int attrs(unsigned char *value)
{
    int n = 0;
    int y, x;

    for (y = 0; y < 200; ++y)
        for (x = 0; x < 40; ++x) {
            unsigned char b = SCR[y * 40 + x];

            if (!(b & 0x40)) {
                if (value)
                    value[n] = b;
                ++n;
            }
        }
    return n;
}

static void attr_at(unsigned char *found, int *row, int *col, int which)
{
    int n = 0;
    int y, x;

    *found = 0;
    *row = -1;
    *col = -1;
    for (y = 0; y < 200; ++y)
        for (x = 0; x < 40; ++x) {
            unsigned char b = SCR[y * 40 + x];

            if (!(b & 0x40) && n++ == which) {
                *found = b;
                *row = y;
                *col = x;
                return;
            }
        }
}

/* The lowest and highest x that a sprite put ink on, and its rows. */
static void extent(unsigned char y0, unsigned char rows, unsigned char *x0,
                   unsigned char *x1, unsigned char *ry0, unsigned char *ry1)
{
    int y, x;

    *x0 = 255; *x1 = 0; *ry0 = 255; *ry1 = 0;
    for (y = y0; y < y0 + rows; ++y)
        for (x = 0; x < 240; ++x) {
            unsigned char b = SCR[y * 40 + x / 6];

            if ((b & 0x40) && (b & (0x20 >> (x % 6)))) {
                if (x < *x0) *x0 = x;
                if (x > *x1) *x1 = x;
                if (y < *ry0) *ry0 = y;
                if (y > *ry1) *ry1 = y;
            }
        }
}

/* A figure at every byte phase: the shirt goes one byte left of the pixels
 * and white comes back one byte right of them, and nothing else on the
 * screen is turned into a colour cell. */
static void test_figure(unsigned char x, unsigned char y)
{
    unsigned char left, right;
    unsigned char x0, x1, ry0, ry1;
    int row, col, n;

    blank();
    spr_src = fig;
    spr_x = x;
    spr_y = y;
    spr_rows = 12;
    spr_ink = 1;
    h_spr();

    n = attrs(0);
    check(n == 24, "a figure writes two cells on each of its 12 rows", n, 24);

    attr_at(&left, &row, &col, 0);
    check(left == 1, "the shirt attribute holds the kit colour", left, 1);
    check(row == y, "the shirt attribute is on the figure's first row",
          row, y);

    attr_at(&right, &row, &col, 1);
    check(right == 7, "the cell after the figure is white ink", right, 7);

    extent(y, 12, &x0, &x1, &ry0, &ry1);
    check(x1 < 240, "the figure drew something", x1, 0);
    check(ry0 == y && ry1 == (unsigned char)(y + 11),
          "the pixels cover the twelve rows", ry0, y);
    check(col > x1 / 6, "the white cell is to the right of the pixels",
          col, x1 / 6);
    check(col == (x1 / 6) + 1, "the white cell is the next byte along",
          col, (x1 / 6) + 1);

    /* every row of the figure has the shirt one byte left of its pixels */
    {
        int i, bad = 0;

        for (i = 0; i < 12; ++i) {
            unsigned char b = SCR[(y + i) * 40 + (x / 6) - 1];

            if (b != 1)
                ++bad;
        }
        check(bad == 0, "the shirt cell is on every row of the figure",
              bad, 0);
    }
}

/* Erasing the box a figure stood in must put the white ink back. */
static void test_erase(void)
{
    blank();
    spr_src = fig;
    spr_x = 100;
    spr_y = 60;
    spr_rows = 12;
    spr_ink = 1;
    h_spr();
    h_box0(88, 59, 108, 73);
    check(attrs(0) == 0, "erasing the box leaves no colour cell", attrs(0), 0);
    check((SCR[60 * 40 + 100 / 6] & 0x3F) == 0, "the pixels are gone",
          SCR[60 * 40 + 100 / 6] & 0x3F, 0);
}

/* The wedge behind a goal owns its paper cell: erasing over it must not
 * take the black away. */
static void test_paper(void)
{
    blank();
    SCR[80 * 40 + 10] = 0x10;      /* paper black, the dark wedge */
    h_box0(50, 78, 90, 82);
    check(SCR[80 * 40 + 10] == 0x10,
          "erasing keeps a paper attribute as it is",
          SCR[80 * 40 + 10], 0x10);
}

/* The ball's pixels have to sit inside the box action.c rubs out. */
static void test_ball(unsigned char x)
{
    unsigned char x0, x1, ry0, ry1;

    blank();
    spr_src = ball;
    spr_x = x;
    spr_y = 90;
    spr_rows = 3;
    spr_ink = 0;
    h_spr();
    extent(88, 6, &x0, &x1, &ry0, &ry1);
    check(x0 >= (unsigned char)(x - 2), "the ball starts inside its box",
          x0, x - 2);
    check(x1 <= (unsigned char)(x + 5), "the ball ends inside its box",
          x1, x + 5);
    check(attrs(0) == 0, "the ball writes no colour cell", attrs(0), 0);
}

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
    unsigned char x;

    for (x = 40; x < 46; ++x)          /* one of each byte phase */
        test_figure(x, 50);
    for (x = 90; x < 96; ++x)
        test_ball(x);
    test_erase();
    test_paper();

    if (fails)
        printf("%d checks FAILED\n", fails);
    else
        printf("sprite checks passed\n");
    return fails ? 1 : 0;
}
