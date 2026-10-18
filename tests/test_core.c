/*
 * test_core.c - unit tests for the Football Manager 2 core.
 *
 * Two ways to run them:
 *
 *   sim65 (host, fast):
 *     cl65 -t sim6502 -O -o build/test_core.prg tests/test_core.c \
 *          src/game.c src/match.c
 *     sim65 build/test_core.prg          (exit code = failed checks)
 *
 *   on the machine (real 6502):
 *     cl65 -t atmos -O -C oric.cfg -D ORIC_TEST=1 -o build/selftest.tap \
 *          tests/test_core.c src/game.c src/match.c src/ui.c src/scr.s \
 *          src/kbd.s src/snd.s
 *     then CLOAD the tape: the results appear on screen.
 */
#include <string.h>
#include "fm2.h"
#include "match.h"

#ifdef ORIC_TEST
#include "ui.h"
#else
#include <stdio.h>
#endif

static unsigned int fails;
static unsigned int checks;
#ifdef ORIC_TEST
static unsigned char row_y = 2;
#endif

static void say(const char *s)
{
#ifdef ORIC_TEST
    if (row_y > 26)
        row_y = 3;
    ui_gotoxy(0, row_y);
    ui_fill(row_y, ' ');
    ui_gotoxy(0, row_y);
    ui_puts(s);
    ++row_y;
#else
    printf("%s\n", s);
#endif
}

static void ok(unsigned char cond, const char *what)
{
    ++checks;
    if (!cond) {
        ++fails;
        say(what);
        say("  *** FAILED ***");
    }
#ifndef ORIC_TEST
    else {
        printf("ok   %s\n", what);
    }
#else
    (void)what;
#endif
}

static void check_eq(unsigned int got, unsigned int want, const char *what)
{
    if (got != want) {
        char b1[24], b2[24];
        say(what);
        u2s(got, b1);
        str_append(b1, " WANTED");
        u2s(want, b2);
        str_append(b1, " ");
        str_append(b1, b2);
        say(b1);
        ++checks;
        ++fails;
    } else {
        ok(1, what);
    }
}

/* ---------------------------------------------------------------------- */

static void test_rng(void)
{
    unsigned char i;
    unsigned char seen[4];
    unsigned int a;

    rng_seed(1);
    a = rnd16();
    rng_seed(1);
    check_eq(rnd16() == a, 1, "rng is reproducible");
    rng_seed(2);
    ok(rnd16() != a, "different seeds differ");

    rng_seed(1234);
    for (i = 0; i < 4; ++i)
        seen[i] = 0;
    for (i = 0; i < 200; ++i) {
        unsigned char v = rnd_range(4);
        if (v > 3) {
            ok(0, "rnd_range stays in range");
            return;
        }
        seen[v] = 1;
    }
    ok((unsigned char)(seen[0] && seen[1] && seen[2] && seen[3]),
       "rnd_range covers 0..3");
    ok(rnd_range(0) == 0, "rnd_range(0) is 0");
}

static void test_strings(void)
{
    char b[8];
    char n[12];

    check_eq(strcmp(u2s(0, b), "0"), 0, "u2s 0");
    check_eq(strcmp(u2s(7, b), "7"), 0, "u2s 7");
    check_eq(strcmp(u2s(123, b), "123"), 0, "u2s 123");
    check_eq(strcmp(u2s(32000, b), "32000"), 0, "u2s 32000");

    rng_seed(99);
    make_player_name(n, POS_MF, 0);
    ok(strlen(n) <= 9, "player name fits");
    ok(n[1] == '.', "player name is initial dot surname");
    ok(n[0] >= 'A' && n[0] <= 'Z', "player initial is a capital");
}

