/*
 * select.c - team selection, the FM2 way.
 *
 * The Spectrum game shows the pitch over three screens (defence, midfield
 * and attack) with four outfield positions on each and the goalkeeper on
 * the defensive screen.  A reserve pool sits at the top of the screen:
 * fire on it to bring up a player, up/down to scroll through the
 * reserves, fire again to take him, then fire on a pitch position to put
 * him there.  Fire on a filled position lifts that player so he can be
 * dropped somewhere else, which is how two players are swapped.  Left and
 * right change screen.  When the eleven are picked, Enter moves on to the
 * two substitutes.
 *
 * All of it is drawn on the Oric HIRES bitmap: a full pitch outline with
 * the three bands of positions, and the reserve and substitute boxes.
 */
#include <string.h>
#include "fm2.h"
#include "ui.h"
#include "hires.h"

#define BOXW      42
#define BOXH      16
#define BOXX0     30
#define BOXX1     78
#define BOXX2     126
#define BOXX3     174

static unsigned char view;        /* VIEW_DEF / MID / ATT                 */
static unsigned char curs;        /* 0 pool, 1..4 zones, 5 keeper, 6..7   */
static unsigned char phase;       /* 0 the eleven, 1 the substitutes      */
static unsigned char held;        /* squad index in hand, or 0xFF         */
static unsigned char *origin;     /* slot he was lifted from, or 0        */
static unsigned char pick;        /* reserve being browsed, or 0xFF       */

/* Slot tops, on text-row boundaries so the labels sit inside the boxes. */
static const unsigned char band_y[3] = { 24, 64, 104 };

static const char *pos_name(unsigned char p)
{
    switch (p) {
    case POS_GK: return "G";
    case POS_DF: return "D";
    case POS_MF: return "M";
    default:     return "A";
    }
}

/* ---------------------------------------------------------------------- */
/* squad bookkeeping                                                       */

static unsigned char in_team(unsigned char i)
{
    unsigned char z;

    if (i == keeper)
        return 1;
    for (z = 0; z < ZONES; ++z)
        if (zone[z] == i)
            return 1;
    for (z = 0; z < NSUBS; ++z)
        if (subsel[z] == i)
            return 1;
    return 0;
}

static unsigned char eligible(unsigned char i)
{
    return (unsigned char)(i < squad_count && !in_team(i) &&
                           squad[i].fit >= 50);
}

/* Next free player from `from`, wrapping.  0xFF if there is none. */
static unsigned char next_free(unsigned char from)
{
    unsigned char i, n;

    for (n = 0; n < squad_count; ++n) {
        i = (unsigned char)((from + n) % squad_count);
        if (eligible(i))
            return i;
    }
    return 0xFF;
}

/* Previous free player, wrapping backwards. */
static unsigned char prev_free(unsigned char from)
{
    unsigned char i, n;

    for (n = 0; n < squad_count; ++n) {
        i = (unsigned char)((from + squad_count - 1 - n) % squad_count);
        if (eligible(i))
            return i;
    }
    return 0xFF;
}

static unsigned char first_free(void)
{
    return next_free(0);
}

static void formation(char *b)
{
    b[0] = (char)('0' + zone_players(VIEW_DEF));
    b[1] = '-';
    b[2] = (char)('0' + zone_players(VIEW_MID));
    b[3] = '-';
    b[4] = (char)('0' + zone_players(VIEW_ATT));
    b[5] = 0;
}

/* ---------------------------------------------------------------------- */
/* drawing                                                                 */

static void append_char(char *dst, char c)
{
    while (*dst)
        ++dst;
    dst[0] = c;
    dst[1] = 0;
}

static void clip7(char *dst, const char *src)
{
    unsigned char i = 0;

    while (i < 7 && src[i]) {
        dst[i] = src[i];
        ++i;
    }
    dst[i] = 0;
}

static void draw_pitch(void)
{
    unsigned char v, s, x0, y0;

    h_rect(24, 16, 216, 150);
    h_hline(24, 216, 83);
    h_hline(100, 140, 83);
    h_circle(120, 83, 14);

    h_rect(74, 16, 166, 34);
    h_rect(100, 16, 140, 25);
    h_rect(74, 132, 166, 150);
    h_rect(100, 141, 140, 150);
    h_rect(112, 13, 128, 16);
    h_rect(112, 150, 128, 153);

    /* the two bands you are not looking at, as small markers */
    for (v = 0; v < 3; ++v) {
        if (v == view)
            continue;
        for (s = 0; s < 4; ++s) {
            if (zone[v * 4 + s] == 0xFF)
                continue;
            x0 = (unsigned char)(BOXX0 + s * 48 + 20);
            y0 = (unsigned char)(band_y[v] + 8);
            h_spot(x0, y0, 2);
        }
    }
    if (view != VIEW_DEF && keeper != 0xFF)
        h_spot(119, 136, 2);
}

