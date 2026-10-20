/*
 * main.c - screens and game flow for Football Manager 2 (Oric Atmos).
 *
 * The interface follows the Spectrum original: one management screen
 * with numbered options, a twelve-zone team selection across defence,
 * midfield and attack, passing-height/length training, and a match
 * played out as animated action sequences on a HIRES pitch.
 */
#include <string.h>
#include "fm2.h"
#include "match.h"
#include "ui.h"
#include "hires.h"
#include "select.h"
#include "action.h"

static char b[8];

/* ---------------------------------------------------------------------- */
/* cassette save and load                                                  */
/* ---------------------------------------------------------------------- */

unsigned char tape_save(void)
{
    save_game_state();
    tape_ptr = (unsigned char *)&saveblk;
    tape_len = (unsigned int)sizeof(SaveGame);
    strcpy(tape_name, "FM2SAVE");
    return tape_save_block();
}

unsigned char tape_load_game(void)
{
    tape_ptr = (unsigned char *)&saveblk;
    tape_len = (unsigned int)sizeof(SaveGame);
    strcpy(tape_name, "FM2SAVE");
    if (!tape_load_block())
        return 0;
    return load_game_state();
}

/* ---------------------------------------------------------------------- */
/* small helpers                                                           */
/* ---------------------------------------------------------------------- */

static const char *pos_name(unsigned char p)
{
    switch (p) {
    case POS_GK: return "G";
    case POS_DF: return "D";
    case POS_MF: return "M";
    default:     return "A";
    }
}

static unsigned char div_of(unsigned char t)
{
    return (unsigned char)(t / TEAMS_PER_DIV);
}

/* A menu row: " 1  NAME          extra". */
static void menu_row(unsigned char num, const char *name, const char *extra,
                     unsigned char extra_col)
{
    lb_reset();
    lb_num(num, 2, ' ');
    lb_str("  ");
    lb_str(name);
    lb_pad(extra_col);
    lb_str_clip(extra, 39);
}

static void frame(void)
{
    ui_clear();
    ui_header();
}

static void is_up_or(unsigned char k, unsigned char *hit)
{
    *hit = (unsigned char)(is_up(k) || k == 'Q');
}

/* ---------------------------------------------------------------------- */
/* title                                                                   */
/* ---------------------------------------------------------------------- */

static unsigned char title_screen(unsigned int *seed)
{
    unsigned char k, up;
    unsigned int spin;

    for (;;) {
        spin = 0;
        ui_clear();
        ui_bar_center(2, "FOOTBALL MANAGER 2", ATTR_BAR);
        ui_bar_center(3, "FOR THE ORIC ATMOS", ATTR_YEL);
        ui_center(10, "1  NEW GAME");
        ui_center(11, "2  LOAD GAME");
        ui_center(12, "3  INSTRUCTIONS");
        ui_center(15, "ESC  QUIT TO BASIC");
        ui_center(19, "(C) 2026 P F JOHNSON");
        ui_center(20, "ORIGINAL BY ADDICTIVE SOFTWARE");
        ui_help("PRESS A KEY");
        ui_footer("1 2 3 OR ESC");

        while (!(k = kbd_get()))
            ++spin;
        *seed = (unsigned int)(spin ^ (unsigned int)((unsigned int)k << 8)
                               ^ 0x5A5A);
        snd_click();
        is_up_or(k, &up);
        (void)up;
        if (k == '1')
            return 0;
        if (k == '2')
            return 1;
        if (k == '3')
            return 2;
        if (k == K_ESC)
            return 3;
    }
}

static void instructions_screen(void)
{
    ui_clear();
    ui_bar_center(0, "INSTRUCTIONS", ATTR_BAR);
    ui_gotoxy(1, 2);  ui_puts("MANAGE ONE CLUB FOR A SEASON.");
    ui_gotoxy(1, 4);  ui_puts("1 SQUAD  2 TEAM  3 TRAINING");
    ui_gotoxy(1, 5);  ui_puts("4 BUY  5 SELL  6 MATCH  7 TABLE");
    ui_gotoxy(1, 6);  ui_puts("8 RESULTS  9 FINANCE  0 SAVE");
    ui_gotoxy(1, 8);  ui_puts("SKILL 3-9. OUT OF POSITION IS 2.");
    ui_gotoxy(1, 9);  ui_puts("FITNESS BELOW 50 AND HE IS OUT.");
    ui_gotoxy(1, 11); ui_puts("TWELVE ZONES: FILL ONE TO MARK.");
    ui_footer("ESC BACK");
    while (ui_key() != K_ESC)
        ;
}

