/*
 * action.c - the match action on the Oric HIRES screen.
 *
 * Three camera views follow the ball, as in the Spectrum original: behind
 * the left goal, the halfway line seen from the touchline, and behind the
 * right goal.  The Oric bitmap is one bit per pixel, so the grass is the
 * bright paper and every line, player and the ball is cut out of it in
 * dark paper.  The crowd, the scoreboard card and the advertising bands
 * sit above the pitch.
 *
 * Players are little run-cycle figures, seven pixels wide and twelve
 * tall, about the size of the Spectrum sprites.  They chase the ball in
 * one-pixel steps and change legs on every step, so the pitch is alive
 * while the match plays.  Each step only rubs out the boxes the figures
 * stand in and puts the markings back inside them.
 */
#include <string.h>
#include "fm2.h"
#include "ui.h"
#include "hires.h"
#include "match.h"

/* head of the pitch in scanlines; h_pitch in hires.s draws the same
 * rows and keeps the constant in step with this one */
#define G_TOP  48               /* first green scanline                  */
#define FN     6                /* figures: five outfield and a keeper   */

static unsigned char a_home, a_away;
static unsigned char a_view;    /* 0 left goal, 1 centre, 2 right goal   */
static unsigned char a_tick;    /* animation step, also the leg phase    */
static unsigned char last_hs, last_as, last_min;
static unsigned char ball_x, ball_y;

/* current and previous sprite anchors */
static unsigned char fx[FN], fy[FN], fs[FN], fn;
static unsigned char ox[FN], oy[FN], on;
static unsigned char obx, oby, oball;

/* Base positions for the goal views (the right goal view is mirrored). */
static const unsigned char goal_figs[] = {
    150, 82, 176, 118, 132, 162, 196, 168, 206, 96
};
/* Halfway line, seen from the touchline. */
static const unsigned char mid_figs[] = {
    58, 92, 88, 140, 40, 168, 152, 84, 186, 144
};

/* The markings themselves live in h_marks (hires.s), which draws the same
 * table a row at a time instead of calling the line routine per line. */

static void clockface(unsigned char m);

static unsigned char gx(unsigned char x)
{
    return (unsigned char)(a_view == 2 ? 239 - x : x);
}

/* ------------------------------------------------------------------ */
/* colour                                                              */

/* The Oric starts every scanline with white ink on black paper, and the
 * bitmap can carry serial attribute bytes that change that from the byte
 * they sit in onwards.  The pitch is therefore drawn the other way round
 * from the other bitmap pages: the grass is the paper, and the lines,
 * the players and the ball are ink cut into it.  One paper attribute at
 * the head of each grass run colours the park green; the attribute cell
 * itself falls on grass, so it never shows. */
/* The grass, its attribute bytes and the crowd behind the goal are laid
 * down by h_pitch (hires.s): one row is a run of plain stores there, and
 * doing it in C cost a line call and an attribute write per row. */

/* ------------------------------------------------------------------ */
/* the pitch                                                           */

static void markings(void)
{
    h_marks(a_view);
}

static void pitch(void)
{
    h_pitch(a_view);
    markings();
}

/* ------------------------------------------------------------------ */
/* header                                                              */

/* An advertising hoarding: white letters on the dark surround. */
static void band(unsigned char row, unsigned char col, const char *s)
{
    unsigned char y = (unsigned char)(row * 8);

    h_box0(0, y, 239, (unsigned char)(y + 7));
    h_text(col, row, s);
}

/* A small score in the white panel: dark digits on paper. */
static void digit(unsigned char col, unsigned char row, unsigned char v)
{
    char s[3];

    s[0] = (char)('0' + v / 10);
    s[1] = (char)('0' + v % 10);
    s[2] = 0;
    if (v < 10) {
        s[0] = s[1];
        s[1] = 0;
    }
    h_text(col, row, s);
}

static void header(unsigned char hs, unsigned char as, unsigned char minute)
{
    /* crowd speckle behind the cards, then the card itself: the box has
     * to be rubbed back to blank or the crowd shows through the lettering */
    h_band();

    h_box0(44, 0, 231, 15);
    h_hline(44, 231, 0);
    h_hline(44, 231, 15);
    h_vline(44, 0, 15);
    h_vline(231, 0, 15);
    h_vline(150, 0, 15);
    h_vline(200, 0, 15);
    h_text(9, 0, team_name(a_home));
    h_text(9, 1, team_name(a_away));
    digit(26, 0, hs);
    digit(26, 1, as);
    clockface(minute);

    band(2, 6, sponsor[0] ? sponsor : "CORP   PRISM   LEISURE");
    band(5, 3, "ENDURANCE  ADDICTIVE  GAMES");
}

/* Repaint the score after a goal. */
static void score(unsigned char hs, unsigned char as)
{
    digit(26, 0, hs);
    digit(26, 1, as);
}

