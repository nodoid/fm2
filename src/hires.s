;
; hires.s - Oric Atmos HIRES driver for Football Manager 2.
;
; The Oric has one 1-bit 240x200 bitmap at $A000 and a 40x28 text screen
; at $BB80; the two share the same 8K of memory, so the game switches
; between them.  A byte in HIRES holds six pixels, bit 5 leftmost, and
; bit 6 must be set or the ULA treats the byte as a serial attribute
; ($00-$3F are attributes).  Blank is therefore $40, six lit pixels $7F.
;
; The video mode is latched from the byte in the last screen cell, $BFDF:
; $1E selects 50 Hz HIRES and $1A 50 Hz TEXT.  The ULA reads it at the end
; of every frame, so writing it once switches the display next frame.
;
; The bitmap is linear: address = $A000 + y*40 + x/6.  A text cell is one
; byte wide and eight scanlines tall, so a character occupies seven bytes
; at $A000 + row*320 + col + n*40.
;
; API (cc65 cdecl):
;   void hires_on (void);              switch to HIRES and clear
;   void hires_off (void);             back to TEXT (caller redraws)
;   void h_clear (void);
;   void h_plot (unsigned char x, unsigned char y);
;   void h_unplot (unsigned char x, unsigned char y);
;   void h_hline (unsigned char x0, unsigned char x1, unsigned char y);
;   void h_vline (unsigned char x, unsigned char y0, unsigned char y1);
;   void h_text (unsigned char col, unsigned char row, const char *s);
;   void h_texti (unsigned char col, unsigned char row, const char *s);
;
; The pitch, the markers and the scoreboard all go through these
; primitives, which is several times faster than the same loops compiled
; from C.

        .export         _hires_on, _hires_off, _h_clear
        .export         _h_plot, _h_unplot
        .export         _h_hline, _h_vline
        .export         _h_dark, _h_inv, _h_fill
        .export         _h_text, _h_texti
        .import         _scr_charset
        .export         _h_pitch, _h_band, _h_marks, _h_box0, _h_spr
        .export         _spr_src, _spr_x, _spr_y, _spr_rows, _spr_ink
        .import         popa
        .import         _font6, _xmask, _mfrom, _mto
        .importzp       ptr1, ptr2, ptr3

BFDF    = $BFDF
SCR     = $A000

        .bss
h_x:            .res    1
h_y:            .res    1
h_x0:           .res    1
h_x1:           .res    1
h_y0:           .res    1
h_y1:           .res    1
h_tmp:          .res    2
h_col:          .res    1
h_dst:          .res    2
h_inv:          .res    1
h_rem:          .res    1
h_q0:           .res    1
h_q1:           .res    1
h_lm:           .res    1
h_rm:           .res    1
h_fillb:        .res    1
h_mode:         .res    1
p_view:         .res    1
p_b:            .res    1
p_lim:          .res    1
p_rem:          .res    1
m_view:         .res    1
m_x0:           .res    1
m_x1:           .res    1
m_lm:           .res    1
m_rm:           .res    1
m_q0:           .res    1
m_q1:           .res    1
m_idx:          .res    1
; The sprite blitter's parameters: the caller fills these in and calls
; h_spr, which saves shuffling four arguments through the C stack.
_spr_src:       .res    2
_spr_x:         .res    1
_spr_y:         .res    1
_spr_rows:      .res    1
_spr_ink:       .res    1

s_q:            .res    1
s_rsl:          .res    1
s_rsr:          .res    1
s_rv:           .res    1
s_cnt:          .res    1
_h_dark:        .res    1
_h_inv:         .res    1

h_tinv:         .res    1

        .rodata
; The head of the grass run in the goal views, one byte per six rows:
; b = edge(y)/6 + 1, and the right hand view is the same wedge mirrored,
; so its run starts at 40 - b.
goalb:          .byte   14, 13, 13, 13, 13, 13, 13, 12, 12, 12, 12, 12, 12
                .byte   11, 11, 11, 11, 11, 11, 10, 10, 10, 10, 10, 10, 9

; The crowd above the pitch dashes four pixels every nine, which repeats
; every eighteen pixels, so one line of it is these three bytes repeated.
band0:          .byte   $3C, $07, $20
band1:          .byte   $03, $30, $1E