/* ---------------------------------------------------------------------- */
/* club choice - Division 4                                                */
/* ---------------------------------------------------------------------- */

static unsigned char club_select(void)
{
    unsigned char div = (unsigned char)(DIVS - 1), cur = 0, k, i;

    for (;;) {
        unsigned char base = (unsigned char)(div * TEAMS_PER_DIV);

        ui_clear();
        lb_reset();
        lb_str("CHOOSE YOUR CLUB - DIVISION ");
        lb_num((unsigned int)(div + 1), 1, ' ');
        lb_pad(39);
        ui_attr(0, ATTR_BAR);
        lb_draw(0, 0);
        for (i = 0; i < TEAMS_PER_DIV; ++i) {
            lb_reset();
            lb_ch(' ');
            lb_num((unsigned int)(i + 1), 2, ' ');
            lb_str("  ");
            lb_str(team_name((unsigned char)(base + i)));
            ui_item_lb((unsigned char)(2 + i), (unsigned char)(i == cur));
        }
        ui_pause(150);
        ui_help("LEFT/RIGHT CHANGES DIVISION");
        ui_footer("1-4 DIV   Q/S MOVE   ENTER   ESC");
        k = ui_key();
        if (k >= '1' && k < (char)('1' + DIVS)) {
            div = (unsigned char)(k - '1');
            cur = 0;
        } else if (k == K_LEFT || k == K_RIGHT) {
            if (k == K_LEFT)
                div = (unsigned char)(div ? div - 1 : DIVS - 1);
            else
                div = (unsigned char)((div + 1) % DIVS);
            cur = 0;
        } else {
            unsigned char up;
            is_up_or(k, &up);
            if (up && cur)
                --cur;
            else if (k == 'S' && cur + 1 < TEAMS_PER_DIV)
                ++cur;
            else if (k == K_ENTER)
                return (unsigned char)(base + cur);
            else if (k == K_ESC)
                return 0xFF;
        }
    }
}

/* ---------------------------------------------------------------------- */
/* kit colour                                                              */
/* ---------------------------------------------------------------------- */

/* The match screen colours the user's players with an ink attribute, so
 * the choice is one of the seven inks that show up on green. */
static const unsigned char kit_cols[] = { 1, 3, 4, 5, 6, 7 };

static void kit_select(void)
{
    unsigned char k;

    ui_clear();
    ui_bar_center(2, "KIT COLOUR", ATTR_BAR);
    ui_center(5, "1 RED   2 YELLOW   3 BLUE");
    ui_center(6, "4 MAGENTA  5 CYAN  6 WHITE");
    ui_footer("PRESS 1-6");
    do {
        k = ui_key();
    } while (k < '1' || k > '6');
    shirt = kit_cols[(unsigned char)(k - '1')];
}

/* ---------------------------------------------------------------------- */
/* sponsorship - offered at the start of every season                      */
/* ---------------------------------------------------------------------- */

static const char *const sponsor_names[] = {
    "PRISM", "ENDURANCE", "CORP", "OZONE",
    "MANTRA", "TANGERINE", "LEISURE", "KICK OFF"
};
#define NSPONSORS 8

