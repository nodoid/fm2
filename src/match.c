/*
 * match.c - FM2-style match action for Football Manager 2 (Oric).
 *
 * The match is a stream of short action sequences, as in the Spectrum
 * original: the ball is played out from midfield, a pass or a tackle
 * follows, and the sequence ends with a shot, a save or a goal.  Each
 * step is handed to the caller as a frame carrying the ball position and
 * a one-line commentary so the screen can animate it.
 *
 * The engine is integer-only and touches no hardware.
 */
#include <string.h>
#include "fm2.h"
#include "match.h"

/* match state */
static unsigned char m_home, m_away;
static unsigned char m_minute, m_hs, m_as;
static unsigned char m_ballx, m_bally;
static unsigned char m_half_done, m_done;
static unsigned char m_mid_h, m_mid_a, m_att_h, m_att_a, m_def_h, m_def_a;

/* goalscorers for the user's side */
static unsigned char m_scorers[8];
static unsigned char m_nscorers;

static unsigned char user_side(unsigned char side)
{
    return (unsigned char)(side ? (m_away == user_team) : (m_home == user_team));
}

/* queued frames for the current sequence */
static MatchFrame mq[3];
static unsigned char mq_head, mq_len;

unsigned char sim_goals(unsigned char att, unsigned char def)
{
    unsigned int p;
    unsigned char g = 0, i;

    p = (unsigned int)att * 40 / ((unsigned int)def + 40);
    if (p > 60)
        p = 60;
    for (i = 0; i < 6; ++i) {
        if (rnd_range(100) < p)
            ++g;
    }
    return g;
}

void quick_score(unsigned char home_str, unsigned char away_str,
                 unsigned char *hs, unsigned char *as)
{
    *hs = sim_goals(home_str, away_str);
    *as = sim_goals(away_str, home_str);
}

/* ---------------------------------------------------------------------- */

static void push(unsigned char kind, unsigned char side, unsigned char x,
                 unsigned char y)
{
    MatchFrame *f;

    if (mq_len >= 3)
        return;
    f = &mq[mq_head + mq_len];        /* mq_head is always 0 in practice */
    f->kind = kind;
    f->side = side;
    f->x = x;
    f->y = y;
    f->minute = m_minute;
    f->hs = m_hs;
    f->as = m_as;
    m_ballx = x;
    m_bally = y;
    ++mq_len;
}

/* How many midfielders the user has in the side chosen for this attack. */
static unsigned char mid_rating(unsigned char side)
{
    return side ? m_mid_a : m_mid_h;
}

static unsigned char attack_rating(unsigned char side)
{
    return side ? m_att_a : m_att_h;
}

/* A user-side player in the given view, or 0xFF. */
static unsigned char user_player(unsigned char view)
{
    unsigned char z, i;
    unsigned char count = 0;

    for (z = (unsigned char)(view * 4); z < (unsigned char)(view * 4 + 4); ++z)
        if (zone[z] != 0xFF && zone[z] < squad_count)
            ++count;
    if (!count)
        return 0xFF;
    count = (unsigned char)(rnd_range(count) + 1);
    for (z = (unsigned char)(view * 4); z < (unsigned char)(view * 4 + 4); ++z) {
        i = zone[z];
        if (i != 0xFF && i < squad_count) {
            if (--count == 0)
                return i;
        }
    }
    return 0xFF;
}

/* Create the frames for one attacking move. */
static void make_attack(void)
{
    unsigned char side;
    unsigned char x, y;

    mq_len = 0;
    mq_head = 0;

    /* who wins the midfield? */
    side = (unsigned char)(rnd_range((unsigned char)(mid_rating(0) + mid_rating(1) + 1))
                           < mid_rating(0) ? 0 : 1);

    x = (unsigned char)(side ? 28 : 11);
    y = (unsigned char)(2 + rnd_range(4));
    push(M_PASS, side, x, y);

    /* the move develops toward goal */
    x = (unsigned char)(side ? 20 : 19);
    y = (unsigned char)(2 + rnd_range(4));
    push(M_PASS, side, x, y);

    x = (unsigned char)(side ? 14 : 25);
    y = (unsigned char)(2 + rnd_range(4));

    /* tackle or shot */
    if (rnd_range(100) < 35) {
        /* the defending side wins it back */
        push(M_TACKLE, (unsigned char)!side, x, y);
        return;
    }

    {
        unsigned char mine = user_side(side);
        unsigned char p = (unsigned char)((side ? 10 : 12) + attack_rating(side) / 2);
        unsigned char scorer = mine ? user_player(VIEW_ATT) : 0xFF;

        x = (unsigned char)(side ? (rnd_range(3) ? 6 : 9) : (rnd_range(3) ? 33 : 30));
        y = (unsigned char)(3 + rnd_range(2));
        if (rnd_range(100) < p) {
            if (side)
                ++m_as;
            else
                ++m_hs;
            if (mine && m_nscorers < 8 && scorer != 0xFF)
                m_scorers[m_nscorers++] = scorer;
            push(M_GOAL, side, (unsigned char)(side ? 2 : 37), 4);
            mq[mq_len - 1].hs = m_hs;
            mq[mq_len - 1].as = m_as;
        } else if (rnd_range(3) == 0) {
            push(M_MISS, side, x, 1);
        } else {
            push(M_SAVE, (unsigned char)!side,
                 (unsigned char)(side ? 3 : 36), 4);
        }
    }
}