; The pitch markings, one entry per line: kind 1 is across (x0, x1, y),
; kind 2 is down (x, y0, y1), and 0 ends the list.  The right hand goal
; view is the mirror image, so one table serves both and h_marks flips
; the x coordinates.
marks_goal:     .byte   1, 100, 239,  60           ; far touchline
                .byte   1, 100, 239, 192           ; near touchline
                .byte   2, 100,  60, 174           ; goal line
                .byte   1, 100, 160,  84           ; penalty area
                .byte   1, 100, 160, 164
                .byte   2, 160,  84, 164
                .byte   1, 100, 122, 100           ; six yard box
                .byte   1, 100, 122, 148
                .byte   2, 122, 100, 148
                .byte   1,  86, 100, 112           ; the net
                .byte   1,  86, 100, 118
                .byte   1,  86, 100, 124
                .byte   1,  86, 100, 130
                .byte   1,  86, 100, 136
                .byte   2,  90, 112, 136
                .byte   2,  95, 112, 136
                .byte   0

marks_mid:      .byte   1,   0, 239,  56           ; touchlines
                .byte   1,   0, 239, 192
                .byte   2, 120,  56, 192           ; halfway line
                .byte   0

; Half the centre circle: dy every four pixels from -50 to 50.  The
; parabola is flat enough to pass for a circle seen from the touchline.
circtab:        .byte   0, 3, 6, 8, 10, 12, 14, 15, 16, 17, 18, 18, 18
                .byte   18, 18, 18, 17, 16, 15, 14, 12, 10, 8, 6, 3, 0

        .code

; ----------------------------------------------------------------------
; void hires_on (void)
_hires_on:
        lda     #$1E            ; 50 Hz HIRES
        sta     BFDF
        jsr     _h_clear
        rts

; ----------------------------------------------------------------------
; void hires_off (void)
;   The bitmap covers the ROM character set at $B400, so the font has to
;   be rebuilt before any text is drawn again.
_hires_off:
        lda     #$1A            ; 50 Hz TEXT
        sta     BFDF
        jmp     _scr_charset

; ----------------------------------------------------------------------
; ----------------------------------------------------------------------
; void h_clear (void) - 8000 bytes of blank bitmap plus the text footer
_h_clear:
        lda     #<SCR
        sta     ptr1
        lda     #>SCR
        sta     ptr1+1
        ldx     #31
        lda     #$40
@page:  ldy     #0
@loop:  sta     (ptr1),y
        iny
        bne     @loop
        inc     ptr1+1
        dex
        bne     @page
        ldy     #0
@tail:  sta     (ptr1),y        ; last 64 bytes, up to $BF3F
        iny
        cpy     #64
        bne     @tail
        ; The three text rows under the bitmap are always displayed, even
        ; in HIRES, and they take their glyphs from the character set at
        ; $B400 - which is inside the bitmap.  A code below 32 picks one
        ; of the thirty-two blank glyphs scr_charset builds there, so the
        ; band stays empty instead of showing the picture as letters.
        lda     #$00
        ldy     #0
@foot:  sta     $BF68,y
        iny
        cpy     #$77
        bne     @foot
        rts

; ----------------------------------------------------------------------
; ptr1 = $A000 + h_y * 40
row_addr:
        lda     h_y
        sta     ptr1
        lda     #0
        sta     ptr1+1
        asl     ptr1
        rol     ptr1+1          ; *2
        asl     ptr1
        rol     ptr1+1          ; *4
        asl     ptr1
        rol     ptr1+1          ; *8
        lda     ptr1
        sta     h_tmp
        lda     ptr1+1
        sta     h_tmp+1
        asl     ptr1
        rol     ptr1+1          ; *16
        asl     ptr1
        rol     ptr1+1          ; *32
        clc
        lda     ptr1
        adc     h_tmp
        sta     ptr1
        lda     ptr1+1
        adc     h_tmp+1
        sta     ptr1+1
        lda     ptr1+1
        clc
        adc     #>SCR
        sta     ptr1+1
        rts

; ----------------------------------------------------------------------
; void h_pitch (unsigned char view)
;   The park, top to bottom: green paper with black ink, and behind the
;   goal the dark wedge with its crowd.  Every run starts and ends on a
;   byte edge, so a row is a short string of stores -- which is why a
;   camera change no longer takes a second.
;
;   view 0 = left goal, 1 = halfway line, 2 = right goal (mirrored).
;
;   Every row starts with the same pair of attributes: the paper at byte
;   0 and a white ink at byte 1.  The ULA carries the colour state to the
;   right and on into the next scanline, so without that pair a stray
;   shirt attribute left behind by a figure would tint the rest of its
;   row and every row below it.  With it the worst case is one row, and
;   the figures can colour themselves at any x they like.
_h_pitch:
        sta     p_view
        lda     #48
        sta     h_y
        jsr     row_addr
        lda     p_view
        cmp     #1
        bne     @goal