static void test_setup(void)
{
    unsigned char i, gk = 0, df = 0, mf = 0, fw = 0;

    rng_seed(4242);
    league_setup();
    for (i = 0; i < NUM_TEAMS; ++i) {
        ok(league[i].name[0] != 0, "club has a name");
        ok(strlen(league[i].name) <= 12, "club name fits column");
    }

    new_game(60);                      /* a Division 4 club */
    check_eq(user_team, 60, "user team stored");
    check_eq(squad_size(), 14, "starting squad size");
    check_eq(cash, 250, "starting cash");
    check_eq(pass_hi, 3, "passing height starts neutral");
    check_eq(pass_len, 3, "passing length starts neutral");

    for (i = 0; i < squad_size(); ++i) {
        Player *p = player(i);
        switch (p->pos) {
        case POS_GK: ++gk; break;
        case POS_DF: ++df; break;
        case POS_MF: ++mf; break;
        default:     ++fw; break;
        }
        ok(p->skill >= 3 && p->skill <= 9, "skill is 3 to 9");
        ok(p->fit <= 100, "fitness in range");
        ok(p->value >= 30 && p->value <= 360, "value in FM2 range");
    }
    ok(gk >= 2, "at least two keepers");
    ok(df >= 3, "at least three defenders");
    ok(mf >= 3, "at least three midfielders");
    ok(fw >= 2, "at least two attackers");

    check_eq(num_selected(), 11, "auto select picks eleven");
    ok(selection_ok(), "auto selected team is valid");
    ok(team_attack() > 20 && team_attack() < 120, "attack rating sensible");
    ok(team_defence() > 20 && team_defence() < 120, "defence rating sensible");
}

static void test_zones(void)
{
    unsigned char i, z;

    new_game(61);
    check_eq(zone_players(VIEW_DEF), 4, "four defenders in zones");
    check_eq(zone_players(VIEW_MID), 4, "four midfielders in zones");
    check_eq(zone_players(VIEW_ATT), 2, "two attackers in zones");
    check_eq(num_selected(), 11, "zones plus keeper make eleven");

    /* a zone can be emptied */
    zone[VIEW_DEF * 4] = 0xFF;
    auto_select_marks();
    check_eq(num_selected(), 10, "empty zone removes a player");
    ok(!selection_ok(), "ten players is not a valid team");

    /* and refilled */
    for (i = 0; i < squad_count; ++i) {
        if (squad[i].pos == POS_DF && !sel[i]) {
            zone[VIEW_DEF * 4] = i;
            break;
        }
    }
    auto_select_marks();
    ok(selection_ok(), "filling the zone repairs the team");

    /* a player cannot stand in two zones */
    zone[VIEW_MID * 4] = zone[VIEW_DEF * 4];
    auto_select_marks();
    check_eq(num_selected(), 10, "duplicate zone entry does not double count");
    (void)z;

    auto_select();
    ok(selection_ok(), "auto select repairs everything");

    /* out-of-position players still count */
    keeper = 0xFF;
    auto_select_marks();
    ok(!selection_ok(), "no keeper is rejected");
    auto_select();
    ok(selection_ok(), "auto select finds a keeper");
}

static void test_fixtures(void)
{
    unsigned char r, m, i, j, d;
    static unsigned char met[TEAMS_PER_DIV][TEAMS_PER_DIV];

    for (d = 0; d < DIVS; ++d) {
        for (i = 0; i < TEAMS_PER_DIV; ++i)
            for (j = 0; j < TEAMS_PER_DIV; ++j)
                met[i][j] = 0;

        for (r = 0; r < ROUNDS; ++r) {
            unsigned char h[MPR], a[MPR];
            unsigned char seen[TEAMS_PER_DIV];

            for (i = 0; i < TEAMS_PER_DIV; ++i)
                seen[i] = 0;
            fixtures_for(d, r, h, a);
            for (m = 0; m < MPR; ++m) {
                unsigned char hi = (unsigned char)(h[m] - d * TEAMS_PER_DIV);
                unsigned char ai = (unsigned char)(a[m] - d * TEAMS_PER_DIV);

                ok(hi != ai, "no club plays itself");
                ok(!seen[hi] && !seen[ai], "club appears once per round");
                ok(h[m] / TEAMS_PER_DIV == d && a[m] / TEAMS_PER_DIV == d,
                   "fixture stays in its division");
                seen[hi] = 1;
                seen[ai] = 1;
                ++met[hi][ai];
                ++met[ai][hi];
            }
        }
        for (i = 0; i < TEAMS_PER_DIV; ++i)
            for (j = 0; j < TEAMS_PER_DIV; ++j)
                if (i != j)
                    check_eq(met[i][j], 1, "every pair meets once");
    }
}

