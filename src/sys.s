;
; sys.s - small system helpers for Football Manager 2.
;
;   void soft_reset (void);   /* back to BASIC, cold start */
;
; $FFFC is the 6502 reset vector; on the Oric the ROM leaves it pointing at
; the reset entry, which cold starts BASIC.  Keeping the jump in assembler
; avoids an inline __asm__ in C, which upsets cc65's branch optimiser.
;
        .export         _soft_reset

        .code

_soft_reset:
        jmp     ($FFFC)