static void draw_slot(unsigned char x0, unsigned char y0, unsigned char idx,
                      unsigned char active)
{
    char n[8];
    char b[8];
    unsigned char col = (unsigned char)(x0 / 6);
    unsigned char row = (unsigned char)(y0 / 8);
    unsigned char top = (unsigned char)(y0 - 2);
    unsigned char bot = (unsigned char)(y0 + BOXH - 1);

    if (active)
        h_thick(x0, top, (unsigned char)(x0 + BOXW), bot);
    else
        h_rect(x0, top, (unsigned char)(x0 + BOXW), bot);

    if (idx != 0xFF && idx < squad_count) {
        clip7(n, squad[idx].name);
        h_text(col, row, n);
        b[0] = pos_name(squad[idx].pos)[0];
        b[1] = (char)('0' + squad[idx].skill);
        b[2] = ' ';
        b[3] = (char)('0' + squad[idx].fit / 10);
        b[4] = (char)('0' + squad[idx].fit % 10);
        b[5] = 0;
        h_text(col, (unsigned char)(row + 1), b);
    } else {
        h_text(col, row, "----");
        h_text(col, (unsigned char)(row + 1), "EMPTY");
    }
}

static void draw_pool(void)
{
    char line[41];
    char n[8];

    line[0] = 0;
    if (pick != 0xFF) {
        clip7(n, squad[pick].name);
        strcpy(line, "PICK ");
        str_append(line, n);
        str_append(line, " ");
        str_append(line, pos_name(squad[pick].pos));
        append_char(line, (char)('0' + squad[pick].skill));
        str_append(line, " FIT ");
        str_append(line, u2s(squad[pick].fit, n));
        str_append(line, "  ");
        str_append(line, u2s(squad[pick].value, n));
        str_append(line, "K");
    } else if (held != 0xFF) {
        clip7(n, squad[held].name);
        strcpy(line, "IN HAND ");
        str_append(line, n);
        str_append(line, " - PICK A POSITION");
    } else {
        strcpy(line, "RESERVE POOL - FIRE TO PICK A PLAYER");
    }
    if (curs == 0)
        h_texti(0, 1, line);
    else
        h_text(0, 1, line);
}

static void draw_subs(void)
{
    draw_slot(30, 152, subsel[0], (unsigned char)(curs == 6));
    draw_slot(126, 152, subsel[1], (unsigned char)(curs == 7));
}

static void draw_status(void)
{
    char f[6];

    formation(f);
    h_text(0, 22, "TEAM ");
    h_num(5, 22, num_selected(), 2);
    h_text(7, 22, "/11  ");
    h_text(12, 22, f);
    h_text(18, 22, " SUBS ");
    h_num(24, 22, (unsigned char)((subsel[0] != 0xFF) +
                                  (subsel[1] != 0xFF)), 2);
    h_text(26, 22, "/2");

    if (phase == 0 && selection_ok())
        h_text(0, 23, "ELEVEN PICKED - ENTER FOR SUBS");
    else if (phase == 1)
        h_text(0, 23, "SUBS: FIRE PICKS, ENTER CONFIRMS");
    else
        h_text(0, 23, "FILL EVERY POSITION");
}

static void draw_all(void)
{
    unsigned char s;

    h_clear();
    h_text(0, 0, "TEAM SELECTION");
    h_text(20, 0, view == VIEW_DEF ? "DEFENCE" :
                   (view == VIEW_MID ? "MIDFIELD" : "ATTACK"));
    h_text(30, 0, phase ? "SUBS" : "TEAM");

    draw_pitch();
    for (s = 0; s < 4; ++s)
        draw_slot((unsigned char)(BOXX0 + s * 48), band_y[view],
                  zone[view * 4 + s], (unsigned char)(curs == 1 + s));
    if (view == VIEW_DEF)
        draw_slot(96, 128, keeper, (unsigned char)(curs == 5));
    draw_subs();
    draw_pool();
    draw_status();
    h_text(0, 24, "Q/S SLOT  I/P VIEW  SPACE FIRE  ESC");
}

/* ---------------------------------------------------------------------- */
/* cursor                                                                  */

static unsigned char curs_ok(unsigned char c)
{
    if (c == 0)
        return 1;
    if (phase)
        return (unsigned char)(c >= 6);
    if (c <= 4)
        return 1;
    return (unsigned char)(c == 5 && view == VIEW_DEF);
}

static void curs_move(signed char dir)
{
    unsigned char c = curs;

    do {
        if (dir > 0)
            c = (unsigned char)(c < 7 ? c + 1 : 0);
        else
            c = (unsigned char)(c ? c - 1 : 7);
    } while (!curs_ok(c));
    curs = c;
}