void sponsor_offer(void)
{
    unsigned char again = 1;

    while (again) {
        unsigned char div = (unsigned char)(user_team / TEAMS_PER_DIV);
        unsigned int amount = (unsigned int)(DIVS - div) * 50;
        const char *name = sponsor_names[rnd8() % NSPONSORS];
        unsigned char k;

        again = 0;
        amount = (unsigned int)(amount - rnd_range(20));
        frame();
        ui_bar_center(2, "SPONSORSHIP OFFER", ATTR_BAR);
        ui_center(5, name);
        lb_reset();
        lb_str("WILL PAY ");
        lb_num(amount, 3, ' ');
        lb_str("K FOR THE SEASON");
        lb_draw(3, 7);
        ui_center(11, "ACCEPT THE OFFER?");
        ui_footer("Y SIGN   N ASK FOR MORE");

        do {
            k = ui_key();
        } while (k != 'Y' && k != 'N');

        if (k == 'Y') {
            cash += amount;
            strcpy(sponsor, name);
            strcpy(news, "SPONSOR SIGNS FOR THE SEASON");
            snd_click();
            return;
        }
        /* Turning a deal down only works while the board still rates you:
         * a manager rating of 100 gives a 75% chance of another offer. */
        if (board_confidence > 25 &&
            rnd_range(100) < (unsigned char)(25 + board_confidence / 2)) {
            again = 1;
        } else {
            sponsor[0] = 0;
            strcpy(news, "NO SPONSOR THIS SEASON");
        }
    }
}

/* ---------------------------------------------------------------------- */
/* team display                                                            */
/* ---------------------------------------------------------------------- */

static void squad_screen(void)
{
    unsigned char i;

    frame();
    ui_center(2, "TEAM DISPLAY");
    lb_reset();
    lb_str(" # NAME      POS SKILL FIT VAL");
    lb_draw(0, 3);
    for (i = 0; i < squad_count; ++i) {
        Player *p = &squad[i];

        lb_reset();
        lb_ch((char)('A' + i));
        lb_ch(' ');
        lb_str(p->name);
        lb_pad(11);
        lb_ch(' ');
        lb_str(pos_name(p->pos));
        lb_ch(' ');
        lb_num(p->skill, 2, ' ');
        lb_num(p->fit, 4, ' ');
        lb_num(p->value, 4, ' ');
        lb_str("K");
        ui_item_lb((unsigned char)(4 + i), (unsigned char)sel[i]);
    }
    ui_message("SKILL 3-9.  LETTERS PICK PLAYERS.");
    ui_footer("ESC BACK");
    wait_esc();
}

/* ---------------------------------------------------------------------- */
/* team selection - twelve zones                                           */
/* ---------------------------------------------------------------------- */


/* ---------------------------------------------------------------------- */
/* training: passing height and length                                     */
/* ---------------------------------------------------------------------- */

static void training_screen(void)
{
    unsigned char k;

    for (;;) {
        frame();
        ui_center(2, "TRAINING");
        lb_reset();
        lb_str("PASSING HEIGHT   ");
        lb_num(pass_hi, 1, ' ');
        lb_str(" / 5");
        lb_draw(0, 5);
        lb_reset();
        lb_str("PASSING LENGTH   ");
        lb_num(pass_len, 1, ' ');
        lb_str(" / 5");
        lb_draw(0, 7);

        ui_gotoxy(1, 10);
        ui_puts("HEIGHT: 1 KEEP IT DOWN   5 HIGH");
        ui_gotoxy(1, 11);
        ui_puts("LENGTH: 1 SHORT PASSES   5 LONG");
        ui_message("HIGH, LONG PASSES SUIT A QUICK");
        ui_help("SIDE.  SHORT PASSING SUITS SKILL.");
        ui_footer("H HEIGHT   L LENGTH   ESC BACK");

        k = ui_key();
        if (k == 'H') {
            pass_hi = (unsigned char)(pass_hi % 5 + 1);
        } else if (k == 'L') {
            pass_len = (unsigned char)(pass_len % 5 + 1);
        } else if (k == K_ESC) {
            return;
        }
    }
}

/* ---------------------------------------------------------------------- */
/* transfers                                                               */
/* ---------------------------------------------------------------------- */