static void next_minute(void)
{
    m_minute = (unsigned char)(m_minute + 2 + rnd_range(5));
    if (m_minute > 90)
        m_minute = 90;
}

void match_begin(unsigned char home, unsigned char away)
{
    m_home = home;
    m_away = away;
    m_minute = 0;
    m_hs = 0;
    m_as = 0;
    m_ballx = 20;
    m_bally = 4;
    m_half_done = 0;
    m_done = 0;
    mq_len = 0;
    mq_head = 0;

    {
        unsigned char umid = (unsigned char)(view_strength(VIEW_MID) * 4 + 12);
        unsigned char uatt = (unsigned char)(view_strength(VIEW_ATT) * 3 + 8);
        unsigned char udef = (unsigned char)(view_strength(VIEW_DEF) * 3 + 10 +
                                             (keeper != 0xFF ? player_eff(keeper) : 0));
        unsigned char omid = (unsigned char)(league[away].str / 2);
        unsigned char oatt = (unsigned char)(league[away].str / 2);
        unsigned char odef = (unsigned char)(league[away].str / 2);

        if (home == user_team) {
            m_mid_h = umid; m_att_h = uatt; m_def_h = udef;
            m_mid_a = omid; m_att_a = oatt; m_def_a = odef;
        } else {
            m_mid_h = omid; m_att_h = oatt; m_def_h = odef;
            m_mid_a = umid; m_att_a = uatt; m_def_a = udef;
        }
    }
    m_nscorers = 0;

}

unsigned char match_next(MatchFrame *f)
{
    if (mq_len) {
        *f = mq[0];
        --mq_len;
        {
            unsigned char i;
            for (i = 0; i < mq_len; ++i)
                mq[i] = mq[i + 1];
        }
        return 1;
    }
    if (m_done)
        return 0;

    if (m_minute == 0) {
        f->kind = M_KICKOFF;
        f->side = 0;
        f->x = 20;
        f->y = 4;
        f->minute = 0;
        f->hs = 0;
        f->as = 0;
        m_minute = 2;
        return 1;
    }
    if (!m_half_done && m_minute >= 45) {
        m_half_done = 1;
        f->kind = M_HALF;
        f->side = 2;
        f->x = 20;
        f->y = 4;
        f->minute = 45;
        f->hs = m_hs;
        f->as = m_as;
        m_minute = 46;
        return 1;
    }
    if (m_minute >= 90) {
        m_done = 1;
        f->kind = M_FULL;
        f->side = 2;
        f->x = 20;
        f->y = 4;
        f->minute = 90;
        f->hs = m_hs;
        f->as = m_as;
        return 1;
    }

    make_attack();
    next_minute();
    return match_next(f);
}

unsigned char match_score_home(void)
{
    return m_hs;
}

unsigned char match_score_away(void)
{
    return m_as;
}

/* Apply the result: appearances, goals and tiredness for the user's side. */
void match_finish(void)
{
    unsigned char i;

    for (i = 0; i < squad_count; ++i) {
        if (!sel[i])
            continue;
        ++squad[i].apps;
        if (squad[i].fit > 12)
            squad[i].fit = (unsigned char)(squad[i].fit - 12);
        else
            squad[i].fit = 0;
    }
    for (i = 0; i < m_nscorers; ++i)
        if (m_scorers[i] < squad_count)
            ++squad[m_scorers[i]].goals;
}