@centre:
        ldy     #0
        lda     #$12            ; paper green
        sta     (ptr1),y
        lda     #$07            ; white ink for the markings
        iny
        sta     (ptr1),y
        lda     #$40            ; blank: this is the grass itself
@cfill: iny
        sta     (ptr1),y
        cpy     #40
        bne     @cfill
        jsr     next_row
        bcc     @centre
        rts

@goal:  ldx     #0              ; q = (y - 48) / 6, bumped every six rows
        lda     #6
        sta     p_rem
        lda     p_view
        bne     @right
@left:  lda     goalb,x         ; b: first grass byte of the row
        sta     p_b
        sta     p_lim
        dec     p_lim           ; the attribute byte sits at b - 1
        ldy     #0
        lda     #$10            ; paper black: the wedge starts at x = 0
        sta     (ptr1),y
        lda     #$07            ; white ink, so the markings stay white
        iny
        sta     (ptr1),y
        lda     #$40
        iny
@lz:    cpy     p_lim           ; the dark wedge: blank it as we pass
        bcs     @lattr
        sta     (ptr1),y
        iny
        jmp     @lz
@lattr: lda     #$12
        sta     (ptr1),y        ; green from just before the run
        lda     #$40
@lf:    iny
        cpy     #40
        bcs     @lspk
        sta     (ptr1),y
        jmp     @lf
@lspk:  lda     h_y             ; crowd on every fourth row
        and     #3
        cmp     #1
        bne     @lnext
        ldy     #2              ; bytes 0 and 1 are the row's attributes
@ld:    cpy     p_lim
        bcs     @lnext
        lda     (ptr1),y
        ora     #$78            ; three pixels at the head of the byte
        sta     (ptr1),y
        iny
        bne     @ld
@lnext: jsr     next_row
        bcs     @out
        dec     p_rem
        bne     @left
        inx
        lda     #6
        sta     p_rem
        jmp     @left

@right: lda     #40
        sec
        sbc     goalb,x         ; the same wedge, mirrored
        sta     p_b
        lda     #$12
        ldy     #0
        sta     (ptr1),y        ; green from the row head
        lda     #$07
        iny
        sta     (ptr1),y        ; white ink
        lda     #$40
        iny
@rf:    cpy     p_b
        bcs     @rw
        sta     (ptr1),y
        iny
        jmp     @rf
@rw:    lda     p_b
        tay
        dey
        lda     #$10            ; paper black: the wedge
        sta     (ptr1),y
        ldy     p_b             ; and blank the wedge itself
        lda     #$40
@rz:    cpy     #40
        bcs     @rspk
        sta     (ptr1),y
        iny
        jmp     @rz
@rspk:  lda     h_y
        and     #3
        cmp     #1
        bne     @rnext
        ldy     #39
@rd:    cpy     p_b
        bcc     @rnext
        lda     (ptr1),y
        ora     #$47            ; three pixels at the end of the byte
        sta     (ptr1),y
        dey
        jmp     @rd
@rnext: jsr     next_row
        bcs     @out
        dec     p_rem
        bne     @right
        inx
        lda     #6
        sta     p_rem
        jmp     @right
@out:   rts

; Advance ptr1 one bitmap row and bump h_y; carry set past the last row.
next_row:
        clc
        lda     ptr1
        adc     #40
        sta     ptr1
        lda     ptr1+1
        adc     #0
        sta     ptr1+1
        inc     h_y
        lda     h_y
        cmp     #200
        rts

; ----------------------------------------------------------------------
; void h_box0 (unsigned char x0, unsigned char y0, unsigned char x1,
;              unsigned char y1) - rub a rectangle back to blank.
;   The match screen erases every figure this way: the masks are worked
;   out once and the row pointer walks the box, instead of one line call
;   per row.
_h_box0:
        sta     h_y1
        jsr     popa
        sta     h_x1
        jsr     popa
        sta     h_y0
        jsr     popa
        sta     h_x0
        lda     h_x0
        cmp     h_x1
        bcc     @xok
        beq     @xok
        lda     h_x0
        pha
        lda     h_x1
        sta     h_x0
        pla
        sta     h_x1
@xok:   lda     h_x1
        cmp     #240
        bcc     @clipped
        lda     #239
        sta     h_x1
