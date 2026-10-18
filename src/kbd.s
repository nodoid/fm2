;
; kbd.s - interrupt driven keyboard input for Football Manager 2.
;
; The Oric's 50 Hz VIA timer interrupt is hooked (cc65 installs a stub that
; calls handlers declared with .interruptor and then chains to the ROM's own
; handler, so BASIC's book-keeping carries on as usual).  Every tick the
; matrix is scanned here:
;
;   VIA PB0-2 select a keyboard row, PB3 is the key-down sense line and
;   the AY-3-8912 port A (register 14) drives one column low at a time,
;   using the same VIA PCR bus sequence as the ROM's ReadKbdCol.
;
; Rows with no key down cost one PSG access, so an idle machine is barely
; touched; a key press is decoded with the same table the ROM uses and
; pushed into an eight byte queue together with auto-repeat.
;
; Reading keys from an interrupt means a keystroke made while the game is
; busy redrawing a screen is still waiting when the menu comes back for
; input - polling would simply lose it.
;
; API:
;   void kbd_init(void);
;   unsigned char kbd_get(void);      /* 0 = nothing waiting */
;   unsigned char kbd_wait(void);
;   unsigned int kbd_ticks;           /* 50 Hz frame counter */
;   unsigned char kbd_suspend;        /* set during tape I/O */
;
        .export         _kbd_init, _kbd_get, _kbd_wait
        .export         _kbd_ticks, _kbd_suspend
        .export         _kbd_dbg_head, _kbd_dbg_tail, _kbd_dbg_cur, _kbd_dbg_q
        .interruptor    kbd_irq

VIA_PRB  = $0300
VIA_DDRB = $0302
VIA_DDRA = $0303
VIA_PCR  = $030C
VIA_PRA  = $030F

K_UP     = $E3
K_DOWN   = $E4
K_LEFT   = $E5
K_RIGHT  = $E6

        .bss
kbd_row:        .res    1
kbd_col:        .res    1
kbd_bit:        .res    1
kbd_idx:        .res    1
kbd_shift:      .res    1
kbd_new:        .res    1
kbd_rep_i:      .res    1
kbd_rep_d:      .res    1
_kbd_dbg_head:  .res    1
_kbd_dbg_tail:  .res    1
_kbd_dbg_q:     .res    8
_kbd_dbg_cur:   .res    8
kbd_prev:       .res    8
ay_reg:         .res    1
ay_val:         .res    1
ay_base:        .res    1

_kbd_ticks:     .res    2
_kbd_suspend:   .res    1

        .code

; ----------------------------------------------------------------------
; ay_write: A = register, X = value
_ay:
        sta     ay_reg
        stx     ay_val
        lda     VIA_PCR
        and     #$11
        sta     ay_base

        lda     ay_reg
        sta     VIA_PRA
        lda     ay_base
        ora     #$EE
        sta     VIA_PCR
        lda     ay_base
        ora     #$CC
        sta     VIA_PCR

        lda     ay_val
        sta     VIA_PRA
        lda     ay_base
        ora     #$EC
        sta     VIA_PCR
        lda     ay_base
        ora     #$CC
        sta     VIA_PCR
        rts

; ----------------------------------------------------------------------
; void kbd_init (void)
;   The ROM has already left DDRA/DDRB the way both it and we need them;
;   this only makes sure and empties the queue.
_kbd_init:
        lda     #$FF
        sta     VIA_DDRA
        lda     #$F7
        sta     VIA_DDRB
        lda     #$B8
        sta     VIA_PRB
        lda     #$0E
        ldx     #$00
        jsr     _ay

        lda     #0
        sta     _kbd_dbg_head
        sta     _kbd_dbg_tail
        sta     _kbd_suspend
        sta     _kbd_ticks
        sta     _kbd_ticks+1
        lda     #$FF
        sta     kbd_rep_i
        ldx     #7
        lda     #0
@clr:   sta     kbd_prev,x
        sta     _kbd_dbg_cur,x
        dex
        bpl     @clr
        rts

; ----------------------------------------------------------------------
; unsigned char kbd_get (void) - pop one queued key code, 0 if empty
_kbd_get:
        ldx     _kbd_dbg_head
        cpx     _kbd_dbg_tail
        beq     @empty
        lda     _kbd_dbg_q,x
        pha                     ; keep the key code safe
        inx
        txa
        and     #7
        sta     _kbd_dbg_head
        pla
        rts
@empty: lda     #0
        rts

; ----------------------------------------------------------------------
; unsigned char kbd_wait (void)
_kbd_wait:
        jsr     _kbd_get
        tax
        beq     _kbd_wait
        txa
        rts

; ----------------------------------------------------------------------
; push: A = key code (never zero)
_push:
        pha
        ldx     _kbd_dbg_tail
        pla
        sta     _kbd_dbg_q,x
        inx
        txa
        and     #7
        sta     _kbd_dbg_tail
        rts

; ----------------------------------------------------------------------
; scan: build _kbd_dbg_cur, one bit per key down (bit 7 = column 0)
_scan:
        php
        sei
        ldx     #7
        lda     #0
@clr:   sta     _kbd_dbg_cur,x
        dex
        bpl     @clr

        lda     #0
        sta     kbd_row
@row:   lda     #$0E
        ldx     #$00
        jsr     _ay                    ; all columns low
        lda     kbd_row
        ora     #$B8
        sta     VIA_PRB
        lda     VIA_PRB
        lda     VIA_PRB                ; settle (two reads, like the ROM)
        and     #$08
        beq     @next_row              ; nothing down in this row

        lda     #$01
        sta     kbd_col
        lda     #$80
        sta     kbd_bit
