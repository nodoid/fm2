/*
 * game.c - Football Manager 2 core (portable C).
 *
 * No hardware access lives here: the same source is used by the Oric
 * build and by the sim65 unit tests.
 *
 * The four divisions hold twenty clubs each.  Fixtures are not stored:
 * a round-robin is generated arithmetically from the club's position in
 * its division, which keeps the data small enough for a 37K machine.
 */
#include <string.h>
#include "fm2.h"
#include "match.h"

/* ---------------------------------------------------------------------- */
/* data tables                                                            */
/* ---------------------------------------------------------------------- */

static const char *const club_names[NUM_TEAMS] = {
    /* Division 1 */
    "ARSENAL",     "LIVERPOOL",   "EVERTON",       "MAN UTD",
    "TOTTENHAM",   "CHELSEA",     "MAN CITY",      "ASTON VILLA",
    "LEEDS",       "NEWCASTLE",   "WEST HAM",      "SOUTHAMPTON",
    "NOTTINGHAM F", "SHEFFIELD W", "SUNDERLAND",   "NORWICH",
    "WIMBLEDON",   "QPR",         "COVENTRY",      "WATFORD",
    /* Division 2 */
    "DERBY",       "OXFORD UTD",  "LUTON",         "PORTSMOUTH",
    "IPSWICH",     "LEICESTER",   "BIRMINGHAM",    "CRYSTAL PAL",
    "BLACKBURN",   "STOKE",       "SWINDON",       "BARNSLEY",
    "HULL",        "BRADFORD",    "PLYMOUTH",      "BRIGHTON",
    "MILLWALL",    "CHARLTON",    "OLDHAM",        "SWANSEA",
    /* Division 3 */
    "BOURNEMOUTH", "BRISTOL C",   "BURY",          "CHESTER",
    "GILLINGHAM",  "PRESTON",     "WALSALL",       "WIGAN",
    "YORK",        "SHREWSBURY",  "BOLTON",        "CARDIFF",
    "FULHAM",      "GRIMSBY",     "HUDDERSFIELD",  "MANSFIELD",
    "NORTHAMPTON", "ROTHERHAM",   "SOUTHEND",      "STOCKPORT",
    /* Division 4 */
    "ALDERSHOT",   "BURNLEY",     "CAMBRIDGE",     "COLCHESTER",
    "CREWE",       "DONCASTER",   "EXETER",        "HALIFAX",
    "HARTLEPOOL",  "HEREFORD",    "LEYTON O",      "LINCOLN",
    "PETERBOROUGH", "ROCHDALE",   "SCUNTHORPE",    "TORQUAY",
    "TRANMERE",    "WREXHAM",     "CARLISLE",      "DARLINGTON"
};

static const char *const surnames[] = {
    "SMITH", "JONES", "BROWN", "TAYLOR", "WILSON", "DAVIES",
    "EVANS", "THOMAS", "ROBERTS", "WALKER", "WRIGHT", "ROBINSON",
    "THOMPSON", "HUGHES", "EDWARDS", "GREEN", "HALL", "WOOD",
    "HARRIS", "CLARKE", "JACKSON", "TURNER", "HILL", "MOORE",
    "COOPER", "WARD", "MORRIS", "KING", "BAKER", "ADAMS",
    "NELSON", "CARTER"
};
#define NSUR (sizeof surnames / sizeof surnames[0])

/* The club starts with 14 players: 2 goalkeepers, 4 defenders, 4
 * midfielders and 4 attackers.  Two more can be signed. */
#define START_SQUAD 14
static const unsigned char start_pos[START_SQUAD] = {
    POS_GK, POS_GK,
    POS_DF, POS_DF, POS_DF, POS_DF,
    POS_MF, POS_MF, POS_MF, POS_MF,
    POS_FW, POS_FW, POS_FW, POS_FW
};

/* ---------------------------------------------------------------------- */
/* state                                                                   */
/* ---------------------------------------------------------------------- */

Team league[NUM_TEAMS];
Player squad[SQUAD_SIZE];
unsigned char squad_count;
unsigned char keeper;
unsigned char zone[ZONES];
unsigned char subsel[NSUBS];
unsigned char sel[SQUAD_SIZE];
unsigned int cash;
unsigned char user_team;
unsigned char pass_hi;
unsigned char pass_len;
unsigned char round_num;
unsigned char season;
unsigned char last_round;
unsigned char board_confidence;

