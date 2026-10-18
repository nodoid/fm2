/*
 * ui.c - screen helpers for Football Manager 2.
 *
 * Everything the game draws goes through these few primitives, which in
 * turn call the assembly screen driver in scr.s.  The line builder is
 * used because the Oric has no printf in the ROM linkage we use and
 * cc65's printf is far too big for a 37K machine.
 */
#include <string.h>
#include "fm2.h"
#include "ui.h"

/* ---------------------------------------------------------------------- */
/* screen rows used by every page                                          */

#define ROW_HEAD 0
#define ROW_SEP  1
#define ROW_TOP  3
#define ROW_MSG  24
#define ROW_HELP 25
#define ROW_FOOT 27
#define ROW_INFO 26

/* attribute bytes: $00-$07 ink, $10-$17 paper, written into a cell */
#define ATTR_BLUE_BAR  0x14    /* blue paper, white ink */
#define ATTR_YELLOW    0x13
#define ATTR_CYAN_INK  0x06
#define ATTR_GREEN_INK 0x02
#define ATTR_RED_INK   0x01

static char lb[42];
static unsigned char lblen;      /* strlen(lb), kept up to date: the Oric is
                                  * far too slow to rescan the line on
                                  * every character */

/* ---------------------------------------------------------------------- */
/* basic output                                                            */

void ui_clear(void)
{
    scr_clear();
}

void ui_gotoxy(unsigned char x, unsigned char y)
{
    scr_gotoxy(x, y);
}

void ui_putc(char c)
{
    scr_putc((unsigned char)c);
}

void ui_puts(const char *s)
{
    scr_puts(s);
}

void ui_puts_inv(const char *s)
{
    scr_puts_inv(s);
}

void ui_fill(unsigned char y, char c)
{
    scr_fill(y, (unsigned char)c);
}

void ui_attr(unsigned char y, unsigned char a)
{
    scr_attr(y, a);
}

void ui_hline(unsigned char y, char c)
{
    scr_gotoxy(0, y);
    scr_fill(y, (unsigned char)c);
}

void ui_center(unsigned char y, const char *s)
{
    unsigned char n = (unsigned char)strlen(s);
    unsigned char x = (unsigned char)((40 - n) / 2);

    scr_gotoxy(x, y);
    scr_puts(s);
}

/* ---------------------------------------------------------------------- */
/* line builder                                                            */

void lb_reset(void)
{
    lblen = 0;
    lb[0] = 0;
}

void lb_str(const char *s)
{
    str_append(lb, s);
    lblen = (unsigned char)strlen(lb);
}

void lb_str_clip(const char *s, unsigned char max)
{
    while (*s && lblen < max)
        lb_ch(*s++);
}

void lb_ch(char c)
{
    if (lblen < 41) {
        lb[lblen++] = c;
        lb[lblen] = 0;
    }
}

void lb_num(unsigned int v, unsigned char width, char pad)
{
    char t[8];
    unsigned char n;

    u2s(v, t);
    n = (unsigned char)strlen(t);
    while (n < width) {
        lb_ch(pad);
        ++n;
    }
    lb_str(t);
}

void lb_spaces(unsigned char n)
{
    while (n--)
        lb_ch(' ');
}

void lb_pad(unsigned char width)
{
    while (lblen < width)
        lb_ch(' ');
}

void lb_draw(unsigned char x, unsigned char y)
{
    scr_gotoxy(x, y);
    scr_puts(lb);
}

void lb_draw_inv(unsigned char x, unsigned char y)
{
    scr_gotoxy(x, y);
    scr_puts_inv(lb);
}

unsigned char lb_len(void)
{
    return lblen;
}

void lb_draw_center(unsigned char y, unsigned char inv)
{
    unsigned char n = lblen;
    unsigned char x = (unsigned char)(n < 40 ? (40 - n) / 2 : 0);

    scr_gotoxy(x, y);
    if (inv)
        scr_puts_inv(lb);
    else
        scr_puts(lb);
}

/* ---------------------------------------------------------------------- */
/* keyboard                                                                */

unsigned char ui_key(void)
{
    unsigned char k;

    do {
        k = kbd_get();
    } while (!k);
    snd_click();
    return k;
}

unsigned char ui_key_ns(void)
{
    unsigned char k;

    do {
        k = kbd_get();
    } while (!k);
    return k;
}

unsigned char ui_poll(void)
{
    return kbd_get();
}

void ui_flush(void)
{
    while (kbd_get())
        ;
}

