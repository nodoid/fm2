/*
 * match.h - FM2-style action match engine for Football Manager 2.
 *
 * The caller starts a match and then pulls frames one at a time; each
 * frame carries the ball position, the running score and a short
 * commentary line, which is all the action screen needs to animate.
 */
#ifndef MATCH_H
#define MATCH_H

#include "fm2.h"

#define M_KICKOFF 0
#define M_PASS    1
#define M_TACKLE  2
#define M_SHOT    3
#define M_SAVE    4
#define M_GOAL    5
#define M_MISS    6
#define M_HALF    7
#define M_FULL    8

#define FRAME_LEN 33

typedef struct {
    unsigned char kind;
    unsigned char side;      /* 0 home, 1 away, 2 neutral            */
    unsigned char x, y;      /* ball position, x 0..39, y 0..7       */
    unsigned char minute;
    unsigned char hs, as;
    char text[FRAME_LEN + 1];
} MatchFrame;

/* Simulates one team's goals from attack/defence ratings. */
unsigned char sim_goals(unsigned char att, unsigned char def);
void quick_score(unsigned char home_str, unsigned char away_str,
                 unsigned char *hs, unsigned char *as);

/* The user's fixture: home and away are indices into league[]. */
void match_begin(unsigned char home, unsigned char away);
unsigned char match_next(MatchFrame *f);   /* 0 when the match is over  */
unsigned char match_score_home(void);
unsigned char match_score_away(void);
void match_finish(void);                   /* apps, goals, tiredness    */

#endif
