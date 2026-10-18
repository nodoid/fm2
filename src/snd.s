;
; snd.s - AY-3-8912 sound effects for Football Manager 2.
;
; Channel A tone is used for clicks and the goal jingle; the noise
; generator supplies the referee's whistle.  kbd_init() must have set up
; the VIA ports before any of these routines are called.
;
        .export         _snd_init, _snd_off, _snd_click
        .export         _snd_goal, _snd_whistle, _snd_bad
        .export         _snd_set
        .import         popa

VIA_PRB  = $0300
VIA_DDRB = $0302
VIA_DDRA = $0303
VIA_PCR  = $030C
VIA_PRA  = $030F

        .bss
snd_reg:        .res    1
snd_val:        .res    1
snd_base:       .res    1
snd_lo:         .res    1
snd_hi:         .res    1

        .code

; A = register, X = value
; Interrupts are masked for the four bus phases: the ROM's keyboard
; scan (and our own) drives the same VIA/AY handshake, and a tick in the
; middle of the sequence would latch the wrong register.
_snd_ay:
        php
        sei
        sta     snd_reg
        stx     snd_val
        lda     VIA_PCR
        and     #$11
        sta     snd_base

        lda     snd_reg
        sta     VIA_PRA
        lda     snd_base
        ora     #$EE
        sta     VIA_PCR
        lda     snd_base
        ora     #$CC
        sta     VIA_PCR

        lda     snd_val
        sta     VIA_PRA
        lda     snd_base
        ora     #$EC
        sta     VIA_PCR
        lda     snd_base
        ora     #$CC
        sta     VIA_PCR
        plp
        rts

; ----------------------------------------------------------------------
; void snd_set (unsigned char reg, unsigned char val)
;   Escape hatch used by the test programs to poke AY registers.
_snd_set:
        sta     snd_val         ; A = value
        jsr     popa            ; A = register
        ldx     snd_val
        jmp     _snd_ay

; ----------------------------------------------------------------------
; void snd_init (void)
_snd_init:
        lda     #7
        ldx     #$7E            ; tone A on; port A stays an input, which
                                ; the keyboard scan depends on ($3E breaks it)
        jsr     _snd_ay
        lda     #8
        ldx     #0
        jsr     _snd_ay
        lda     #0
        ldx     #0
        jsr     _snd_ay
        lda     #1
        ldx     #0
        jmp     _snd_ay

; ----------------------------------------------------------------------
; void snd_off (void)
_snd_off:
        lda     #8
        ldx     #0
        jmp     _snd_ay

; ----------------------------------------------------------------------
; void snd_tone (unsigned int period) - internal
_snd_tone:
        sta     snd_lo
        stx     snd_hi
        lda     #0
        ldx     snd_lo
        jsr     _snd_ay
        lda     #1
        ldx     snd_hi
        jsr     _snd_ay
        lda     #8
        ldx     #13
        jmp     _snd_ay

; ----------------------------------------------------------------------
; void snd_delay (unsigned int n) - roughly n * 1000 cycles
_snd_delay:
        sta     snd_lo
        stx     snd_hi
@outer: ldx     #200
@inner: dex
        bne     @inner
        lda     snd_lo
        bne     @dec
        lda     snd_hi
        beq     @done
        dec     snd_hi
@dec:   dec     snd_lo
        jmp     @outer
@done:  rts

; ----------------------------------------------------------------------
; void snd_click (void)
_snd_click:
        lda     #<420
        ldx     #>420
        jsr     _snd_tone
        lda     #3
        ldx     #0
        jsr     _snd_delay
        jmp     _snd_off

; ----------------------------------------------------------------------
; void snd_bad (void) - low buzz
_snd_bad:
        lda     #<500
        ldx     #>500
        jsr     _snd_tone
        lda     #10
        ldx     #0
        jsr     _snd_delay
        jmp     _snd_off

; ----------------------------------------------------------------------
; void snd_goal (void) - rising three-note jingle
_snd_goal:
        lda     #<238
        ldx     #>238
        jsr     _snd_tone
        lda     #40
        ldx     #0
        jsr     _snd_delay
        lda     #<189
        ldx     #>189
        jsr     _snd_tone
        lda     #40
        ldx     #0
        jsr     _snd_delay
        lda     #<159
        ldx     #>159
        jsr     _snd_tone
        lda     #60
        ldx     #0
        jsr     _snd_delay
        jmp     _snd_off

; ----------------------------------------------------------------------
; void snd_whistle (void)
_snd_whistle:
        lda     #6
        ldx     #8              ; noise period
        jsr     _snd_ay
        lda     #7
        ldx     #$77            ; noise A on, tones off, port A still input
        jsr     _snd_ay
        lda     #8
        ldx     #13
        jsr     _snd_ay
        lda     #70
        ldx     #0
        jsr     _snd_delay
        lda     #7
        ldx     #$7E
        jsr     _snd_ay
        jmp     _snd_off