/* The match clock, on its own panel at the right of the card. */
static void clockface(unsigned char m)
{
    h_hline(202, 230, 2);
    h_hline(202, 230, 13);
    digit(35, 0, m);
    h_text(35, 1, "MIN");
}

/* ------------------------------------------------------------------ */
/* figures                                                             */

/* Run cycle: two frames of a seven by twelve figure.  Bit 6 is the
 * leftmost pixel.  Ours are solid, theirs are open skeletons. */
static const unsigned char spr_solid[] = {
    0x1C, 0x1C, 0x3E, 0x3E, 0x7F, 0x3E, 0x3E, 0x1C, 0x22, 0x22, 0x41, 0x41,
    0x1C, 0x1C, 0x3E, 0x3E, 0x63, 0x3E, 0x3E, 0x1C, 0x08, 0x08, 0x1C, 0x1C
};
static const unsigned char spr_open[] = {
    0x1C, 0x14, 0x3E, 0x22, 0x2A, 0x22, 0x3E, 0x1C, 0x22, 0x22, 0x41, 0x41,
    0x1C, 0x14, 0x3E, 0x22, 0x22, 0x22, 0x3E, 0x1C, 0x08, 0x08, 0x1C, 0x1C
};
static const unsigned char spr_ball[] = {
    0x1C, 0x3E, 0x1C
};

/* Blitting the figure is h_spr in hires.s: the row is shifted into the two
 * bytes it spans, and the shirt attribute goes in either side of it.  The
 * parameters (spr_src and friends, declared in hires.h) live there so the
 * driver does not have to pass four arguments through the C stack. */

#ifdef ACTION_TRACE
void action_test_fig(unsigned char x, unsigned char y, unsigned char s,
                     unsigned char p)
{
    spr_src = s ? spr_solid : spr_open;
    spr_x = x;
    spr_y = y;
    spr_rows = 12;
    spr_ink = 0;
    h_spr();
    (void)p;
}
#endif

/* The ink colour of figure i: the first two slots are the home side and
 * the rest the away side, so the manager's men wear the chosen kit
 * whichever end of the ground they are attacking. */
static unsigned char figure_ink(unsigned char i)
{
    unsigned char mine = (i < 2) ? a_home : a_away;

    return (unsigned char)(mine == user_team ? shirt : 0);
}

/* Where the players want to be: two thirds of the way from their slot to
 * the ball, and they run at up to three pixels a step, so a move down the
 * pitch is chased by the whole side rather than played out with everybody
 * standing where they kicked off. */
static void layout(void)
{
    const unsigned char *t = (a_view == 1) ? mid_figs : goal_figs;
    unsigned char i;

    fn = 5;
    for (i = 0; i < 5; ++i) {
        int sx = t[i * 2];
        int sy = t[i * 2 + 1];
        int tx, ty, dx, dy;

        if (a_view == 2)
            sx = 239 - sx;
        tx = ((int)ball_x * 2 + sx) / 3;
        ty = ((int)ball_y * 2 + sy) / 3;
        if (tx < 18)
            tx = 18;
        else if (tx > 224)
            tx = 224;
        if (ty < 62)
            ty = 62;
        else if (ty > 172)
            ty = 172;
        dx = tx - (int)fx[i];
        dy = ty - (int)fy[i];
        if (dx > 3)
            dx = 3;
        else if (dx < -3)
            dx = -3;
        if (dy > 2)
            dy = 2;
        else if (dy < -2)
            dy = -2;
        fx[i] = (unsigned char)((int)fx[i] + dx);
        fy[i] = (unsigned char)((int)fy[i] + dy);
        fs[i] = figure_ink(i);
    }
    if (a_view != 1) {
        unsigned char ky = ball_y;

        if (ky < 104)
            ky = 104;
        else if (ky > 148)
            ky = 148;
        fx[5] = gx(104);
        fy[5] = (unsigned char)(ky - 6);
        fs[5] = (unsigned char)((a_view == 0 ? a_home : a_away) == user_team
                                ? shirt : 0);
        fn = 6;
    }
}

/* The user's side wears the kit colour picked at the start of the game.
 * An ink attribute only takes effect from the byte it sits in, so one is
 * written on the grass at each side of the figure (spr_ink, below); the
 * attribute cell itself shows as paper, which is the grass, so nothing
 * leaks. */
static void draw(void)
{
    unsigned char i;

    spr_src = spr_ball;
    spr_x = ball_x;
    spr_y = ball_y;
    spr_rows = 3;
    spr_ink = 0;
    h_spr();
    for (i = 0; i < fn; ++i) {
        const unsigned char *d = fs[i] ? spr_solid : spr_open;

        spr_src = d + (((unsigned char)(a_tick + i)) & 1) * 12;
        spr_x = (unsigned char)(fx[i] - 1);
        spr_y = fy[i];
        spr_rows = 12;
        spr_ink = fs[i];        /* 0 for the other side */
        h_spr();
    }
}