@clipped:
        lda     h_y0
        cmp     h_y1
        bcc     @yok
        beq     @yok
        lda     h_y0
        pha
        lda     h_y1
        sta     h_y0
        pla
        sta     h_y1
@yok:   lda     h_y0
        sta     h_y

        lda     h_x0
        jsr     xparts
        lda     _mfrom,x
        sta     m_lm
        sty     m_q0
        lda     h_x1
        jsr     xparts
        lda     _mto,x
        sta     m_rm
        sty     m_q1

@row:   jsr     row_addr
        ldy     m_q0
        cpy     m_q1
        bne     @multi
        lda     m_lm
        and     m_rm
        jsr     boxclr
        jmp     @next
@multi: lda     m_lm
        jsr     boxclr
        iny
@mid:   cpy     m_q1
        bcs     @last
        lda     #$3F            ; every pixel of a middle byte is cleared
        jsr     boxclr
        iny
        bne     @mid
@last:  ldy     m_q1
        lda     m_rm
        jsr     boxclr
@next:  lda     h_y
        cmp     h_y1
        beq     @done
        inc     h_y
        jmp     @row
@done:  rts

; A = the pixels to keep, Y = byte of the row.  A serial attribute (bits 5
; and 6 clear) carries the ink and paper for the rest of the scanline.  A
; paper attribute is left alone - the wedge behind a goal needs it - but an
; ink one is rubbed back to blank grass: that is what takes the shirt
; colour away when a figure walks off, and it leaves the byte drawable
; again, so the next figure to stand there is not clipped by it.
boxclr: sta     h_tmp
        lda     (ptr1),y
        and     #$60
        beq     @attr
        lda     h_tmp
        eor     #$3F
        and     (ptr1),y
        ora     #$40
        sta     (ptr1),y
        rts
@attr:  lda     (ptr1),y
        and     #$10            ; paper: keep the wedge black
        bne     @keep
        lda     #$40
        sta     (ptr1),y
@keep:  rts

; ----------------------------------------------------------------------
; void h_marks (unsigned char view) - the pitch markings, drawn straight
;   into the bitmap.  One call replaces the three dozen line calls the C
;   version made, and the centre circle's dashes share a single mask.
_h_marks:
        sta     m_view
        cmp     #1
        bne     @goal
        lda     #<marks_mid
        sta     ptr2
        lda     #>marks_mid
        sta     ptr2+1
        jmp     @next
@goal:  lda     #<marks_goal
        sta     ptr2
        lda     #>marks_goal
        sta     ptr2+1
@next:  ldy     #0
        lda     (ptr2),y
        bne     @kind
        jmp     @tail
@kind:  cmp     #1
        bne     @downline
        jmp     @across
@downline:
        ; a line down the page: x, then the two ends
        ldy     #1
        lda     (ptr2),y
        jsr     mirrorx
        sta     h_x
        jsr     xbyte           ; A = pixel mask, Y = byte of the row
        sta     m_lm
        sty     m_idx
        ldy     #2
        lda     (ptr2),y
        sta     h_y0
        ldy     #3
        lda     (ptr2),y
        sta     h_y1
        lda     h_y0
        sta     h_y
        jsr     row_addr
@down:  ldy     m_idx
        lda     m_lm
        jsr     setpix
        lda     h_y
        cmp     h_y1
        bne     @downmore
        jmp     @step
@downmore:
        inc     h_y
        clc
        lda     ptr1
        adc     #40
        sta     ptr1
        lda     ptr1+1
        adc     #0
        sta     ptr1+1
        jmp     @down

@across:
        ldy     #1
        lda     (ptr2),y
        sta     m_x0
        ldy     #2
        lda     (ptr2),y
        sta     m_x1
        ldy     #3
        lda     (ptr2),y
        sta     h_y
        lda     m_view
        cmp     #2
        bne     @ready
        lda     #239            ; the mirror image runs the other way
        sec
        sbc     m_x1
        sta     h_tmp
        lda     #239
        sec
        sbc     m_x0
        sta     m_x1
        lda     h_tmp
        sta     m_x0
@ready: jsr     row_addr
        lda     m_x0
        jsr     xparts
        lda     _mfrom,x
        sta     m_lm
        sty     m_q0
        lda     m_x1
        jsr     xparts
        lda     _mto,x
        sta     m_rm
        sty     m_q1
        ldy     m_q0
        cpy     m_q1
        bne     @multi
        lda     m_lm
        and     m_rm
        jsr     setpix
        jmp     @step
@multi: lda     m_lm
        jsr     setpix
        iny