static void buy_screen(void)
{
    unsigned char k, cur = 0;

    for (;;) {
        unsigned char i;

        frame();
        ui_center(2, "BUY PLAYER");
        for (i = 0; i < MARKET_SIZE; ++i) {
            lb_reset();
            lb_num((unsigned int)(i + 1), 2, ' ');
            lb_str("  ");
            lb_str(market[i].name);
            lb_pad(14);
            lb_str(pos_name(market[i].pos));
            lb_num(market[i].skill, 3, ' ');
            lb_num(market[i].value, 5, ' ');
            lb_str("K");
            ui_item_lb((unsigned char)(4 + i), (unsigned char)(i == cur));
        }
        lb_reset();
        lb_str("SQUAD ");
        lb_num(squad_count, 2, ' ');
        lb_str(" OF 16      CASH ");
        lb_num(cash, 4, ' ');
        lb_str("K");
        lb_draw(0, 9);
        ui_message("THREE PLAYERS ARE ON OFFER.");
        ui_help("BID FOR THE ONE YOU WANT.");
        ui_footer("Q/S MOVE   ENTER BID   ESC BACK");

        k = ui_key();
        {
            unsigned char up;
            is_up_or(k, &up);
            if (up && cur)
                --cur;
            else if (k == 'S' && cur + 1 < MARKET_SIZE)
                ++cur;
            else if (k == K_ENTER) {
                if (buy_player(cur))
                    snd_goal();
                else {
                    snd_bad();
                    strcpy(news, squad_count >= SQUAD_SIZE ?
                           "SQUAD TOO BIG" : "NOT ENOUGH CASH");
                }
            } else if (k == K_ESC)
                return;
        }
    }
}

static void sell_screen(void)
{
    unsigned char k, cur = 0;

    for (;;) {
        unsigned char i;

        frame();
        ui_center(2, "SELL PLAYER");
        for (i = 0; i < squad_count && i < 12; ++i) {
            lb_reset();
            lb_ch((char)('A' + i));
            lb_ch(' ');
            lb_str(squad[i].name);
            lb_pad(11);
            lb_str(pos_name(squad[i].pos));
            lb_num(squad[i].skill, 2, ' ');
            lb_num(squad[i].value, 5, ' ');
            lb_str("K");
            ui_item_lb((unsigned char)(4 + i), (unsigned char)(i == cur));
        }
        ui_message("SELLING A PLAYER RAISES CASH.");
        ui_help("THE BOARD WILL NOT ACCEPT A");
        ui_footer("Q/S MOVE   ENTER SELL   ESC BACK");

        k = ui_key();
        {
            unsigned char up;
            is_up_or(k, &up);
            if (up && cur)
                --cur;
            else if (k == 'S' && cur + 1 < squad_count)
                ++cur;
            else if (k == K_ENTER) {
                if (sell_player(cur)) {
                    snd_click();
                    if (cur + 1 > squad_count)
                        cur = 0;
                } else {
                    snd_bad();
                    strcpy(news, "THE BOARD SAYS NO");
                }
            } else if (k == K_ESC)
                return;
        }
    }
}

/* ---------------------------------------------------------------------- */
/* match action                                                            */
/* ---------------------------------------------------------------------- */

static void match_screen(unsigned char home, unsigned char away,
                         unsigned char cup)
{
    MatchFrame f;
    unsigned char running = 1;
    unsigned char flip = (unsigned char)(away == user_team);

    hires_on();
    action_begin(home, away, flip);
    match_begin(home, away);

    while (running) {
        if (!match_next(&f)) {
            running = 0;
            break;
        }
        if (f.kind == M_HALF) {
            action_frame(f.x, f.y, f.minute, f.hs, f.as, cup);
            ui_pause(20000);
            ui_pause(20000);
            action_end();               /* text mode for the team talk */
            ui_clear();
            ui_bar_center(0, "HALF TIME TEAM TALK", ATTR_BAR);
            ui_center(2, "CHANGE THE TEAM NOW?");
            ui_gotoxy(14, 5);
            ui_puts("1  TEAM SELECTION");
            ui_gotoxy(14, 6);
            ui_puts("2  CONTINUE");
            ui_footer("1 OR 2");
            {
                unsigned char c;
                do {
                    c = ui_key();
                } while (c != '1' && c != '2');
                if (c == '1')
                    team_selection();
            }
            hires_on();
            action_begin(home, away, flip);
            continue;
        }
        if (f.kind == M_FULL) {
            unsigned int n;

            action_frame(f.x, f.y, f.minute, f.hs, f.as, cup);
            /* Hold the final score until a key, but not forever if the
             * player has walked away. */
            for (n = 0; n < 60; ++n) {
                if (ui_key())
                    break;
                ui_pause(20000);
            }
            break;
        }

        action_frame(f.x, f.y, f.minute, f.hs, f.as, cup);
        if (f.kind == M_GOAL)
            snd_goal();
        else if (f.kind == M_TACKLE || f.kind == M_SAVE)
            snd_click();

        /* a short pause, or skip on a key press */
        {
            unsigned char i;
            for (i = 0; i < 3; ++i) {
                if (kbd_get())
                    break;
                ui_pause(4000);
            }
        }
    }
    action_end();
    ui_clear();
}