static unsigned char res_round = 0xFF;

unsigned char res_h[MPR], res_a[MPR];
unsigned char res_hs[MPR], res_as[MPR];
unsigned char res_valid[MPR];

Target market[MARKET_SIZE];
char news[64];

Cup fa_cup, league_cup;
unsigned char cup_won;

SaveGame saveblk;

unsigned int rng_state;

/* ---------------------------------------------------------------------- */
/* random                                                                  */
/* ---------------------------------------------------------------------- */

void rng_seed(unsigned int s)
{
    rng_state = s ? s : 0xACE1;
}

unsigned int rnd16(void)
{
    unsigned int x = rng_state;

    x ^= (unsigned int)(x << 7);
    x ^= (unsigned int)(x >> 9);
    x ^= (unsigned int)(x << 8);
    rng_state = x;
    return x;
}

unsigned char rnd8(void)
{
    return (unsigned char)(rnd16() & 0xFF);
}

unsigned char rnd_range(unsigned char n)
{
    if (!n)
        return 0;
    return (unsigned char)(rnd16() % n);
}

/* ---------------------------------------------------------------------- */
/* small string helpers (no printf in the Oric build)                      */
/* ---------------------------------------------------------------------- */

char *u2s(unsigned int v, char *buf)
{
    char tmp[6];
    unsigned char n = 0;

    if (v == 0) {
        buf[0] = '0';
        buf[1] = 0;
        return buf;
    }
    while (v && n < 5) {
        tmp[n++] = (char)('0' + (v % 10));
        v = (unsigned int)(v / 10);
    }
    {
        unsigned char i = 0;
        while (n)
            buf[i++] = tmp[--n];
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

void make_player_name(char *dst, unsigned char pos, unsigned char n)
{
    const char *s;

    (void)pos;
    (void)n;
    dst[0] = (char)('A' + rnd_range(26));
    dst[1] = '.';
    s = surnames[rnd_range((unsigned char)NSUR)];
    {
        unsigned char i = 0;
        while (s[i] && i < 7) {
            dst[2 + i] = s[i];
            ++i;
        }
        dst[2 + i] = 0;
    }
}

/* ---------------------------------------------------------------------- */
/* setup                                                                   */
/* ---------------------------------------------------------------------- */

void league_reset(void)
{
    unsigned char i;

    for (i = 0; i < NUM_TEAMS; ++i) {
        league[i].played = 0;
        league[i].won = 0;
        league[i].drawn = 0;
        league[i].lost = 0;
        league[i].gf = 0;
        league[i].ga = 0;
        league[i].points = 0;
    }
    for (i = 0; i < MPR; ++i) {
        res_h[i] = 0;
        res_a[i] = 0;
        res_hs[i] = 0;
        res_as[i] = 0;
        res_valid[i] = 0;
    }
    last_round = 0xFF;
    res_round = 0xFF;
}

/* Fill the four divisions with their clubs. */
void league_setup(void)
{
    unsigned char i;

    for (i = 0; i < NUM_TEAMS; ++i) {
        unsigned char div = (unsigned char)(i / TEAMS_PER_DIV);

        strcpy(league[i].name, club_names[i]);
        /* a spread of strength inside each division */
        league[i].str = (unsigned char)(92 - div * 13 - (i % 8) + 4);
    }
}

static void make_squad(unsigned char div)
{
    unsigned char i;

    squad_count = START_SQUAD;
    for (i = 0; i < START_SQUAD; ++i) {
        Player *p = &squad[i];

        make_player_name(p->name, start_pos[i], i);
        p->pos = start_pos[i];
        p->skill = (unsigned char)(3 + rnd_range(7));
        p->fit = (unsigned char)(72 + rnd_range(29));
        p->goals = 0;
        p->apps = 0;
        p->value = (unsigned int)(p->skill * 30 + rnd_range(61) + div * 8);
    }
}

void new_game(unsigned char team)
{
    unsigned char i;

    if (team >= NUM_TEAMS)
        team = 0;
    user_team = team;

    league_setup();
    league_reset();

    cash = 250;
    pass_hi = 3;
    pass_len = 3;
    round_num = 0;
    season = 1;
    board_confidence = 60;
    cup_won = 0;
    keeper = 0xFF;
    for (i = 0; i < ZONES; ++i)
        zone[i] = 0xFF;
    for (i = 0; i < NSUBS; ++i)
        subsel[i] = 0xFF;

    make_squad((unsigned char)(team / TEAMS_PER_DIV));
    auto_select();
    cup_setup(&fa_cup, team);
    cup_setup(&league_cup, team);
    refresh_market();
    strcpy(news, "WELCOME TO THE CLUB");
}

/* ---------------------------------------------------------------------- */
/* fixtures: round robin by arithmetic                                     */
/* ---------------------------------------------------------------------- */

/* Circle method.  Club 0..n-1 of a division; round r in 0..n-2, tie m. */
static void circle_pair(unsigned char n, unsigned char r, unsigned char m,
                        unsigned char *a, unsigned char *b)
{
    if (m == 0) {
        *a = (unsigned char)(n - 1);
        *b = r;
    } else {
        *a = (unsigned char)((r + m) % (n - 1));
        *b = (unsigned char)((r + n - 1 - m) % (n - 1));
    }
}

void fixtures_for(unsigned char div, unsigned char round,
                  unsigned char *home, unsigned char *away)
{
    unsigned char m, a, b;
    unsigned char base = (unsigned char)(div * TEAMS_PER_DIV);

    for (m = 0; m < MPR; ++m) {
        circle_pair(TEAMS_PER_DIV, round, m, &a, &b);
        if ((round + m) & 1) {
            home[m] = (unsigned char)(base + b);
            away[m] = (unsigned char)(base + a);
        } else {
            home[m] = (unsigned char)(base + a);
            away[m] = (unsigned char)(base + b);
        }
    }
}

unsigned char find_user_fixture(unsigned char round,
                                unsigned char *home,
                                unsigned char *away)
{
    unsigned char h[MPR], a[MPR], m;

    if (round >= ROUNDS)
        return 0;
    fixtures_for((unsigned char)(user_team / TEAMS_PER_DIV), round, h, a);
    for (m = 0; m < MPR; ++m) {
        if (h[m] == user_team || a[m] == user_team) {
            *home = h[m];
            *away = a[m];
            return 1;
        }
    }
    return 0;
}

void apply_result(unsigned char home, unsigned char away,
                  unsigned char hs, unsigned char as)
{
    Team *h = &league[home];
    Team *a = &league[away];

    ++h->played;
    ++a->played;
    h->gf = (unsigned char)(h->gf + hs);
    h->ga = (unsigned char)(h->ga + as);
    a->gf = (unsigned char)(a->gf + as);
    a->ga = (unsigned char)(a->ga + hs);
    if (hs > as) {
        ++h->won;
        ++a->lost;
        h->points += 3;
    } else if (hs < as) {
        ++a->won;
        ++h->lost;
        a->points += 3;
    } else {
        ++h->drawn;
        ++a->drawn;
        ++h->points;
        ++a->points;
    }
}

/* Clear the stored results when the current round changes. */
void start_round(unsigned char round)
{
    unsigned char m;

    if (res_round == round)
        return;
    res_round = round;
    for (m = 0; m < MPR; ++m)
        res_valid[m] = 0;
}

/* Play every other tie of the user's division for this round. */
void play_other_matches(unsigned char round, unsigned char skip_user)
{
    unsigned char h[MPR], a[MPR], m;

    if (round >= ROUNDS)
        return;
    start_round(round);
    fixtures_for((unsigned char)(user_team / TEAMS_PER_DIV), round, h, a);
    for (m = 0; m < MPR; ++m) {
        unsigned char hs, as;

        if (skip_user && (h[m] == user_team || a[m] == user_team))
            continue;
        if (res_valid[m])
            continue;
        quick_score((unsigned char)(league[h[m]].str + 6), league[a[m]].str,
                    &hs, &as);
        res_h[m] = h[m];
        res_a[m] = a[m];
        res_hs[m] = hs;
        res_as[m] = as;
        res_valid[m] = 1;
        apply_result(h[m], a[m], hs, as);
    }
}

/* Play one complete round of every division (used when the user's match
 * has already been played). */
void play_league_round(unsigned char round)
{
    unsigned char d, m;
    unsigned char mydiv = (unsigned char)(user_team / TEAMS_PER_DIV);

    if (round >= ROUNDS)
        return;
    for (d = 0; d < DIVS; ++d) {
        unsigned char h[MPR], a[MPR];

        if (d == mydiv)
            continue;                  /* the caller plays that one */
        fixtures_for(d, round, h, a);
        for (m = 0; m < MPR; ++m) {
            unsigned char hs, as;

            quick_score((unsigned char)(league[h[m]].str + 6), league[a[m]].str,
                        &hs, &as);
            apply_result(h[m], a[m], hs, as);
        }
    }
}

/* ---------------------------------------------------------------------- */
/* table                                                                   */
/* ---------------------------------------------------------------------- */

static signed char better(unsigned char x, unsigned char y)
{
    Team *a = &league[x];
    Team *b = &league[y];
    int gda, gdb;

    if (a->points != b->points)
        return (signed char)(a->points > b->points);
    gda = (int)a->gf - (int)a->ga;
    gdb = (int)b->gf - (int)b->ga;
    if (gda != gdb)
        return (signed char)(gda > gdb);
    if (a->gf != b->gf)
        return (signed char)(a->gf > b->gf);
    return (signed char)(strcmp(a->name, b->name) < 0);
}

void sort_table(unsigned char div, unsigned char *order)
{
    unsigned char i, j;
    unsigned char base = (unsigned char)(div * TEAMS_PER_DIV);

    for (i = 0; i < TEAMS_PER_DIV; ++i)
        order[i] = (unsigned char)(base + i);
    for (i = 0; i < TEAMS_PER_DIV - 1; ++i) {
        for (j = (unsigned char)(i + 1); j < TEAMS_PER_DIV; ++j) {
            if (better(order[j], order[i])) {
                unsigned char t = order[i];
                order[i] = order[j];
                order[j] = t;
            }
        }
    }
}

unsigned char user_position(void)
{
    unsigned char order[TEAMS_PER_DIV];
    unsigned char i;

    sort_table((unsigned char)(user_team / TEAMS_PER_DIV), order);
    for (i = 0; i < TEAMS_PER_DIV; ++i)
        if (order[i] == user_team)
            return (unsigned char)(i + 1);
    return TEAMS_PER_DIV;
}

/* ---------------------------------------------------------------------- */
/* squad                                                                   */
/* ---------------------------------------------------------------------- */

unsigned char squad_size(void)
{
    return squad_count;
}

Player *player(unsigned char i)
{
    return &squad[i];
}

/* FM2 treats a player used out of position as skill 2. */
unsigned char player_eff(unsigned char i)
{
    Player *p = &squad[i];
    unsigned char v;

    if (!sel[i])
        return 0;
    v = p->skill;
    if (p->pos == POS_GK)
        v = (unsigned char)(v + 1);
    if (p->fit < 50)
        v = (unsigned char)(v / 2);
    else if (p->fit < 70)
        --v;
    return v;
}

static unsigned char in_zone(unsigned char i)
{
    unsigned char z;

    for (z = 0; z < ZONES; ++z)
        if (zone[z] == i)
            return 1;
    return 0;
}

unsigned char num_selected(void)
{
    unsigned char i, n = 0;

    for (i = 0; i < squad_count; ++i)
        if (sel[i])
            ++n;
    return n;
}

unsigned char selection_ok(void)
{
    unsigned char i, gk = 0, out = 0;

    if (keeper == 0xFF)
        return 0;
    for (i = 0; i < squad_count; ++i) {
        if (!sel[i])
            continue;
        if (squad[i].pos == POS_GK)
            ++gk;
        else
            ++out;
        if (squad[i].fit < 50)
            return 0;
    }
    return (unsigned char)(gk == 1 && out == 10);
}

unsigned char zone_players(unsigned char view)
{
    unsigned char z, n = 0;

    for (z = (unsigned char)(view * 4); z < (unsigned char)(view * 4 + 4); ++z)
        if (zone[z] != 0xFF)
            ++n;
    return n;
}

unsigned char view_strength(unsigned char view)
{
    unsigned char z, total = 0;

    for (z = (unsigned char)(view * 4); z < (unsigned char)(view * 4 + 4); ++z) {
        unsigned char i = zone[z];
        if (i != 0xFF && i < squad_count)
            total = (unsigned char)(total + player_eff(i));
    }
    return total;
}

/* Pick the best available player for a position. */
static unsigned char best_at(unsigned char pos, unsigned char *used)
{
    unsigned char i, best = 0xFF;
    unsigned char bestv = 0;

    for (i = 0; i < squad_count; ++i) {
        unsigned char v;

        if (used[i] || squad[i].pos != pos || squad[i].fit < 50)
            continue;
        v = squad[i].skill;
        if (v > bestv) {
            bestv = v;
            best = i;
        }
    }
    return best;
}

void auto_select(void)
{
    unsigned char used[SQUAD_SIZE];
    unsigned char i, z;

    for (i = 0; i < SQUAD_SIZE; ++i) {
        used[i] = 0;
        sel[i] = 0;
    }
    for (z = 0; z < ZONES; ++z)
        zone[z] = 0xFF;
    for (i = 0; i < NSUBS; ++i)
        subsel[i] = 0xFF;

    keeper = best_at(POS_GK, used);
    if (keeper != 0xFF) {
        used[keeper] = 1;
        sel[keeper] = 1;
    }
    /* 4 defenders, 4 midfielders, 2 attackers: 4-4-2 */
    for (z = 0; z < 4; ++z) {
        unsigned char p = best_at(POS_DF, used);
        if (p != 0xFF) {
            zone[z] = p;
            used[p] = 1;
            sel[p] = 1;
        }
    }
    for (z = 4; z < 8; ++z) {
        unsigned char p = best_at(POS_MF, used);
        if (p != 0xFF) {
            zone[z] = p;
            used[p] = 1;
            sel[p] = 1;
        }
    }
    for (z = 8; z < 10; ++z) {
        unsigned char p = best_at(POS_FW, used);
        if (p != 0xFF) {
            zone[z] = p;
            used[p] = 1;
            sel[p] = 1;
        }
    }
    /* two substitutes: the best two left */
    {
        unsigned char n = 0;
        for (i = 0; i < squad_count && n < NSUBS; ++i) {
            if (!used[i] && squad[i].fit >= 50) {
                subsel[n] = i;
                used[i] = 1;
                ++n;
            }
        }
    }
    auto_select_marks();
}

void auto_select_marks(void)
{
    unsigned char i;

    for (i = 0; i < squad_count; ++i)
        sel[i] = (unsigned char)(i == keeper || in_zone(i));
}

unsigned char team_attack(void)
{
    unsigned char a = view_strength(VIEW_ATT);
    unsigned char m = view_strength(VIEW_MID);

    return (unsigned char)((a * 2 + m) / 3 + 20);
}

unsigned char team_defence(void)
{
    unsigned char d = view_strength(VIEW_DEF);
    unsigned char m = view_strength(VIEW_MID);
    unsigned char g = (keeper != 0xFF) ? player_eff(keeper) : 0;

    return (unsigned char)((d * 2 + m + g * 2) / 4 + 20);
}

unsigned char total_wages(void)
{
    unsigned char i;
    unsigned int w = 0;

    for (i = 0; i < squad_count; ++i)
        w += (unsigned int)(squad[i].skill * 2 + 4);
    return (unsigned char)(w ? (w / 2) : 0);
}

static unsigned char clamp100(int v)
{
    if (v < 0)
        return 0;
    if (v > 100)
        return 100;
    return (unsigned char)v;
}

void train_week(void)
{
    unsigned char i;

    for (i = 0; i < squad_count; ++i) {
        Player *p = &squad[i];
        int v = (int)p->fit + 2;

        if (sel[i])
            v -= 3;                    /* matches take it out of them */
        p->fit = clamp100(v);
    }
}

void age_squad(void)
{
    unsigned char i;

    for (i = 0; i < squad_count; ++i) {
        Player *p = &squad[i];

        p->goals = 0;
        p->apps = 0;
        p->fit = clamp100((int)p->fit + 8);
    }
}

/* ---------------------------------------------------------------------- */
/* transfers                                                               */
/* ---------------------------------------------------------------------- */

unsigned char player_value(unsigned char i)
{
    return (unsigned char)(squad[i].value > 255 ? 255 : squad[i].value);
}

void refresh_market(void)
{
    unsigned char i;

    for (i = 0; i < MARKET_SIZE; ++i) {
        Target *t = &market[i];
        unsigned char pos = (unsigned char)(rnd_range(4));

        make_player_name(t->name, pos, i);
        t->pos = pos;
        t->skill = (unsigned char)(4 + rnd_range(6));
        t->value = (unsigned int)(t->skill * 35 + rnd_range(50));
    }
}

unsigned char buy_player(unsigned char idx)
{
    unsigned char i;

    if (idx >= MARKET_SIZE || squad_count >= SQUAD_SIZE)
        return 0;
    if (cash < market[idx].value)
        return 0;
    cash -= market[idx].value;
    strcpy(squad[squad_count].name, market[idx].name);
    squad[squad_count].pos = market[idx].pos;
    squad[squad_count].skill = market[idx].skill;
    squad[squad_count].fit = 95;
    squad[squad_count].goals = 0;
    squad[squad_count].apps = 0;
    squad[squad_count].value = market[idx].value;
    ++squad_count;
    for (i = idx; i + 1 < MARKET_SIZE; ++i)
        market[i] = market[i + 1];
    make_player_name(market[MARKET_SIZE - 1].name,
                     (unsigned char)rnd_range(4), MARKET_SIZE);
    market[MARKET_SIZE - 1].pos = (unsigned char)rnd_range(4);
    market[MARKET_SIZE - 1].skill = (unsigned char)(4 + rnd_range(6));
    market[MARKET_SIZE - 1].value = (unsigned int)(market[MARKET_SIZE - 1].skill * 35 + rnd_range(50));
    strcpy(news, "SIGNING COMPLETED");
    return 1;
}

unsigned char sell_player(unsigned char idx)
{
    unsigned char z, v;

    if (idx >= squad_count || squad_count <= 11)
        return 0;
    v = (unsigned char)(squad[idx].value > 255 ? 255 : squad[idx].value);
    cash += v;
    if (keeper == idx)
        keeper = 0xFF;
    for (z = 0; z < ZONES; ++z) {
        if (zone[z] == idx)
            zone[z] = 0xFF;
        else if (zone[z] != 0xFF && zone[z] > idx)
            --zone[z];
    }
    {
        unsigned char i;
        for (i = 0; i < NSUBS; ++i) {
            if (subsel[i] == idx)
                subsel[i] = 0xFF;
            else if (subsel[i] != 0xFF && subsel[i] > idx)
                --subsel[i];
        }
        for (i = idx; i + 1 < squad_count; ++i) {
            squad[i] = squad[i + 1];
            sel[i] = sel[i + 1];
        }
        --squad_count;
        sel[squad_count] = 0;
    }
    strcpy(news, "PLAYER SOLD");
    return 1;
}

/* ---------------------------------------------------------------------- */
/* cups                                                                    */
/* ---------------------------------------------------------------------- */

void cup_setup(Cup *c, unsigned char seed_team)
{
    unsigned char i, j;

    c->n = CUP_SIZE;
    c->round = 0;
    c->teams[0] = seed_team;
    for (i = 1; i < CUP_SIZE; ++i) {
        unsigned char t;

        do {
            t = (unsigned char)rnd_range(NUM_TEAMS);
            for (j = 0; j < i; ++j)
                if (c->teams[j] == t)
                    break;
        } while (j < i);
        c->teams[i] = t;
    }
    for (i = 0; i < CUP_TIES; ++i) {
        c->hs[i] = 0;
        c->as[i] = 0;
    }
}

/* Shuffle the surviving clubs so the ties look like a fresh draw. */
void cup_draw(Cup *c)
{
    unsigned char i;

    for (i = c->n; i > 1; --i) {
        unsigned char j = (unsigned char)rnd_range(i);
        unsigned char t = c->teams[i - 1];
        c->teams[i - 1] = c->teams[j];
        c->teams[j] = t;
    }
}

unsigned char cup_user_tie(Cup *c, unsigned char *opponent, unsigned char *home)
{
    unsigned char i;

    if (c->n < 2)
        return 0;
    for (i = 0; i + 1 < c->n; i += 2) {
        if (c->teams[i] == user_team) {
            *opponent = c->teams[i + 1];
            *home = 1;
            return 1;
        }
        if (c->teams[i + 1] == user_team) {
            *opponent = c->teams[i];
            *home = 0;
            return 1;
        }
    }
    return 0;
}

/* Simulate the round.  The user's score is supplied; returns the number of
 * ties the user won (1) or a replay (2), 0 if knocked out. */
unsigned char cup_play_round(Cup *c, unsigned char user_hs, unsigned char user_as,
                             unsigned char *out_hs, unsigned char *out_as)
{
    unsigned char i, tied = 0, user_win = 0;

    *out_hs = user_hs;
    *out_as = user_as;
    for (i = 0; i + 1 < c->n; i += 2) {
        unsigned char h = c->teams[i], a = c->teams[i + 1];
        unsigned char hs, as;

        if (h == user_team || a == user_team) {
            hs = user_hs;
            as = user_as;
            if (hs == as) {
                /* a replay: give it to the home side on the toss of a coin */
                if (rnd_range(2))
                    ++hs;
                else
                    ++as;
                tied = 2;
            }
            *out_hs = hs;
            *out_as = as;
        } else {
            quick_score((unsigned char)(league[h].str + 6), league[a].str,
                        &hs, &as);
            if (hs == as) {
                if (rnd_range(2))
                    ++hs;
                else
                    ++as;
            }
        }
        c->hs[i / 2] = hs;
        c->as[i / 2] = as;
    }
    /* the winners go through in bracket order */
    {
        unsigned char k = 0;
        for (i = 0; i + 1 < c->n; i += 2) {
            unsigned char h = c->teams[i], a = c->teams[i + 1];
            unsigned char w;

            w = (c->hs[i / 2] > c->as[i / 2]) ? h : a;
            c->teams[k++] = w;
            if (w == user_team)
                user_win = 1;
        }
        c->n = k;
    }
    ++c->round;
    if (tied == 2 && user_win)
        return 2;
    return user_win;
}

/* Which cups play this week, as a bitmask (1 FA, 2 League). */
unsigned char cup_week(unsigned char round)
{
    unsigned char mask = 0;

    if (fa_cup.n >= 2 && round >= 3 && ((round - 3) % 4) == 0)
        mask |= 1;
    if (league_cup.n >= 2 && round >= 1 && ((round - 1) % 4) == 0)
        mask |= 2;
    return mask;
}

/* ---------------------------------------------------------------------- */
/* finances                                                                */
/* ---------------------------------------------------------------------- */

unsigned int week_end(unsigned char was_home)
{
    unsigned int wages = total_wages();
    unsigned int gate = 0;
    char b[6];

    cash += 20;                       /* sponsorship */
    if (was_home) {
        unsigned int att;
        unsigned char pos = user_position();
        unsigned char div = (unsigned char)(user_team / TEAMS_PER_DIV);

        att = 22000 - (unsigned int)div * 3500 - (unsigned int)pos * 250
              + rnd_range(1500);
        if (att > 32000)
            att = 32000;
        gate = att / 400;
        cash += gate;
    }

    strcpy(news, was_home ? "GATE " : "AWAY WEEK ");
    if (was_home) {
        str_append(news, u2s(gate, b));
        str_append(news, "K ");
    }
    str_append(news, "WAGES ");
    str_append(news, u2s(wages, b));
    str_append(news, "K");

    if (cash < wages) {
        cash = 0;
        strcpy(news, "THE BANK HAS CALLED IN THE DEBT!");
    } else {
        cash -= wages;
    }

    train_week();
    if ((round_num & 3) == 0)
        refresh_market();
    return gate;
}

unsigned char prize_money(void)
{
    unsigned char pos = user_position();

    return (unsigned char)((TEAMS_PER_DIV + 1 - pos) * 8 + (pos == 1 ? 60 : 0));
}

void season_finish(void)
{
    unsigned char pos = user_position();
    unsigned int prize = prize_money();
    char b[6];

    cash += prize;
    strcpy(news, "SEASON OVER - FINISHED ");
    str_append(news, u2s(pos, b));
    str_append(news, " PRIZE ");
    str_append(news, u2s(prize, b));
    str_append(news, "K");
}

/* Three up, three down between neighbouring divisions.  Clubs are swapped
 * between the division slots, and the user's club is followed by name. */
static void swap_clubs(unsigned char a, unsigned char b)
{
    Team t;

    memcpy(&t, &league[a], sizeof(Team));
    memcpy(&league[a], &league[b], sizeof(Team));
    memcpy(&league[b], &t, sizeof(Team));
}

void promote_relegate(void)
{
    unsigned char d;
    char myname[13];
    unsigned char i;

    strcpy(myname, league[user_team].name);
    for (d = 0; d + 1 < DIVS; ++d) {
        unsigned char up_order[TEAMS_PER_DIV];
        unsigned char down_order[TEAMS_PER_DIV];
        unsigned char k;

        sort_table(d, up_order);          /* upper division */
        sort_table((unsigned char)(d + 1), down_order);   /* lower */
        for (k = 0; k < 3; ++k) {
            /* top three of the lower division change places with the
             * bottom three of the upper one */
            swap_clubs(down_order[k], up_order[TEAMS_PER_DIV - 1 - k]);
        }
    }
    for (i = 0; i < NUM_TEAMS; ++i)
        if (strcmp(league[i].name, myname) == 0) {
            user_team = i;
            break;
        }
}

void new_season(void)
{
    unsigned char i;

    age_squad();
    league_reset();
    for (i = 0; i < ZONES; ++i)
        zone[i] = 0xFF;
    round_num = 0;
    ++season;
    auto_select();
    cup_setup(&fa_cup, user_team);
    cup_setup(&league_cup, user_team);
    refresh_market();
}

/* ---------------------------------------------------------------------- */
/* save / restore                                                          */
/* ---------------------------------------------------------------------- */

void save_game_state(void)
{
    unsigned char i;

    saveblk.magic = SAVE_MAGIC;
    saveblk.version = SAVE_VERSION;
    saveblk.user_team = user_team;
    saveblk.round_num = round_num;
    saveblk.season = season;
    saveblk.last_round = last_round;
    saveblk.pass_hi = pass_hi;
    saveblk.pass_len = pass_len;
    saveblk.squad_count = squad_count;
    saveblk.keeper = keeper;
    saveblk.board_confidence = board_confidence;
    saveblk.cup_won = cup_won;
    saveblk.cash = cash;
    saveblk.rng_state = rng_state;

    for (i = 0; i < NUM_TEAMS; ++i)
        saveblk.league[i] = league[i];
    for (i = 0; i < SQUAD_SIZE; ++i)
        saveblk.squad[i] = squad[i];
    for (i = 0; i < ZONES; ++i)
        saveblk.zone[i] = zone[i];
    for (i = 0; i < NSUBS; ++i)
        saveblk.subsel[i] = subsel[i];
    saveblk.fa_cup = fa_cup;
    saveblk.league_cup = league_cup;
}

unsigned char save_valid(void)
{
    return (unsigned char)(saveblk.magic == SAVE_MAGIC &&
                           saveblk.version == SAVE_VERSION);
}

unsigned char load_game_state(void)
{
    unsigned char i;

    if (!save_valid())
        return 0;
    user_team = saveblk.user_team;
    round_num = saveblk.round_num;
    season = saveblk.season;
    last_round = saveblk.last_round;
    pass_hi = saveblk.pass_hi;
    pass_len = saveblk.pass_len;
    squad_count = saveblk.squad_count;
    keeper = saveblk.keeper;
    board_confidence = saveblk.board_confidence;
    cup_won = saveblk.cup_won;
    cash = saveblk.cash;
    rng_state = saveblk.rng_state;

    for (i = 0; i < NUM_TEAMS; ++i)
        league[i] = saveblk.league[i];
    for (i = 0; i < SQUAD_SIZE; ++i)
        squad[i] = saveblk.squad[i];
    for (i = 0; i < ZONES; ++i)
        zone[i] = saveblk.zone[i];
    for (i = 0; i < NSUBS; ++i)
        subsel[i] = saveblk.subsel[i];
    fa_cup = saveblk.fa_cup;
    league_cup = saveblk.league_cup;
    auto_select_marks();
    refresh_market();
    return 1;
}