@mid:   cpy     m_q1
        bcs     @last
        lda     #$3F
        jsr     setpix
        iny
        bne     @mid
@last:  ldy     m_q1
        lda     m_rm
        jsr     setpix

@step:  clc                     ; next table entry
        lda     ptr2
        adc     #4
        sta     ptr2
        bcs     @carry
        jmp     @next
@carry: inc     ptr2+1
        jmp     @next

@tail:  lda     m_view          ; the halfway view also has the circle
        cmp     #1
        bne     @out
        ldx     #0
@dash:  stx     m_idx           ; xparts returns X, so keep i safe
        txa                     ; x0 = 70 + 4i, x1 = x0 + 3
        asl     a
        asl     a
        clc
        adc     #70
        sta     m_x0
        jsr     xparts
        lda     _mfrom,x
        sta     m_lm
        sty     m_q0
        lda     m_x0
        clc
        adc     #3
        jsr     xparts
        lda     _mto,x
        sta     m_rm
        sty     m_q1
        ldx     m_idx
        lda     circtab,x
        sta     h_tmp           ; dy
        lda     #126
        sec
        sbc     h_tmp
        sta     h_y
        jsr     dashrow
        ldx     m_idx
        lda     circtab,x
        clc
        adc     #126
        sta     h_y
        jsr     dashrow
        ldx     m_idx
        inx
        cpx     #26
        bcc     @dash
@out:   rts

; h_y = row: OR the two mask bytes the circle dash was cut with.
dashrow: jsr     row_addr
        ldy     m_q0
        cpy     m_q1
        bne     @two
        lda     m_lm
        and     m_rm
        jsr     setpix
        rts
@two:   lda     m_lm
        jsr     setpix
        ldy     m_q1
        lda     m_rm
        jsr     setpix
        rts

; A = the pixels to set, Y = byte of the row.  A serial attribute carries
; the colours for the rest of the scanline, so it is never drawn over: the
; pitch would lose the paper colour that makes it green.
setpix: sta     h_tmp
        lda     (ptr1),y
        and     #$60
        beq     @keep
        lda     h_tmp
        ora     (ptr1),y
        sta     (ptr1),y
@keep:  rts

; A = x, mirrored for the right hand view.
mirrorx:
        sta     h_tmp
        lda     m_view
        cmp     #2
        bne     @keep
        lda     #239
        sec
        sbc     h_tmp
        rts
@keep:  lda     h_tmp
        rts

; ----------------------------------------------------------------------
; void h_spr (void) - blit one figure straight into the bitmap.
;   The caller leaves the rows in spr_src, the anchor in spr_x/spr_y, the
;   row count in spr_rows and the shirt attribute in spr_ink (0 for an
;   opponent).  A sprite row spans two bytes; the shift is worked out once
;   for the whole figure, then each row is two shifts and two stores, with
;   the ink attribute written either side of it on the way past.
_h_spr:
        lda     _spr_y
        sta     h_y
        jsr     row_addr
        lda     _spr_x
        jsr     xparts
        sty     s_q
        stx     s_rsl
        inc     s_rsl           ; the left byte takes r + 1 shifts
        lda     #6
        sec
        sbc     s_rsl           ; the right byte takes 6 - (r + 1)
        sta     s_rsr
        clc
        lda     ptr1
        adc     s_q
        sta     ptr1
        lda     ptr1+1
        adc     #0
        sta     ptr1+1
        lda     _spr_src
        sta     ptr2
        lda     _spr_src+1
        sta     ptr2+1
        lda     _spr_rows
        sta     s_cnt

@row:   ldy     #0
        lda     (ptr2),y
        sta     s_rv
        ldx     s_rsl
        lda     s_rv
        ; ptr1 already points at byte x/6 of the row, so the figure's two
        ; bytes are 0 and 1, and the ink attributes sit either side.
@lshr:  lsr     a
        dex
        bne     @lshr
        ldy     #0
        jsr     sprput

        lda     s_rv
        ldx     s_rsr
        beq     @rshr_done
@rshr:  asl     a
        dex
        bne     @rshr
@rshr_done:
        and     #$3F
        ldy     #1
        jsr     sprput

        ; $00-$07 sets the ink and $10-$17 the paper, and either one
        ; colours the rest of the scanline.  So the shirt is an ink
        ; attribute in the byte to the left of the figure, and a white one
        ; in the byte to its right restores the markings and the crowd.
        ;
        ; (ptr1) indexes the row, so the byte before the figure is one
        ; less on the pointer, not y = $FF: indirect indexing does not
        ; wrap, so that would have put the colour six rows below.  A
        ; colour cell is never overwritten - the wedge behind a goal
        ; needs its paper - so a figure drawn over one stays white.
        lda     s_q
        cmp     #2
        bcc     @notint
        lda     _spr_ink
        beq     @notint
        lda     ptr1            ; step on to the byte before the figure
        bne     @stepback
        dec     ptr1+1