/* ---------------------------------------------------------------------- */
/* league table                                                            */
/* ---------------------------------------------------------------------- */

static void table_screen(void)
{
    unsigned char div = div_of(user_team), k;
    unsigned char order[TEAMS_PER_DIV];

    for (;;) {
        unsigned char i;

        frame();
        lb_reset();
        lb_str("LEAGUE TABLE       DIVISION ");
        lb_num((unsigned int)(div + 1), 1, ' ');
        lb_draw(0, 2);
        lb_reset();
        lb_str("PO NAME            P  W  D  L  F  A PT");
        lb_draw(0, 3);
        sort_table(div, order);
        for (i = 0; i < TEAMS_PER_DIV; ++i) {
            Team *t = &league[order[i]];
            unsigned char won = (unsigned char)((t->points - t->drawn) / 3);
            unsigned char lost = (unsigned char)(t->played - won - t->drawn);

            lb_reset();
            lb_num((unsigned int)(i + 1), 2, ' ');
            lb_ch(' ');
            lb_str(team_name(order[i]));
            lb_pad(19);
            lb_num(t->played, 2, ' ');
            lb_num(won, 3, ' ');
            lb_num(t->drawn, 3, ' ');
            lb_num(lost, 3, ' ');
            lb_num(t->gf, 3, ' ');
            lb_num(t->ga, 3, ' ');
            lb_num(t->points, 3, ' ');
            ui_item_lb((unsigned char)(4 + i), (unsigned char)(order[i] == user_team));
        }
        ui_help("3 UP, 3 DOWN.  LEFT/RIGHT DIVISION");
        ui_footer("ESC BACK");

        k = ui_key();
        if (k == K_ESC)
            return;
        if (k == K_LEFT && div)
            --div;
        else if (k == K_RIGHT && div + 1 < DIVS)
            ++div;
    }
}

/* ---------------------------------------------------------------------- */
/* results and fixtures                                                    */
/* ---------------------------------------------------------------------- */

static void results_screen(void)
{
    unsigned char k;

    for (;;) {
        unsigned char i;

        frame();
        lb_reset();
        lb_str("RESULTS AND FIXTURES    ROUND ");
        lb_num((unsigned int)(round_num + 1), 2, ' ');
        lb_draw(0, 2);
        for (i = 0; i < MPR && i < 10; ++i) {
            unsigned char fh[MPR], fa[MPR];

            fixtures_for(div_of(user_team), round_num, fh, fa);
            lb_reset();
            if (res_valid[i]) {
                lb_str(team_name(res_h[i]));
                lb_pad(14);
                lb_num(res_hs[i], 1, ' ');
                lb_ch('-');
                lb_num(res_as[i], 1, ' ');
                lb_ch(' ');
                lb_str(team_name(res_a[i]));
            } else {
                lb_str(team_name(fh[i]));
                lb_pad(14);
                lb_str("V ");
                lb_str(team_name(fa[i]));
            }
            lb_draw(0, (unsigned char)(4 + i));
        }
        ui_message(news);
        ui_help("LEAGUE RESULTS THIS ROUND.");
        ui_footer("ESC BACK");
        k = ui_key();
        if (k == K_ESC)
            return;
    }
}

/* ---------------------------------------------------------------------- */
/* finance                                                                 */
/* ---------------------------------------------------------------------- */