/* Rub out everything drawn last step, put the markings back, redraw.
 * h_box0 clears a whole box in one call: the masks are worked out once
 * and the row pointer walks it.  The boxes reach a byte wider than the
 * figures themselves, because a figure writes its shirt attribute in the
 * byte to the left of its pixels; h_box0 turns that attribute back to
 * white, so no colour is left behind when the figure runs off. */
static void erase(void)
{
    unsigned char i;

    for (i = 0; i < on; ++i)
        h_box0((unsigned char)(ox[i] - 12), (unsigned char)(oy[i] - 1),
               (unsigned char)(ox[i] + 8), (unsigned char)(oy[i] + 13));
    if (oball)
        h_box0((unsigned char)(obx > 2 ? obx - 2 : 0),
               (unsigned char)(oby > 2 ? oby - 2 : 0),
               (unsigned char)(obx + 5), (unsigned char)(oby + 3));
    markings();
}

static void remember(void)
{
    unsigned char i;

    for (i = 0; i < fn; ++i) {
        ox[i] = fx[i];
        oy[i] = fy[i];
    }
    on = fn;
    obx = ball_x;
    oby = ball_y;
    oball = 1;
}

/* ------------------------------------------------------------------ */
/* the animation                                                       */

static unsigned char view_for(unsigned char ex)
{
    if (ex < 13)
        return 0;
    if (ex < 26)
        return 1;
    return 2;
}

static void ball_screen(unsigned char ex, unsigned char ey,
                        unsigned char *px, unsigned char *py)
{
    unsigned int x, y;

    if (a_view == 1) {
        x = 20 + (unsigned int)(ex - 13) * 16;
        y = 86 + (unsigned int)ey * 13;
    } else {
        if (a_view == 0)
            x = 94 + (unsigned int)ex * 7;
        else
            x = 94 + (unsigned int)(39 - ex) * 7;
        if (a_view == 2)
            x = 239 - x;
        y = 92 + (unsigned int)ey * 11;
    }
    if (x > 232)
        x = 232;
    if (y > 184)
        y = 184;
    if (y < 70)
        y = 70;
    *px = (unsigned char)x;
    *py = (unsigned char)y;
}

/* One animation step: erase, move, redraw, and wait a little. */
static void step(unsigned char bx, unsigned char by)
{
    erase();
    ball_x = bx;
    ball_y = by;
    ++a_tick;
    layout();
    draw();
    remember();
    ui_pause(2500);
}

void action_begin(unsigned char home, unsigned char away, unsigned char flip)
{
    unsigned char i;

    a_home = home;
    a_away = away;
    (void)flip;
    a_view = 1;
    a_tick = 0;
    ball_x = 120;
    ball_y = 126;
    last_hs = 0;
    last_as = 0;
    last_min = 0;
    fn = 5;
    for (i = 0; i < 5; ++i) {
        fx[i] = mid_figs[i * 2];
        fy[i] = mid_figs[i * 2 + 1];
        fs[i] = figure_ink(i);
    }
    hires_on();
    h_inv = 1;                  /* grass is the paper on this page */
    pitch();
    header(0, 0, 0);
    layout();
    draw();
    on = 0;
    oball = 0;
    remember();
}

void action_end(void)
{
    h_inv = 0;
    hires_off();
}

void action_frame(unsigned char ex, unsigned char ey, unsigned char minute,
                  unsigned char hs, unsigned char as, unsigned char cup)
{
    unsigned char v, nx, ny, bx, by, k;

    (void)cup;

    v = view_for(ex);

    if (v != a_view) {
        unsigned char i;
        const unsigned char *t;

        a_view = v;
        a_tick = 0;
        ball_screen(ex, ey, &nx, &ny);
        ball_x = nx;
        ball_y = ny;
        t = (a_view == 1) ? mid_figs : goal_figs;
        for (i = 0; i < 5; ++i) {
            fx[i] = t[i * 2];
            fy[i] = t[i * 2 + 1];
            if (a_view == 2)
                fx[i] = (unsigned char)(239 - fx[i]);
        }
        /* h_pitch covers every byte of the pitch rows, so there is no
         * screen clear here: painting straight over the old view is both
         * quicker and flash free. */
        pitch();
        header(hs, as, minute);
        layout();
        draw();
        remember();
        last_hs = hs;
        last_as = as;
        last_min = minute;
        ui_pause(2000);
        return;
    }

    ball_screen(ex, ey, &nx, &ny);
    bx = ball_x;
    by = ball_y;
    for (k = 1; k <= 8; ++k)
        step((unsigned char)((int)bx + ((int)nx - (int)bx) * k / 8),
             (unsigned char)((int)by + ((int)ny - (int)by) * k / 8));

    /* keep the players running while the next move is worked out */
    step(ball_x, ball_y);

    if (minute != last_min) {
        clockface(minute);
        last_min = minute;
    }
    if (hs != last_hs || as != last_as)
        score(hs, as);
    last_hs = hs;
    last_as = as;
}