@stepback:
        dec     ptr1
        ldy     #0
        lda     (ptr1),y
        and     #$60
        beq     @restore        ; a colour cell: never write over it
        lda     _spr_ink
        sta     (ptr1),y
@restore:
        inc     ptr1
        bne     @white
        inc     ptr1+1
@white: ldy     #2
        lda     (ptr1),y
        and     #$60
        beq     @notint
        lda     #$07            ; opponents and lines stay white
        sta     (ptr1),y
@notint:
        clc
        lda     ptr1
        adc     #40
        sta     ptr1
        lda     ptr1+1
        adc     #0
        sta     ptr1+1
        inc     ptr2
        bne     @nocarry
        inc     ptr2+1
@nocarry:
        dec     s_cnt
        bne     @row
        rts

; A = the pixels to set, Y = byte of the row.  A serial attribute carries
; the ink and paper for the rest of the scanline, so a figure is never
; drawn over one: that would recolour the pitch past it.
sprput: sta     h_tmp
        lda     (ptr1),y
        and     #$60
        beq     @keep
        lda     h_tmp
        ora     (ptr1),y
        ora     #$40
        sta     (ptr1),y
@keep:  rts

; One line of the header crowd: the three byte pattern repeated across
; the row.  Y walks the row, X the pattern.
.macro  bandrow addr
        ldy     #0
        ldx     #0
:       lda     addr,x
        ora     #$40            ; pixels on, and still a character byte
        sta     (ptr1),y
        iny
        inx
        cpx     #3
        bcc     :-
        ldx     #0
        cpy     #40
        bcc     :-
.endmacro

; ----------------------------------------------------------------------
; void h_band (void) - the crowd speckle across the head of the page
_h_band:
        lda     #0
        sta     h_y
        jsr     row_addr
@row:   lda     h_y
        and     #2
        bne     @pat1
        bandrow band0
        jmp     @next
@pat1:  bandrow band1
@next:  clc
        lda     ptr1
        adc     #120            ; three rows down
        sta     ptr1
        lda     ptr1+1
        adc     #0
        sta     ptr1+1
        lda     h_y
        cmp     #45
        beq     @done
        clc
        adc     #3
        sta     h_y
        jmp     @row
@done:  rts

; ----------------------------------------------------------------------
; A = pixel x -> Y = x/6, X = x%6.
;
; The byte index is a table lookup rather than the multiply-and-shift the
; first version used: x/6 is the same for 2i and 2i+1, so a 120 byte table
; indexed by x>>1 covers every x, and the pixel offset follows from it by
; one shift and two adds.  Around twenty-five cycles instead of four
; hundred, which matters because every line and every box pays it.
qtab:   .repeat 120, i
        .byte   i / 3
        .endrepeat

xparts:
        sta     h_rem           ; x
        lsr     a
        tay                     ; x / 2
        lda     qtab,y          ; q = x / 6
        sta     h_tmp
        asl     a               ; 2q
        sta     h_dst
        asl     a               ; 4q
        clc
        adc     h_dst           ; 6q
        sta     h_dst
        lda     h_rem
        sec
        sbc     h_dst           ; r = x - 6q
        tax
        ldy     h_tmp
        rts

; Returns the byte offset of h_x in Y, and its pixel mask in A.
xbyte:
        lda     h_x
        jsr     xparts
        lda     _xmask,x
        rts

; ----------------------------------------------------------------------
; void h_plot (unsigned char x, unsigned char y)
_h_plot:
        sta     h_y
        jsr     popa
        sta     h_x
        jsr     row_addr
        jsr     xbyte
        ora     (ptr1),y
        sta     (ptr1),y
        rts

; ----------------------------------------------------------------------
; void h_unplot (unsigned char x, unsigned char y)
_h_unplot:
        sta     h_y
        jsr     popa
        sta     h_x
        jsr     row_addr
        jsr     xbyte
        eor     #$3F
        and     (ptr1),y
        ora     #$40
        sta     (ptr1),y
        rts

