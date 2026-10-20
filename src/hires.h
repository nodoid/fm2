/*
 * hires.h - Oric HIRES screen for Football Manager 2.
 *
 * The bitmap and the text screen share 8K, so the game switches between
 * them: management pages stay in text, the pitch pages are bitmaps.
 */
#ifndef HIRES_H
#define HIRES_H

#define HCOLS 40
#define HROWS 25

void hires_on(void);
void hires_off(void);
/* Rebuild the text-mode charset that the bitmap overwrites. */
void scr_charset(void);
void h_clear(void);
void h_plot(unsigned char x, unsigned char y);
void h_unplot(unsigned char x, unsigned char y);
void h_hline(unsigned char x0, unsigned char x1, unsigned char y);
void h_vline(unsigned char x, unsigned char y0, unsigned char y1);
void h_bline(unsigned char x0, unsigned char x1, unsigned char y);
void h_bvline(unsigned char x, unsigned char y0, unsigned char y1);
extern unsigned char h_dark;
extern unsigned char h_inv;   /* 1 flips the polarity: paper on, ink off */
void h_fill(unsigned char x0, unsigned char y0, unsigned char x1,
            unsigned char y1);
void h_text(unsigned char col, unsigned char row, const char *s);
void h_texti(unsigned char col, unsigned char row, const char *s);
void h_pitch(unsigned char view);
void h_band(void);
void h_marks(unsigned char view);
void h_box0(unsigned char x0, unsigned char y0, unsigned char x1,
            unsigned char y1);

/* sprite blitter: fill in these, then call h_spr */
extern const unsigned char *spr_src;
extern unsigned char spr_x, spr_y, spr_rows, spr_ink;
void h_spr(void);

/* C helpers built on the drawing primitives */
void h_rect(unsigned char x0, unsigned char y0, unsigned char x1,
            unsigned char y1);
void h_thick(unsigned char x0, unsigned char y0, unsigned char x1,
             unsigned char y1);
void h_wipe(unsigned char x0, unsigned char y0, unsigned char x1,
            unsigned char y1);
void h_spot(unsigned char x, unsigned char y, unsigned char kind);
void h_circle(unsigned char cx, unsigned char cy, unsigned char r);
void h_num(unsigned char col, unsigned char row, unsigned int v,
           unsigned char width);

#endif
