/*
 * ui.h - screen helpers for Football Manager 2.
 */
#ifndef UI_H
#define UI_H

/* attribute bytes (ink $00-$07, paper $10-$17) */
#define ATTR_BAR    0x14
#define ATTR_YEL    0x13
#define ATTR_RED    0x01
#define ATTR_GREEN  0x02

/* assembly screen driver (scr.s) */
void scr_init(void);
void scr_clear(void);
void scr_gotoxy(unsigned char x, unsigned char y);
void scr_putc(unsigned char c);
void scr_puts(const char *s);
void scr_puts_inv(const char *s);
void scr_fill(unsigned char y, unsigned char ch);
void scr_attr(unsigned char y, unsigned char attr);

/* assembly keyboard scanner (kbd.s) */
extern unsigned char kbd_ticks[2];
extern unsigned char kbd_suspend;
void kbd_init(void);
unsigned char kbd_get(void);
void soft_reset(void);
unsigned char kbd_wait(void);

/* assembly sound effects (snd.s) */
void snd_init(void);
void snd_off(void);
void snd_click(void);
void snd_goal(void);
void snd_whistle(void);
void snd_bad(void);

/* cassette block transfer (tape.s) */
extern unsigned char *tape_ptr;
extern unsigned int tape_len;
extern char tape_name[16];
unsigned char tape_save_block(void);
unsigned char tape_load_block(void);

/* C helpers */
void ui_clear(void);
void ui_gotoxy(unsigned char x, unsigned char y);
void ui_putc(char c);
void ui_puts(const char *s);
void ui_puts_inv(const char *s);
void ui_attr(unsigned char y, unsigned char a);
void ui_hline(unsigned char y, char c);
void ui_center(unsigned char y, const char *s);
void ui_header(void);
void ui_footer(const char *hints);
void ui_message(const char *msg);
void ui_help(const char *msg);
void ui_player_row(unsigned char y, unsigned char idx, unsigned char star,
                   unsigned char number, unsigned char inv);
void ui_bar_center(unsigned char y, const char *s, unsigned char attr);
void ui_item_lb(unsigned char y, unsigned char selected);
unsigned char is_up(unsigned char k);
unsigned char is_down(unsigned char k);

/* match action pitch */
void ui_pitch_frame(void);
void ui_pitch_draw(unsigned char bx, unsigned char by);
void ui_pitch_score(const char *home, const char *away, unsigned char hs,
                    unsigned char as, unsigned char minute, unsigned char cup);

/* asm helpers */
unsigned char tape_save(void);
unsigned char tape_load_game(void);
void wait_esc(void);

void lb_reset(void);
void lb_str(const char *s);
void lb_ch(char c);
void lb_num(unsigned int v, unsigned char width, char pad);
void lb_pad(unsigned char width);
void lb_str_clip(const char *s, unsigned char max);
void lb_draw(unsigned char x, unsigned char y);
void lb_draw_inv(unsigned char x, unsigned char y);

unsigned char ui_key(void);
unsigned char ui_key_ns(void);
unsigned char ui_poll(void);
void ui_pause(unsigned int n);

#endif