; ----------------------------------------------------------------------
; void h_hline (unsigned char x0, unsigned char x1, unsigned char y)
;   Whole bytes in the middle are filled with one store each, so a pitch
;   line costs about forty writes instead of 240 plots.  The ink/paper
;   choice is made once for the call instead of once per byte: that is
;   most of a long line's cost.
_h_hline:
        sta     h_y
        jsr     popa
        sta     h_x1
        jsr     popa
        sta     h_x0
        lda     h_x0
        cmp     h_x1
        bcc     @sorted
        beq     @sorted
        lda     h_x0
        pha
        lda     h_x1
        sta     h_x0
        pla
        sta     h_x1
@sorted:
        lda     h_x1             ; the calls that run off the row edge
        cmp     #240             ; stop there: there is no byte 40
        bcc     @edge_ok
        lda     #239
        sta     h_x1
@edge_ok:
        jsr     row_addr

        lda     h_x0
        jsr     xparts
        lda     _mfrom,x
        sta     h_lm           ; leftmost byte: bits x0..5
        sty     h_q0

        lda     h_x1
        jsr     xparts
        lda     _mto,x
        sta     h_rm           ; rightmost byte: bits 0..x1
        sty     h_q1

        ; dark == inv means the pixels are being cleared, so a run byte is
        ; $40 and the edge masks are dropped; otherwise it is $7F and the
        ; masks are ORed in.
        ldx     #$80            ; edge mode: bit 7 set = ink
        lda     #$7F
        sta     h_fillb
        lda     _h_dark
        cmp     _h_inv
        beq     @mode           ; dark == inv: pixels on
        ldx     #0
        lda     #$40
        sta     h_fillb
@mode:  stx     h_mode

        ldy     h_q0
        cpy     h_q1
        bne     @multi
        lda     h_lm
        and     h_rm
        jsr     edge
        sta     (ptr1),y
        rts
@multi: lda     h_lm
        jsr     edge
        sta     (ptr1),y
        lda     h_fillb
        iny
@mid:   cpy     h_q1
        bcs     @last
        sta     (ptr1),y
        iny
        bne     @mid
@last:  ldy     h_q1
        lda     h_rm
        jsr     edge
        sta     (ptr1),y
        rts

; A = six bit mask, Y = byte of the row: returns the new byte in A.
edge:   bit     h_mode
        bmi     @ink
        eor     #$3F
        and     (ptr1),y
        ora     #$40
        rts
@ink:   ora     (ptr1),y
        ora     #$40
        rts

; ----------------------------------------------------------------------
; void h_vline (unsigned char x, unsigned char y0, unsigned char y1)
_h_vline:
        sta     h_y1
        jsr     popa
        sta     h_y0
        jsr     popa
        sta     h_x
        lda     h_y0
        cmp     h_y1
        bcc     @sorted
        beq     @sorted
        lda     h_y0
        pha
        lda     h_y1
        sta     h_y0
        pla
        sta     h_y1
@sorted:
        lda     h_y0
        sta     h_y
        jsr     row_addr
        jsr     xbyte
        sta     h_tmp
@loop:  lda     _h_dark
        cmp     _h_inv
        bne     @dark
        lda     h_tmp
        ora     (ptr1),y
        jmp     @put
@dark:  lda     h_tmp
        eor     #$3F
        and     (ptr1),y
        ora     #$40
@put:   sta     (ptr1),y
        lda     h_y
        cmp     h_y1
        beq     @done
        inc     h_y
        clc
        lda     ptr1
        adc     #40
        sta     ptr1
        lda     ptr1+1
        adc     #0
        sta     ptr1+1
        jmp     @loop
@done:  rts

; ----------------------------------------------------------------------
; void h_fill (unsigned char x0, unsigned char y0, unsigned char x1,
;              unsigned char y1) - make a rectangle bright paper.
;   Rows are contiguous, so each one is a short run of stores; this is the
;   workhorse the match screen uses to rub out players as they run.
_h_fill:
        sta     h_y1
        jsr     popa
        sta     h_x1
        jsr     popa
        sta     h_y0
        jsr     popa
        sta     h_x0
        lda     h_x0
        cmp     h_x1
        bcc     @xok
        beq     @xok
        lda     h_x0
        pha
        lda     h_x1
        sta     h_x0
        pla
        sta     h_x1
@xok:   lda     h_y0
        cmp     h_y1
        bcc     @yok
        beq     @yok
        lda     h_y0
        pha
        lda     h_y1
        sta     h_y0
        pla
        sta     h_y1