static void test_results_and_table(void)
{
    unsigned char order[TEAMS_PER_DIV];
    unsigned char i;
    unsigned char base = 60;

    rng_seed(77);
    new_game(60);
    apply_result((unsigned char)(base + 1), (unsigned char)(base + 2), 3, 0);
    check_eq(league[base + 1].points, 3, "win is three points");
    check_eq(league[base + 2].points, 0, "loss is no points");
    check_eq(league[base + 1].gf, 3, "goals for recorded");
    check_eq(league[base + 2].ga, 3, "goals against recorded");
    apply_result((unsigned char)(base + 3), (unsigned char)(base + 4), 1, 1);
    check_eq(league[base + 3].points, 1, "draw is one point");
    check_eq(league[base + 3].played, 1, "played counted");

    sort_table(3, order);
    ok(order[0] == base + 1 || league[order[0]].points >= league[order[1]].points,
       "table sorted by points");
    for (i = 0; i < TEAMS_PER_DIV; ++i)
        ok(order[i] / TEAMS_PER_DIV == 3, "table only holds one division");
}

static void test_action(void)
{
    unsigned char frames = 0, goals_h = 0, goals_a = 0;
    unsigned char saw_half = 0, saw_full = 0;
    MatchFrame f;
    unsigned char i;
    unsigned char before_fit;

    new_game(62);
    auto_select();
    before_fit = squad[keeper].fit;
    match_begin(62, 63);

    for (i = 0; i < 200; ++i) {
        if (!match_next(&f))
            break;
        ++frames;
        ok(f.x < 40, "ball x on the pitch");
        ok(f.y < 8, "ball y on the pitch");
        ok(strlen(f.text) <= FRAME_LEN, "commentary fits the line");
        if (f.kind == M_HALF)
            saw_half = 1;
        if (f.kind == M_FULL)
            saw_full = 1;
        if (f.kind == M_GOAL) {
            if (f.side)
                ++goals_a;
            else
                ++goals_h;
        }
        ok(f.minute <= 90, "minute in range");
    }
    ok(frames > 8, "a match produces action");
    ok(saw_half, "half time is reached");
    ok(saw_full, "full time is reached");
    check_eq(match_score_home(), goals_h, "home score matches the goals");
    check_eq(match_score_away(), goals_a, "away score matches the goals");
    ok(match_score_home() < 12 && match_score_away() < 12, "score is sane");

    match_finish();
    ok(squad[keeper].fit < before_fit, "a match tires the side");
    ok(squad[keeper].apps > 0, "appearances are counted");
}

static void test_cups(void)
{
    unsigned char i, j, unique;
    unsigned char opp, home;

    rng_seed(303);
    new_game(64);
    check_eq(fa_cup.n, CUP_SIZE, "cup holds thirty two clubs");
    unique = 1;
    for (i = 0; i < CUP_SIZE; ++i) {
        if (fa_cup.teams[i] == user_team)
            continue;
        for (j = 0; j < CUP_SIZE; ++j)
            if (j != i && fa_cup.teams[j] == fa_cup.teams[i])
                unique = 0;
    }
    ok(unique, "no club is drawn twice");
    ok(cup_user_tie(&fa_cup, &opp, &home), "the user is in the cup");

    /* play the whole cup; somebody must win it */
    for (i = 0; i < CUP_ROUNDS; ++i) {
        unsigned char hs = 1, as = 0, oh, oa;
        cup_play_round(&fa_cup, hs, as, &oh, &oa);
    }
    check_eq(fa_cup.n, 1, "the cup ends with one winner");
    ok(fa_cup.teams[0] < NUM_TEAMS, "winner is a real club");
}

static void test_week_and_money(void)
{
    unsigned int before, after;
    unsigned char i;

    new_game(65);
    for (i = 0; i < 20; ++i)
        squad[0].skill = 5;
    before = cash;
    after = week_end(1);
    ok(cash != before, "a home week changes the bank balance");
    ok(after > 0, "a home match pays gate money");

    before = cash;
    week_end(0);
    ok(cash < before, "an away week costs money");

    ok(total_wages() > 0, "wages are paid");
    check_eq(prize_money() > 0, 1, "prize money is positive");
}