static unsigned char slot_index(void)
{
    if (curs >= 1 && curs <= 4)
        return (unsigned char)(view * 4 + curs - 1);
    return 0xFF;
}

/* Put a lifted player back where he came from. */
static void restore_held(void)
{
    if (origin)
        *origin = held;
    held = 0xFF;
    origin = 0;
    auto_select_marks();
}

/* The player slot under the cursor, or 0. */
static unsigned char *slot_here(void)
{
    if (curs == 5)
        return &keeper;
    if (curs >= 6)
        return &subsel[curs - 6];
    if (curs >= 1 && curs <= 4)
        return &zone[view * 4 + curs - 1];
    return 0;
}

/* Put the player in hand into the position under the cursor. */
static void place_here(void)
{
    unsigned char *dest;
    unsigned char prev;

    if (held == 0xFF)
        return;
    if (curs == 5 && squad[held].pos != POS_GK) {
        snd_bad();
        return;
    }
    dest = slot_here();
    if (!dest)
        return;

    prev = *dest;
    *dest = held;
    /* Dropping onto an occupied position swaps the two, so the eleven
     * stay picked.  The goalkeeper only ever goes in goal. */
    if (origin && origin != dest && prev != 0xFF &&
        squad[prev].pos != POS_GK)
        *origin = prev;
    held = 0xFF;
    origin = 0;
    auto_select_marks();
}

/* Space: the fire button. */
static void fire(void)
{
    if (pick != 0xFF) {                 /* take the browsed reserve */
        held = pick;
        origin = 0;
        pick = 0xFF;
        if (phase == 1) {
            curs = (unsigned char)(subsel[0] == 0xFF ? 6 : 7);
        } else if (view == VIEW_DEF && keeper == 0xFF) {
            curs = 5;
        } else {
            unsigned char s;
            for (s = 0; s < 4; ++s)
                if (zone[view * 4 + s] == 0xFF) {
                    curs = (unsigned char)(1 + s);
                    return;
                }
        }
        return;
    }
    if (curs == 0) {
        pick = first_free();
        return;
    }
    if (held != 0xFF) {
        place_here();
        return;
    }
    /* Nothing in hand: lift the player under the cursor so he can be
     * dropped somewhere else, or start a pick if the slot is empty. */
    if (curs == 5) {
        if (keeper != 0xFF) {
            held = keeper;
            origin = &keeper;
            keeper = 0xFF;
            auto_select_marks();
        } else {
            pick = first_free();
        }
    } else if (curs >= 6) {
        if (subsel[curs - 6] != 0xFF) {
            held = subsel[curs - 6];
            origin = &subsel[curs - 6];
            subsel[curs - 6] = 0xFF;
            auto_select_marks();
        } else {
            pick = first_free();
        }
    } else {
        unsigned char z = slot_index();

        if (zone[z] != 0xFF) {
            held = zone[z];
            origin = &zone[z];
            zone[z] = 0xFF;
            auto_select_marks();
        } else {
            pick = first_free();
        }
    }
}

/* ---------------------------------------------------------------------- */

void team_selection(void)
{
    unsigned char k;

    view = VIEW_MID;
    curs = 1;
    phase = 0;
    held = 0xFF;
    origin = 0;
    pick = 0xFF;

    hires_on();
    for (;;) {
        draw_all();
        k = ui_key();

        if (k == K_ESC) {
            if (pick != 0xFF)
                pick = 0xFF;
            else if (held != 0xFF)
                restore_held();
            else
                break;
        } else if (k == 'Q' || k == K_UP) {
            if (pick != 0xFF)
                pick = prev_free(pick);
            else
                curs_move(-1);
        } else if (k == 'S' || k == K_DOWN) {
            if (pick != 0xFF)
                pick = next_free((unsigned char)(pick + 1));
            else
                curs_move(1);
        } else if (k == 'I' || k == K_LEFT) {
            if (phase) {
                curs = 6;
            } else {
                view = (unsigned char)(view ? view - 1 : 2);
                if (!curs_ok(curs))
                    curs = 1;
            }
        } else if (k == 'P' || k == K_RIGHT) {
            if (phase) {
                curs = 7;
            } else {
                view = (unsigned char)((view + 1) % 3);
                if (!curs_ok(curs))
                    curs = 1;
            }
        } else if (k == ' ') {
            fire();
        } else if (k == K_ENTER) {
            if (phase == 0 && selection_ok()) {
                phase = 1;
                curs = 6;
            } else if (phase == 1 && subsel[0] != 0xFF &&
                       subsel[1] != 0xFF) {
                break;
            } else {
                snd_bad();
            }
        } else if (k == 'A') {
            auto_select();
        }
    }
    hires_off();
}