@yok:   lda     h_y0
        sta     h_y

        ; Masks are worked out once: the run length shrinks as the row
        ; loop walks, so they must not be recomputed from the running
        ; byte index.
        lda     h_x0
        jsr     xparts
        lda     _mfrom,x
        sta     h_lm            ; leftmost byte: bits x0..5
        sty     h_q0

        lda     h_x1
        jsr     xparts
        lda     _mto,x
        sta     h_rm            ; rightmost byte: bits 0..x1
        sty     h_q1

@row:   jsr     row_addr
        ldy     h_q0
        lda     h_q0
        cmp     h_q1
        bne     @multi
        lda     h_lm
        and     h_rm
        ora     (ptr1),y
        ora     #$40
        sta     (ptr1),y
        jmp     @next
@multi: lda     h_lm
        ora     (ptr1),y
        ora     #$40
        sta     (ptr1),y
        clc
        lda     h_q0
        adc     #1
        sta     h_rem
@mid:   lda     h_rem
        cmp     h_q1
        bcs     @right
        ldy     h_rem
        lda     #$7F
        sta     (ptr1),y
        inc     h_rem
        jmp     @mid
@right: ldy     h_q1
        lda     h_rm
        ora     (ptr1),y
        ora     #$40
        sta     (ptr1),y
@next:  lda     h_y
        cmp     h_y1
        beq     @done
        inc     h_y
        jmp     @row
@done:  rts

; ----------------------------------------------------------------------
; void h_text (unsigned char col, unsigned char row, const char *s)
;   cc65 hands the last argument (the string pointer) over in A/X, so it
;   has to be preserved while the inverted flag is set up.
_h_text:
        pha
        lda     #0
        sta     h_tinv
        pla
        jmp     text_draw
; void h_texti (unsigned char col, unsigned char row, const char *s)
_h_texti:
        pha
        lda     #1
        sta     h_tinv
        pla
text_draw:
        sta     ptr2
        stx     ptr2+1
        jsr     popa            ; row
        sta     h_y
        jsr     popa            ; col
        sta     h_col

        ; ptr1 = $A000 + row*320 + col
        lda     h_y
        and     #3
        ldx     #6
@sh:    asl     a
        dex
        bne     @sh
        sta     ptr1
        lda     h_y
        lsr     a
        lsr     a
        clc
        adc     h_y
        clc
        adc     #>SCR
        sta     ptr1+1
        lda     ptr1
        clc
        adc     h_col
        sta     ptr1
        lda     ptr1+1
        adc     #0
        sta     ptr1+1

@next:  ldy     #0
        lda     (ptr2),y
        bne     @cont
        rts
@cont:  cmp     #'a'
        bcc     @fold
        cmp     #'z'+1
        bcs     @fold
        sec
        sbc     #32
@fold:  sec
        sbc     #32
        bcs     @have
        lda     #0
@have:  cmp     #64
        bcc     @idx
        lda     #0
@idx:   ; a glyph is seven bytes at _font6 + index*7, already in the
        ; six pixel cell layout, so a row is one load and one store
        sta     h_tmp
        lda     ptr1
        sta     h_dst
        lda     ptr1+1
        sta     h_dst+1
        lda     #0
        sta     ptr3+1
        lda     h_tmp
        asl     a               ; 2i
        rol     ptr3+1
        sta     ptr3
        asl     a               ; 4i
        rol     ptr3+1
        clc
        adc     ptr3            ; 6i
        sta     ptr3
        bcc     @six
        inc     ptr3+1
@six:   clc
        adc     h_tmp           ; 7i
        sta     ptr3
        bcc     @seven
        inc     ptr3+1
@seven: clc
        lda     ptr3
        adc     #<_font6
        sta     ptr3
        lda     ptr3+1
        adc     #>_font6
        sta     ptr3+1
        lda     #7
        sta     h_y              ; rows left
        ldy     #0
@row:   lda     (ptr3),y
        inc     ptr3
        bne     @noc
        inc     ptr3+1
@noc:   ldx     h_tinv
        beq     @plain
        eor     #$7F
        and     #$7F
@plain: ora     #$40
        sta     (ptr1),y
        clc
        lda     ptr1
        adc     #40
        sta     ptr1
        lda     ptr1+1
        adc     #0
        sta     ptr1+1
        dec     h_y
        bne     @row

        lda     h_dst
        clc
        adc     #1
        sta     ptr1
        lda     h_dst+1
        adc     #0
        sta     ptr1+1

        lda     h_col
        cmp     #39
        bcc     @more
        rts
@more:  inc     h_col
        inc     ptr2
        bne     @go
        inc     ptr2+1
@go:    jmp     @next