static void finance_screen(void)
{
    for (;;) {
        unsigned char k;

        frame();
        ui_center(2, "FINANCE");
        lb_reset();
        lb_str("CASH IN HAND       ");
        lb_num(cash, 4, ' ');
        lb_str("K");
        lb_draw(0, 5);
        lb_reset();
        lb_str("WEEKLY WAGES       ");
        lb_num(total_wages(), 4, ' ');
        lb_str("K");
        lb_draw(0, 6);
        lb_reset();
        lb_str("SPONSORSHIP        ");
        lb_num(20, 4, ' ');
        lb_str("K");
        lb_draw(0, 7);
        lb_reset();
        lb_str("BOARD CONFIDENCE   ");
        lb_num(board_confidence, 4, ' ');
        lb_str("%");
        lb_draw(0, 8);
        lb_reset();
        lb_str("POSITION           ");
        lb_num(user_position(), 2, ' ');
        lb_str(" IN DIVISION ");
        lb_num((unsigned int)(div_of(user_team) + 1), 1, ' ');
        lb_draw(0, 10);
        ui_message(news);
        ui_help("A NEGATIVE BALANCE GETS YOU SACKED.");
        ui_footer("ESC BACK");
        k = ui_key();
        if (k == K_ESC)
            return;
    }
}

/* ---------------------------------------------------------------------- */
/* management record                                                       */
/* ---------------------------------------------------------------------- */

static void record_screen(void)
{
    frame();
    ui_center(2, "MANAGEMENT RECORD");
    lb_reset();
    lb_str("SEASON            ");
    lb_num(season, 3, ' ');
    lb_draw(0, 5);
    lb_reset();
    lb_str("LEAGUE POSITION   ");
    lb_num(user_position(), 2, ' ');
    lb_draw(0, 6);
    lb_reset();
    lb_str("FA CUP            ");
    lb_str(cup_won & 1 ? "WINNERS" : "ENTERED");
    lb_draw(0, 7);
    lb_reset();
    lb_str("LEAGUE CUP        ");
    lb_str(cup_won & 2 ? "WINNERS" : "ENTERED");
    lb_draw(0, 8);
    ui_message("SUCCESS POINTS ARE AWARDED FOR");
    ui_help("LEAGUE PLACES AND CUP RUNS.");
    ui_footer("ESC BACK");
    wait_esc();
}

/* ---------------------------------------------------------------------- */
/* save and load                                                           */
/* ---------------------------------------------------------------------- */

static void save_screen(void)
{
    unsigned char k;

    for (;;) {
        frame();
        ui_center(2, "SAVE AND LOAD");
        ui_gotoxy(2, 5);  ui_puts("1  SAVE THE GAME TO TAPE");
        ui_gotoxy(2, 7);  ui_puts("2  LOAD A GAME FROM TAPE");
        ui_message("INSERT A BLANK TAPE TO SAVE.");
        ui_help("SAVE BEFORE EACH MATCH.");
        ui_footer("1 2 OR ESC");

        k = ui_key();
        if (k == '1') {
            save_game_state();
            kbd_suspend = 1;
            if (tape_save())
                strcpy(news, "SAVED TO TAPE");
            else
                strcpy(news, "SAVE FAILED");
            kbd_suspend = 0;
        } else if (k == '2') {
            strcpy(news, "INSERT THE SAVE TAPE");
            kbd_suspend = 1;
            if (tape_load_game())
                strcpy(news, "GAME LOADED");
            else
                strcpy(news, "NO SAVE FOUND");
            kbd_suspend = 0;
        } else if (k == K_ESC) {
            return;
        }
    }
}

/* ---------------------------------------------------------------------- */
/* playing a match day                                                     */
/* ---------------------------------------------------------------------- */

static unsigned char play_fixture(unsigned char home, unsigned char away,
                                  unsigned char cup)
{
    match_screen(home, away, cup);
    return 0;
}

static void season_over(void)
{
    season_finish();
    ui_clear();
    ui_bar_center(2, "SEASON OVER", ATTR_BAR);
    ui_center(5, news);
    ui_center(8, "PROMOTION AND RELEGATION");
    ui_center(9, "HAVE BEEN DECIDED.");
    ui_center(12, "PRESS SPACE FOR THE NEW SEASON");
    while (ui_key() != ' ')
        ;
    promote_relegate();
    new_season();
    sponsor_offer();
}

