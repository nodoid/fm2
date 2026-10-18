;
; tape.s - save/restore the game using the Atmos ROM's cassette routines.
;
; Entry points (BASIC 1.1B, Atmos):
;   $E76A SetupTape        motor + VIA timer
;   $E607 WriteFileHeader  leader, $24, 9 header bytes, filename
;   $E62E WriteDataBlock   FILESTART..FILEEND inclusive
;   $E4AC TapeSync         hunt $24, read header, search for the name
;   $E4E0 GetTapeData      read the block into FILESTART..FILEEND
;   $E93D RestoreVIAState  (cassette close)
;
; The game runs with IRQs masked; these routines are polled, as they are
; when BASIC performs CSAVE/CLOAD, so that is safe.
;
; C interface:
;   extern unsigned char *tape_ptr;
;   extern unsigned int   tape_len;
;   extern char           tape_name[16];
;   unsigned char tape_save_block(void);
;   unsigned char tape_load_block(void);
;
        .export         _tape_save_block, _tape_load_block
        .export         _tape_ptr, _tape_len, _tape_name

FILESTART = $02A9
FILEEND   = $02AB
AUTORUN   = $02AD
LANGFLAG  = $02AE
LOADERR   = $02B1
CNAME     = $027F

        .bss
_tape_ptr:      .res    2
_tape_len:      .res    2
_tape_name:     .res    16

        .code

; ----------------------------------------------------------------------
; clear the ROM's tape state flags
_tape_clear:
        lda     #0
        sta     $024D
        sta     AUTORUN
        sta     LANGFLAG
        sta     $025A
        sta     $025B
        sta     $025C
        sta     $025D
        sta     LOADERR
        sta     $02A8           ; plain data block, no auto-run
        rts

; ----------------------------------------------------------------------
; copy tape_name to CNAME (zero terminated, max 16 chars)
_tape_setname:
        ldy     #0
@copy:  lda     _tape_name,y
        beq     @term
        sta     CNAME,y
        iny
        cpy     #16
        bne     @copy
@term:  lda     #0
        sta     CNAME,y
        rts

; ----------------------------------------------------------------------
; set FILESTART/FILEEND from tape_ptr/tape_len (inclusive end)
_tape_setrange:
        lda     _tape_ptr
        sta     FILESTART
        lda     _tape_ptr+1
        sta     FILESTART+1
        clc
        lda     _tape_ptr
        adc     _tape_len
        sta     FILEEND
        lda     _tape_ptr+1
        adc     _tape_len+1
        sta     FILEEND+1
        lda     FILEEND
        bne     @dec
        dec     FILEEND+1
@dec:   dec     FILEEND
        rts

; ----------------------------------------------------------------------
; unsigned char tape_save_block (void)
_tape_save_block:
        jsr     _tape_clear
        jsr     _tape_setname
        jsr     _tape_setrange
        jsr     $E76A
        jsr     $E607
        jsr     $E62E
        jsr     $E93D
        lda     #1
        ldx     #0
        rts

; ----------------------------------------------------------------------
; unsigned char tape_load_block (void)
_tape_load_block:
        jsr     _tape_clear
        jsr     _tape_setname
        jsr     _tape_setrange
        jsr     $E76A
        jsr     $E4AC
        jsr     $E4E0
        jsr     $E93D
        lda     LOADERR
        ora     $025D
        beq     @ok
        lda     #0
        ldx     #0
        rts
@ok:    lda     #1
        ldx     #0
        rts