void wait_esc(void)
{
    while (ui_key() != K_ESC)
        ;
}

void ui_pause(unsigned int n)
{
    volatile unsigned int i;

    for (i = 0; i < n; ++i)
        ;
}

/* ---------------------------------------------------------------------- */
/* page furniture                                                          */

void ui_header(void)
{
    char b[8];
    unsigned char wk = (unsigned char)(round_num + 1);

    if (wk > ROUNDS)
        wk = ROUNDS;

    scr_attr(ROW_HEAD, ATTR_BAR);
    lb_reset();
    lb_str(league[user_team].name);
    lb_pad(13);
    lb_str(" D");
    lb_num((unsigned int)(user_team / TEAMS_PER_DIV + 1), 1, ' ');
    lb_str("  WK");
    lb_num(wk, 2, ' ');
    lb_str("  ");
    lb_num(cash, 4, ' ');
    lb_ch('K');
    lb_str("  P");
    lb_num(user_position(), 2, ' ');
    lb_pad(39);
    lb_draw(1, ROW_HEAD);
    (void)b;

    ui_hline(ROW_SEP, '=');
}

void ui_footer(const char *hints)
{
    ui_hline(ROW_FOOT, ' ');
    ui_gotoxy(0, ROW_FOOT);
    ui_puts_inv(hints);
}

void ui_message(const char *msg)
{
    ui_hline(ROW_MSG, ' ');
    ui_gotoxy(0, ROW_MSG);
    ui_puts(msg);
}

void ui_help(const char *msg)
{
    ui_hline(ROW_HELP, ' ');
    ui_gotoxy(0, ROW_HELP);
    ui_puts(msg);
}

void ui_title(unsigned char y, const char *s)
{
    ui_hline(y, ' ');
    ui_center(y, s);
}

/* Write a coloured bar (attribute in column 0) with centred text. */
void ui_bar_center(unsigned char y, const char *s, unsigned char attr)
{
    unsigned char n = (unsigned char)strlen(s);

    scr_attr(y, attr);
    lb_reset();
    lb_str(s);
    lb_pad(39);
    lb_draw(1 + (unsigned char)((39 - n) / 2), y);
}

/* Draw the current line builder contents as a menu entry. */
void ui_item_lb(unsigned char y, unsigned char selected)
{
    lb_pad(39);
    if (selected)
        lb_draw_inv(0, y);
    else
        lb_draw(0, y);
}

/* Draw one menu entry; the selected line is drawn in inverse video. */
void ui_item(unsigned char y, const char *s, unsigned char selected)
{
    lb_reset();
    lb_str(s);
    lb_pad(39);
    if (selected)
        lb_draw_inv(0, y);
    else
        lb_draw(0, y);
}

/* ---------------------------------------------------------------------- */
/* formatted helpers used by several screens                               */

void ui_table_row(unsigned char y, unsigned char pos, unsigned char team,
                  unsigned char selected)
{
    Team *t = &league[team];
    int gd = (int)t->gf - (int)t->ga;

    lb_reset();
    lb_num(pos, 2, ' ');
    lb_ch(' ');
    lb_str(t->name);
    lb_pad(15);
    lb_num(t->played, 2, ' ');
    lb_ch(' ');
    lb_num(t->won, 2, ' ');
    lb_ch(' ');
    lb_num(t->drawn, 2, ' ');
    lb_ch(' ');
    lb_num(t->lost, 2, ' ');
    if (gd < 0) {
        gd = -gd;
        lb_ch('-');
    } else {
        lb_ch(' ');
    }
    lb_num((unsigned int)gd, 2, ' ');
    lb_ch(' ');
    lb_num(t->points, 2, ' ');
    lb_pad(39);
    if (selected)
        lb_draw_inv(0, y);
    else
        lb_draw(0, y);
}

/* Two-column club picker list used by the new-game screen. */
void ui_club_row(unsigned char y, unsigned char left, unsigned char right,
                 unsigned char selected)
{
    lb_reset();
    lb_num((unsigned int)(left + 1), 2, ' ');
    lb_ch(' ');
    lb_str(league[left].name);
    lb_pad(21);
    if (right < NUM_TEAMS) {
        lb_num((unsigned int)(right + 1), 2, ' ');
        lb_ch(' ');
        lb_str(league[right].name);
    }
    lb_pad(39);
    if (selected)
        lb_draw_inv(0, y);
    else
        lb_draw(0, y);
}