static void match_day(void)
{
    unsigned char home, away, hs, as;
    unsigned char cup_mask;

    if (!find_user_fixture(round_num, &home, &away)) {
        strcpy(news, "NO FIXTURE THIS WEEK");
        return;
    }

    start_round(round_num);
    play_fixture(home, away, 0);
    hs = match_score_home();
    as = match_score_away();
    match_finish();
    apply_result(home, away, hs, as);
    res_h[0] = home;
    res_a[0] = away;
    res_hs[0] = hs;
    res_as[0] = as;
    res_valid[0] = 1;
    play_other_matches(round_num, 1);
    play_league_round(round_num);

    if (hs > as) {
        board_confidence = (unsigned char)(board_confidence + 3 > 100 ? 100 : board_confidence + 3);
    } else if (hs < as) {
        board_confidence = (unsigned char)(board_confidence > 3 ? board_confidence - 3 : 0);
    }

    week_end((unsigned char)(home == user_team));

    {
        char b2[6];
        strcpy(news, hs > as ? "WIN " : (hs < as ? "LOSS " : "DRAW "));
        str_append(news, u2s(hs, b2));
        str_append(news, "-");
        str_append(news, u2s(as, b2));
        str_append(news, hs > as ? " WELL PLAYED" : "");
    }

    /* cup ties are played in the same week (midweek) */
    cup_mask = cup_week(round_num);
    if (cup_mask) {
        Cup *c = (cup_mask & 1) ? &fa_cup : &league_cup;
        unsigned char opp, at_home, chs, cas;

        if (cup_user_tie(c, &opp, &at_home)) {
            if (at_home) {
                play_fixture(user_team, opp, 1);
                chs = match_score_home();
                cas = match_score_away();
            } else {
                play_fixture(opp, user_team, 1);
                chs = match_score_away();
                cas = match_score_home();
            }
            match_finish();
            {
                unsigned char oh, oa;
                unsigned char won = cup_play_round(c, chs, cas, &oh, &oa);
                if (won) {
                    strcpy(news, "CUP TIE WON ");
                    str_append(news, u2s(oh, b));
                    str_append(news, "-");
                    str_append(news, u2s(oa, b));
                    if (c->n == 1) {
                        cup_won |= (cup_mask & 1) ? 1 : 2;
                        strcpy(news, "YOU HAVE WON THE CUP!");
                    }
                } else {
                    strcpy(news, "CUP TIE LOST ");
                    str_append(news, u2s(oh, b));
                    str_append(news, "-");
                    str_append(news, u2s(oa, b));
                }
            }
        }
    }

    if (board_confidence < 15) {
        ui_clear();
        ui_bar_center(2, "THE BOARD HAS SACKED YOU", ATTR_RED);
        ui_center(6, "YOUR TIME AT THE CLUB IS OVER.");
        ui_center(10, "PRESS SPACE");
        while (ui_key() != ' ')
            ;
        round_num = ROUNDS;
        return;
    }
    last_round = round_num;
    ++round_num;
    if (round_num >= ROUNDS)
        season_over();
}

/* ---------------------------------------------------------------------- */
/* management screen                                                       */
/* ---------------------------------------------------------------------- */

