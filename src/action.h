#ifndef ACTION_H
#define ACTION_H

void action_begin(unsigned char home, unsigned char away, unsigned char flip);
void action_end(void);
void action_frame(unsigned char ex, unsigned char ey, unsigned char minute,
                  unsigned char hs, unsigned char as, unsigned char cup);

#endif