/* simple full line with an ink attribute (used for flashes) */
void ui_flash(unsigned char y, const char *msg, unsigned char attr)
{
    scr_attr(y, attr);
    lb_reset();
    lb_str(msg);
    lb_pad(39);
    lb_draw(1, y);
}

void ui_colour(unsigned char y, unsigned char attr)
{
    scr_attr(y, attr);
}

unsigned char is_up(unsigned char k)
{
    return (unsigned char)(k == K_UP);
}

unsigned char is_down(unsigned char k)
{
    return (unsigned char)(k == K_DOWN);
}

/* ---------------------------------------------------------------------- */
/* match action pitch                                                      */

#define PITCH_TOP 3
#define PITCH_ROWS 9

static unsigned char pitch_last_x, pitch_last_y;

/* Map a zone slot to a pitch cell.  Home attacks to the right. */
static void slot_cell(unsigned char side, unsigned char view,
                      unsigned char slot, unsigned char *x, unsigned char *y)
{
    static const unsigned char hx[3] = { 8, 18, 28 };
    static const unsigned char ax[3] = { 31, 21, 11 };

    *x = side ? ax[view] : hx[view];
    *y = (unsigned char)(PITCH_TOP + 1 + slot * 2);
}

/* Draw the field once: border, halfway line and penalty boxes. */
void ui_pitch_frame(void)
{
    unsigned char r, i;

    ui_fill(PITCH_TOP, '-');
    for (r = 1; r < PITCH_ROWS - 1; ++r) {
        ui_fill((unsigned char)(PITCH_TOP + r), ' ');
        scr_gotoxy(0, (unsigned char)(PITCH_TOP + r));
        scr_putc('|');
        scr_gotoxy(39, (unsigned char)(PITCH_TOP + r));
        scr_putc('|');
    }
    ui_fill((unsigned char)(PITCH_TOP + PITCH_ROWS - 1), '-');
    for (i = 0; i < PITCH_ROWS; ++i) {
        scr_gotoxy(20, (unsigned char)(PITCH_TOP + i));
        scr_putc(i == 0 || i == PITCH_ROWS - 1 ? '+' : ':');
    }
    pitch_last_x = 0xFF;
    pitch_last_y = 0xFF;
}

/* Restore whatever was under the ball, then draw the players and the ball. */
void ui_pitch_draw(unsigned char bx, unsigned char by)
{
    unsigned char side, view, slot, x, y;

    if (pitch_last_x != 0xFF)
        scr_gotoxy(pitch_last_x, pitch_last_y), scr_putc(' ');

    /* the user's shape comes from the twelve zones */
    for (view = 0; view < 3; ++view) {
        for (slot = 0; slot < 4; ++slot) {
            if (zone[view * 4 + slot] == 0xFF)
                continue;
            slot_cell(0, view, slot, &x, &y);
            scr_gotoxy(x, y);
            scr_putc('H');
        }
    }
    /* the opposition always lines up 4-4-2 */
    for (view = 0; view < 3; ++view) {
        unsigned char max = (unsigned char)(view == VIEW_ATT ? 2 : 4);

        for (slot = 0; slot < max; ++slot) {
            slot_cell(1, view, slot, &x, &y);
            scr_gotoxy(x, y);
            scr_putc('A');
        }
    }
    (void)side;

    if (bx > 39)
        bx = 39;
    if (by > PITCH_ROWS)
        by = PITCH_ROWS;
    x = bx;
    y = (unsigned char)(PITCH_TOP + by);
    if (y > PITCH_TOP + PITCH_ROWS - 1)
        y = (unsigned char)(PITCH_TOP + PITCH_ROWS - 1);
    scr_gotoxy(x, y);
    scr_putc('*');
    pitch_last_x = x;
    pitch_last_y = y;
}

/* Scoreboard above the pitch. */
void ui_pitch_score(const char *home, const char *away, unsigned char hs,
                    unsigned char as, unsigned char minute, unsigned char cup)
{
    char b[6];

    lb_reset();
    lb_str(home);
    lb_ch(' ');
    lb_num(hs, 1, ' ');
    lb_ch('-');
    lb_num(as, 1, ' ');
    lb_ch(' ');
    lb_str(away);
    lb_pad(31);
    lb_num(minute, 2, ' ');
    lb_ch('\'');
    if (cup)
        lb_str(" CUP");
    lb_draw(0, 0);
    ui_hline(1, '=');
    (void)b;
    (void)cup;
}