static void main_loop(unsigned char *cur)
{
    for (;;) {
        unsigned char k, i;
        char extra[24];

        frame();
        ui_center(2, "MANAGERS OFFICE");

        for (i = 0; i < 10; ++i) {
            extra[0] = 0;
            switch (i) {
            case 0:
                lb_reset();
                menu_row(1, "TEAM DISPLAY", "", 22);
                lb_num(squad_count, 2, ' ');
                lb_str(" PLAYERS");
                break;
            case 1:
                menu_row(2, "TEAM SELECTION",
                         selection_ok() ? "TEAM READY" : "NOT VALID", 22);
                break;
            case 2:
                lb_reset();
                menu_row(3, "TRAINING", "", 22);
                lb_str("PASS ");
                lb_num(pass_hi, 1, ' ');
                lb_ch('/');
                lb_num(pass_len, 1, ' ');
                break;
            case 3:
                menu_row(4, "BUY PLAYER", "", 22);
                break;
            case 4:
                menu_row(5, "SELL PLAYER", "", 22);
                break;
            case 5: {
                unsigned char h, a;
                if (round_num < ROUNDS && find_user_fixture(round_num, &h, &a)) {
                    strcpy(extra, h == user_team ? "V " : "AT ");
                    str_append(extra, team_name(h == user_team ? a : h));
                } else {
                    strcpy(extra, "SEASON OVER");
                }
                menu_row(6, "PLAY MATCH", extra, 22);
                break;
            }
            case 6:
                menu_row(7, "LEAGUE TABLE", "", 22);
                break;
            case 7:
                menu_row(8, "RESULTS", news, 22);
                break;
            case 8:
                lb_reset();
                menu_row(9, "FINANCE", "", 22);
                lb_num(cash, 4, ' ');
                lb_str("K");
                break;
            default:
                menu_row(10, "SAVE / LOAD", "", 22);
                break;
            }
            ui_item_lb((unsigned char)(4 + i), (unsigned char)(i == *cur));
        }

        lb_reset();
        lb_str("NEXT: ");
        {
            unsigned char h, a;
            if (round_num < ROUNDS && find_user_fixture(round_num, &h, &a)) {
                lb_str(team_name(h));
                lb_str(" V ");
                lb_str(team_name(a));
            } else {
                lb_str("SEASON COMPLETE");
            }
        }
        lb_draw(0, 16);

        lb_reset();
        lb_str("POS ");
        lb_num(user_position(), 2, ' ');
        lb_str(" OF 20   BOARD ");
        lb_num(board_confidence, 3, ' ');
        lb_str("%");
        lb_draw(0, 18);

        ui_message(news);
        ui_help("ARROWS OR NUMBER  ENTER  ESC");
        ui_footer("R RECORD   0 SAVE");

        k = ui_key();
        {
            unsigned char up;
            is_up_or(k, &up);
            if (up && *cur)
                --*cur;
            else if (k == 'S' && *cur < 9)
                ++*cur;
            else if (k == 'R') {
                record_screen();
            } else if (k == K_ENTER || (k >= '0' && k <= '9')) {
                if (k >= '0' && k <= '9')
                    *cur = (unsigned char)(k == '0' ? 9 : k - '1');
                switch (*cur) {
                case 0: squad_screen(); break;
                case 1: team_selection(); break;
                case 2: training_screen(); break;
                case 3: buy_screen(); break;
                case 4: sell_screen(); break;
                case 5: match_day(); break;
                case 6: table_screen(); break;
                case 7: results_screen(); break;
                case 8: finance_screen(); break;
                default: save_screen(); break;
                }
            } else if (k == K_ESC) {
                return;
            }
        }
    }
}

/* ---------------------------------------------------------------------- */
/* main                                                                    */
/* ---------------------------------------------------------------------- */

void main(void)
{
    unsigned int seed = 0x1234;
    unsigned char act, cur = 0;

    kbd_init();
    snd_init();
    scr_init();
    scr_charset();              /* our font, so text survives the bitmap */
    ui_clear();
    league_setup();

    for (;;) {
        act = title_screen(&seed);
        if (act == 3)
            soft_reset();
        if (act == 2) {
            instructions_screen();
            continue;
        }
        if (act == 1) {
            strcpy(news, "INSERT THE SAVE TAPE");
            kbd_suspend = 1;
            if (tape_load_game()) {
                strcpy(news, "GAME LOADED");
                cur = 0;
                main_loop(&cur);
            } else {
                strcpy(news, "NO SAVE FOUND - PRESS A KEY");
                ui_message(news);
                ui_key();
            }
            kbd_suspend = 0;
            continue;
        }
        {
            unsigned char t = club_select();
            if (t == 0xFF)
                continue;
            rng_seed((unsigned int)(seed + (unsigned int)t * 777));
            new_game(t);
            kit_select();
            sponsor_offer();
            cur = 0;
            main_loop(&cur);
        }
    }
}
