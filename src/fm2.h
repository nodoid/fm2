/*
 * fm2.h - shared definitions for Football Manager 2 (Oric Atmos port).
 *
 * A from-scratch reimplementation of the 1988 Addictive game for a 1 MHz
 * 6502 with 37K of RAM: four divisions of twenty clubs, a squad with
 * skill/fitness/position/value, a twelve-zone team selection with
 * man-to-man marking, passing-height and passing-length training, and
 * animated text-mode match action.
 *
 * Everything here is portable C: it is compiled both for the Oric (cc65,
 * 16-bit int) and for the sim65 unit-test target.
 */
#ifndef FM2_H
#define FM2_H

#define DIVS           4
#define TEAMS_PER_DIV  20
#define NUM_TEAMS      (DIVS * TEAMS_PER_DIV)   /* 80 clubs            */
#define ROUNDS         (TEAMS_PER_DIV - 1)      /* 19 league rounds    */
#define MPR            (TEAMS_PER_DIV / 2)      /* 10 matches per round*/
#define FIRST_ROUND    0
#define SQUAD_SIZE     16
#define ZONES          12                       /* 4 per outfield view */
#define NSUBS          2
#define MARKET_SIZE    3
#define CUP_SIZE       32
#define CUP_ROUNDS     5
#define CUP_TIES       (CUP_SIZE / 2)

/* player positions (G/D/M/A, as FM2 shows them) */
#define POS_GK 0
#define POS_DF 1
#define POS_MF 2
#define POS_FW 3

/* the three team-selection views */
#define VIEW_DEF 0
#define VIEW_MID 1
#define VIEW_ATT 2

/* special keys returned by kbd.s (outside ASCII) */
#define K_UP    0xE3
#define K_DOWN  0xE4
#define K_LEFT  0xE5
#define K_RIGHT 0xE6
#define K_ESC   0x1B
#define K_ENTER 0x0D

typedef struct {
    char name[10];          /* "J.SMITH" + NUL                          */
    unsigned char pos;      /* POS_*                                    */
    unsigned char skill;    /* 3..9, as in FM2                          */
    unsigned char fit;      /* 0..100                                   */
    unsigned char goals;
    unsigned char apps;
    unsigned int value;     /* value in thousands of pounds            */
} Player;

typedef struct {
    char name[13];
    unsigned char str;      /* AI strength, 38..90                      */
    unsigned char played, won, drawn, lost;
    unsigned char gf, ga;
    unsigned int points;
} Team;

typedef struct {
    char name[10];
    unsigned char pos;
    unsigned char skill;
    unsigned int value;
} Target;

typedef struct {
    unsigned char teams[CUP_SIZE];
    unsigned char n;               /* clubs still in the cup             */
    unsigned char round;           /* 0..CUP_ROUNDS                      */
    unsigned char hs[CUP_TIES], as[CUP_TIES];
} Cup;

/* ---- global game state -------------------------------------------------- */
extern Team league[NUM_TEAMS];
extern Player squad[SQUAD_SIZE];
extern unsigned char squad_count;
extern unsigned char keeper;              /* squad index or 0xFF           */
extern unsigned char zone[ZONES];         /* squad index or 0xFF           */
extern unsigned char subsel[NSUBS];       /* squad index or 0xFF           */
extern unsigned char sel[SQUAD_SIZE];     /* 1 = in the eleven             */

extern unsigned int cash;                 /* thousands of pounds           */
extern unsigned char user_team;
extern unsigned char pass_hi;             /* passing height 1..5           */
extern unsigned char pass_len;            /* passing length 1..5           */
extern unsigned char round_num;           /* 0..ROUNDS                     */
extern unsigned char season;
extern unsigned char last_round;          /* round just played, or 0xFF    */
extern unsigned char board_confidence;    /* 0..100                        */

/* results of the current round, for the division being viewed */
extern unsigned char res_h[MPR], res_a[MPR];
extern unsigned char res_hs[MPR], res_as[MPR];
extern unsigned char res_valid[MPR];

extern Target market[MARKET_SIZE];
extern char news[64];

extern unsigned int rng_state;

extern Cup fa_cup;
extern Cup league_cup;
extern unsigned char cup_won;             /* bit 0 FA, bit 1 League Cup    */

typedef struct {
    unsigned int magic;
    unsigned char version;
    unsigned char user_team;
    unsigned char round_num, season, last_round;
    unsigned char pass_hi, pass_len;
    unsigned char squad_count, keeper;
    unsigned char board_confidence;
    unsigned char cup_won;
    unsigned int cash, rng_state;
    Team league[NUM_TEAMS];
    Player squad[SQUAD_SIZE];
    unsigned char zone[ZONES];
    unsigned char subsel[NSUBS];
    Cup fa_cup, league_cup;
} SaveGame;

#define SAVE_MAGIC   0x464D          /* "FM" */
#define SAVE_VERSION 3

extern SaveGame saveblk;
void save_game_state(void);
unsigned char load_game_state(void);
unsigned char save_valid(void);

unsigned char sim_goals(unsigned char att, unsigned char def);

/* ---- random numbers ---------------------------------------------------- */
void rng_seed(unsigned int s);
unsigned char rnd8(void);
unsigned int rnd16(void);
unsigned char rnd_range(unsigned char n);

/* ---- setup ------------------------------------------------------------- */
void league_setup(void);
void new_game(unsigned char team);
void league_reset(void);
void new_season(void);

/* ---- fixtures (round-robin computed, not stored) ----------------------- */
void fixtures_for(unsigned char div, unsigned char round,
                  unsigned char *home, unsigned char *away);
unsigned char find_user_fixture(unsigned char round,
                                unsigned char *home, unsigned char *away);
void play_league_round(unsigned char round);
void apply_result(unsigned char home, unsigned char away,
                  unsigned char hs, unsigned char as);
void sort_table(unsigned char div, unsigned char *order);
unsigned char user_position(void);
void season_finish(void);
void promote_relegate(void);
unsigned char prize_money(void);
unsigned int week_end(unsigned char was_home);
void play_other_matches(unsigned char round, unsigned char skip_user);
void start_round(unsigned char round);

/* ---- cups -------------------------------------------------------------- */
void cup_setup(Cup *c, unsigned char seed_team);
void cup_draw(Cup *c);
unsigned char cup_user_tie(Cup *c, unsigned char *opponent, unsigned char *home);
unsigned char cup_play_round(Cup *c, unsigned char user_hs, unsigned char user_as,
                             unsigned char *out_hs, unsigned char *out_as);
unsigned char cup_week(unsigned char round);

/* ---- squad ------------------------------------------------------------- */
unsigned char squad_size(void);
Player *player(unsigned char i);
unsigned char player_eff(unsigned char i);
unsigned char num_selected(void);
unsigned char selection_ok(void);
void auto_select(void);
void auto_select_marks(void);
unsigned char zone_players(unsigned char view);
unsigned char view_strength(unsigned char view);
unsigned char team_attack(void);
unsigned char team_defence(void);
unsigned char total_wages(void);
void train_week(void);
void age_squad(void);

/* ---- transfers --------------------------------------------------------- */
void refresh_market(void);
unsigned char buy_player(unsigned char idx);
unsigned char sell_player(unsigned char idx);
unsigned char player_value(unsigned char i);

/* ---- helpers ----------------------------------------------------------- */
char *u2s(unsigned int v, char *buf);
void str_append(char *dst, const char *src);
void make_player_name(char *dst, unsigned char pos, unsigned char n);
char *news_line(const char *msg);

#endif
