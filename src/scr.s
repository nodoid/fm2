;
; scr.s - Oric Atmos text screen driver for Football Manager 2.
;
; The text screen is 40x28 characters at $BB80.  A byte with bits 6 and 5
; clear is a *serial* attribute ($00-$07 = ink, $10-$17 = paper) and takes
; a character cell; bit 7 of a character byte selects inverse video.
; All routines here work on the real screen, no shadow buffer, because
; the Oric's 1 MHz 6502 has no spare cycles for double buffering.
;
; API (cc65 cdecl):
;   void scr_init(void);
;   void scr_clear(void);
;   void scr_gotoxy(unsigned char x, unsigned char y);
;   void scr_putc(unsigned char c);
;   void scr_puts(const char *s);
;   void scr_puts_inv(const char *s);
;   void scr_fill(unsigned char y, unsigned char ch);
;   void scr_attr(unsigned char y, unsigned char attr);
;   unsigned char scr_cx, scr_cy;     (zero page)
;
        .export         _scr_init, _scr_clear
        .export         _scr_gotoxy, _scr_putc
        .export         _scr_puts, _scr_puts_inv
        .export         _scr_fill, _scr_attr
        .export         _scr_cx, _scr_cy
        .import         popa
        .importzp       ptr1, ptr2

SCREEN  = $BB80
STATUS  = $026A

; ptr1 = screen row pointer, ptr2 = string pointer.  Both are cc65's
; zero-page scratch pointers; the game never holds them across a C call.

        .bss
_scr_cx:        .res    1
_scr_cy:        .res    1
scr_tmp:        .res    1

        .code

; ----------------------------------------------------------------------
; void scr_init (void)
;   Clear the screen, park the cursor at 0,0 and switch the ROM cursor off.
_scr_init:
        lda     STATUS
        and     #$FE
        sta     STATUS
        jsr     _scr_clear
        rts

; ----------------------------------------------------------------------
; void scr_clear (void)
;   Fill all 1120 character cells with spaces (4 pages + 96 bytes).
_scr_clear:
        lda     #<SCREEN
        sta     ptr1
        lda     #>SCREEN
        sta     ptr1+1
        ldy     #0
        ldx     #4
        lda     #' '
@page:  sta     (ptr1),y
        iny
        bne     @page
        inc     ptr1+1
        dex
        bne     @page
        ldy     #0
@tail:  sta     (ptr1),y
        iny
        cpy     #96
        bne     @tail
        lda     #0
        sta     _scr_cx
        sta     _scr_cy
        rts

; ----------------------------------------------------------------------
; void scr_gotoxy (unsigned char x, unsigned char y)
;   y arrives in A, x on the stack.
_scr_gotoxy:
        sta     _scr_cy
        jsr     popa
        sta     _scr_cx
        rts

; ----------------------------------------------------------------------
; void scr_putc (unsigned char c)
;   CR/LF are honoured; printable characters are written at the cursor.
_scr_putc:
        cmp     #13
        beq     @cr
        cmp     #10
        beq     @lf

        ldy     _scr_cy
        cpy     #28
        bcs     @out            ; off-screen: ignore
        pha
        lda     rowlo,y
        sta     ptr1
        lda     rowhi,y
        sta     ptr1+1
        ldy     _scr_cx
        pla
        sta     (ptr1),y
        inc     _scr_cx
        lda     _scr_cx
        cmp     #40
        bcc     @out
@cr:    lda     #0
        sta     _scr_cx
        rts
@lf:    lda     #0
        sta     _scr_cx
        inc     _scr_cy
        lda     _scr_cy
        cmp     #28
        bcc     @out
        lda     #27
        sta     _scr_cy
@out:   rts

; ----------------------------------------------------------------------
; void scr_puts (const char *s)
_scr_puts:
        sta     ptr2
        stx     ptr2+1
@loop:  ldy     #0
        lda     (ptr2),y
        beq     @done
        jsr     _scr_putc
        inc     ptr2
        bne     @loop
        inc     ptr2+1
        jmp     @loop
@done:  rts

; ----------------------------------------------------------------------
; void scr_puts_inv (const char *s)  - same, but inverse video
_scr_puts_inv:
        sta     ptr2
        stx     ptr2+1
@loop:  ldy     #0
        lda     (ptr2),y
        beq     @done
        ora     #$80
        jsr     _scr_putc
        inc     ptr2
        bne     @loop
        inc     ptr2+1
        jmp     @loop
@done:  rts

; ----------------------------------------------------------------------
; void scr_fill (unsigned char y, unsigned char ch)
;   Fill row y with ch, without changing the cursor.
_scr_fill:
        sta     scr_tmp
        jsr     popa
        tax
        lda     rowlo,x
        sta     ptr1
        lda     rowhi,x
        sta     ptr1+1
        lda     scr_tmp
        ldy     #0
@loop:  sta     (ptr1),y
        iny
        cpy     #40
        bne     @loop
        rts

; ----------------------------------------------------------------------
; void scr_attr (unsigned char y, unsigned char attr)
;   Put a serial attribute in column 0 of row y and leave the cursor
;   just after it (column 1).
_scr_attr:
        sta     scr_tmp
        jsr     popa
        tax
        lda     rowlo,x
        sta     ptr1
        lda     rowhi,x
        sta     ptr1+1
        lda     scr_tmp
        ldy     #0
        sta     (ptr1),y
        lda     #1
        sta     _scr_cx
        stx     _scr_cy
        rts

; ----------------------------------------------------------------------
; Row address tables: SCREEN + row * 40
        .rodata
rowlo:  .repeat 28, I
        .byte   <(SCREEN + I * 40)
        .endrep
rowhi:  .repeat 28, I
        .byte   >(SCREEN + I * 40)
        .endrep