@col:   lda     kbd_col
        eor     #$FF
        tax
        lda     #$0E
        jsr     _ay
        lda     kbd_row
        ora     #$B8
        sta     VIA_PRB
        lda     VIA_PRB
        lda     VIA_PRB
        and     #$08
        beq     @nokey
        ldx     kbd_row
        lda     _kbd_dbg_cur,x
        ora     kbd_bit
        sta     _kbd_dbg_cur,x
@nokey: lsr     kbd_bit
        asl     kbd_col
        bne     @col
@next_row:
        inc     kbd_row
        lda     kbd_row
        cmp     #8
        bne     @row

        lda     _kbd_dbg_cur+4              ; shift = left shift / right shift
        ora     _kbd_dbg_cur+7
        and     #$08
        sta     kbd_shift
        plp
        rts

; ----------------------------------------------------------------------
; copy_prev: kbd_prev = _kbd_dbg_cur
_copy_prev:
        ldx     #7
@l:     lda     _kbd_dbg_cur,x
        sta     kbd_prev,x
        dex
        bpl     @l
        rts

; ----------------------------------------------------------------------
; new_index: A = index (row*8+col) of a key pressed since the last scan,
;            or $FF.  kbd_prev is updated.
_new_index:
        lda     #0
        sta     kbd_row
@row:   ldx     kbd_row
        lda     _kbd_dbg_cur,x
        sta     kbd_new
        lda     kbd_prev,x
        eor     #$FF
        and     kbd_new
        sta     kbd_new
        bne     @found
        inc     kbd_row
        lda     kbd_row
        cmp     #8
        bne     @row
        jsr     _copy_prev
        lda     #$FF
        rts
@found: lda     #$80
        sta     kbd_bit
        lda     #0
        sta     kbd_idx
@bit:   lda     kbd_new
        and     kbd_bit
        bne     @got
        lsr     kbd_bit
        inc     kbd_idx
        jmp     @bit
@got:   jsr     _copy_prev
        lda     kbd_row
        asl     a
        asl     a
        asl     a
        clc
        adc     kbd_idx
        rts

; ----------------------------------------------------------------------
; bit_down: A = index; carry set if that key is still down
_bit_down:
        sta     kbd_idx
        and     #7
        tax
        lda     bitmask,x
        sta     kbd_bit
        lda     kbd_idx
        lsr     a
        lsr     a
        lsr     a
        tax
        lda     _kbd_dbg_cur,x
        and     kbd_bit
        beq     @up
        sec
        rts
@up:    clc
        rts

; ----------------------------------------------------------------------
; emit: A = index; decode through the key tables and queue the character
_emit:
        tax
        lda     kbd_shift
        beq     @lower
        lda     key_upper,x
        jmp     @norm
@lower: lda     key_lower,x
@norm:  jsr     _normalise
        beq     @skip
        jmp     _push
@skip:  rts

; ----------------------------------------------------------------------
; normalise: letters to upper case, modifier codes to zero
_normalise:
        cmp     #'a'
        bcc     @special
        cmp     #'z'+1
        bcs     @special
        and     #$DF
        rts
@special:
        cmp     #$80
        bcc     @ret
        cmp     #K_UP
        bcc     @zero
        cmp     #$E7
        bcs     @zero
@ret:   rts
@zero:  lda     #0
        rts

; ----------------------------------------------------------------------
; The 50 Hz tick.  Everything the ROM's handler does (tape timing, BASIC
; book-keeping) still happens: cc65 chains to the saved vector for us.
kbd_irq:
        inc     _kbd_ticks
        bne     @ticks
        inc     _kbd_ticks+1
@ticks: lda     _kbd_suspend
        bne     @out
        php
        jsr     _scan
        jsr     _new_index
        cmp     #$FF
        bne     @pressed

        ; held-key auto repeat
        lda     kbd_rep_i
        cmp     #$FF
        beq     @done
        jsr     _bit_down
        bcc     @stop
        dec     kbd_rep_d
        bne     @done
        lda     #4
        sta     kbd_rep_d
        lda     kbd_rep_i
        jsr     _emit
        jmp     @done
@stop:  lda     #$FF
        sta     kbd_rep_i
        jmp     @done

@pressed:
        sta     kbd_rep_i
        lda     #18
        sta     kbd_rep_d
        lda     kbd_rep_i
        jsr     _emit
@done:  plp
@out:   rts

; ----------------------------------------------------------------------
        .rodata
bitmask:
        .byte   $80,$40,$20,$10,$08,$04,$02,$01

; Key tables, indexed row*8 + column bit (bit 7 first); the layout follows
; the physical Oric keyboard.
key_lower:
        .byte   '7','n','5','v',$E8,'1','x','3'
        .byte   'j','t','r','f',0,$1B,'q','d'
        .byte   'm','6','b','4',$E8,'z','2','c'
        .byte   'k','9',';','-',0,0,92,39
        .byte   ' ',',','.',K_UP,$E1,K_LEFT,K_DOWN,K_RIGHT
        .byte   'u','i','o','p',$E7,8,']','['
        .byte   'y','h','g','e',0,'a','s','w'
        .byte   '8','l','0','/',$E2,13,0,'='
key_upper:
        .byte   '&','N','%','V',$E8,'!','X','#'
        .byte   'J','T','R','F',0,$1B,'Q','D'
        .byte   'M','^','B','$',$E8,'Z','@','C'
        .byte   'K','(',';','_',0,0,'|','"'
        .byte   ' ',',','.',K_UP,$E1,K_LEFT,K_DOWN,K_RIGHT
        .byte   'U','I','O','P',$E7,8,'}','{'
        .byte   'Y','H','G','E',0,'A','S','W'
        .byte   '*','L',')','?',$E2,13,0,'+'