static void test_transfers(void)
{
    unsigned char i, n;

    new_game(66);
    cash = 500;
    n = squad_count;
    for (i = 0; i < MARKET_SIZE; ++i)
        market[i].value = 10;
    ok(buy_player(0), "a player can be signed");
    check_eq(squad_count, (unsigned char)(n + 1), "squad grows");
    ok(cash < 500, "the fee is paid");

    cash = 0;
    ok(!buy_player(0), "cannot sign without cash");

    n = squad_count;
    ok(sell_player(0), "a player can be sold");
    check_eq(squad_count, (unsigned char)(n - 1), "squad shrinks");

    /* the board will not let the squad fall below eleven */
    while (squad_count > 11)
        sell_player(0);
    ok(!sell_player(0), "cannot sell below eleven players");
}

static void test_save_state(void)
{
    unsigned char i;

    new_game(67);
    cash = 321;
    round_num = 5;
    pass_hi = 5;
    pass_len = 1;
    zone[0] = 3;
    if (fa_cup.teams[0] == 0xFF)
        fa_cup.teams[0] = 5;
    save_game_state();
    for (i = 0; i < NUM_TEAMS; ++i)
        league[i].points = 0;
    cash = 0;
    round_num = 0;
    pass_hi = 1;
    zone[0] = 0xFF;

    ok(load_game_state(), "save block loads");
    check_eq(cash, 321, "cash restored");
    check_eq(round_num, 5, "round restored");
    check_eq(pass_hi, 5, "passing height restored");
    check_eq(zone[0], 3, "zones restored");
    check_eq(league[user_team].points, 0, "table restored");

    {
        unsigned int m = saveblk.magic;
        saveblk.magic = 0;
        ok(!save_valid(), "bad magic is rejected");
        saveblk.magic = m;
    }
}

static void test_season(void)
{
    unsigned char i, r;

    rng_seed(808);
    new_game(68);
    for (r = 0; r < ROUNDS; ++r) {
        unsigned char h, a;

        if (find_user_fixture(r, &h, &a)) {
            apply_result(h, a, 1, 0);
            play_other_matches(r, 1);
        }
    }
    {
        unsigned char base = (unsigned char)(user_team / TEAMS_PER_DIV * TEAMS_PER_DIV);
        for (i = 0; i < TEAMS_PER_DIV; ++i)
            check_eq(league[base + i].played, ROUNDS, "division played every round");
    }
    {
        unsigned char p = user_position();
        ok(p >= 1 && p <= TEAMS_PER_DIV, "position is in range");
    }

    /* promotion and relegation keep the club count and the user's club */
    {
        char myname[13];
        unsigned char s = season;

        strcpy(myname, league[user_team].name);
        promote_relegate();
        ok(strcmp(league[user_team].name, myname) == 0,
           "the user follows their club");
        check_eq(league[69].played, ROUNDS, "clubs keep their records");
        new_season();
        check_eq(season, (unsigned char)(s + 1), "season counter advances");
        check_eq(round_num, 0, "new season starts at round zero");
        check_eq(league[0].played, 0, "new season clears the table");
        ok(selection_ok(), "new season re-selects the team");
    }
}

/* ---------------------------------------------------------------------- */

static void run_all(void)
{
    test_rng();
    test_strings();
    test_setup();
    test_zones();
    test_fixtures();
    test_results_and_table();
    test_action();
    test_cups();
    test_week_and_money();
    test_transfers();
    test_save_state();
    test_season();
}

#ifdef ORIC_TEST
int main(void)
{
    kbd_init();
    snd_init();
    scr_init();
    ui_clear();
    ui_bar_center(0, "FM2 SELF TEST", 0x14);
    run_all();

    lb_reset();
    lb_str("CHECKS ");
    lb_num(checks, 3, ' ');
    lb_str("  FAILURES ");
    lb_num(fails, 3, ' ');
    lb_draw(0, 22);
    if (fails)
        ui_bar_center(24, "SELF TEST FAILED", 0x13);
    else
        ui_bar_center(24, "ALL SELF TESTS PASSED", 0x02);
    ui_footer("PRESS A KEY");
    ui_key();
    return 0;
}
#else
int main(void)
{
    run_all();
    printf("%d checks, %d failures\n", (int)checks, (int)fails);
    return (int)(fails & 0xFF);
}
#endif
