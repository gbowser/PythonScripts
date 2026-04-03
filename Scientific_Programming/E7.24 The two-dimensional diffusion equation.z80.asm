; Two-dimensional diffusion on a square plate
; Practical Z80 assembly version inspired by the Python program.
;
; Notes
; - This is written as Z80 assembly source, since raw machine-code bytes
;   would be unreadable and hard to modify.
; - A plain Z80 is not well suited to the original 100x100 floating-point
;   Python simulation, so this version uses:
;     * a smaller 16x16 grid
;     * integer temperatures
;     * a simple 4-neighbour averaging update
; - The edges are left unchanged by updating only the interior cells.
;
; The program:
; 1. fills the grid with a cool temperature
; 2. creates a hot square near the centre
; 3. runs a number of diffusion steps
; 4. leaves the final temperatures in GridCurrent
;
; This source is written in a fairly generic Z80 style.

                ORG     8000h

GRID_WIDTH      EQU     16
GRID_HEIGHT     EQU     16
GRID_SIZE       EQU     GRID_WIDTH*GRID_HEIGHT

COOL_TEMP       EQU     30
HOT_TEMP        EQU     70
NUM_STEPS       EQU     40

                JP      Start

; ------------------------------------------------------------
; Start-up
; ------------------------------------------------------------

Start:
                CALL    InitializeGrid
                CALL    MakeHotRegion

                LD      B,NUM_STEPS
TimeLoop:
                PUSH    BC
                CALL    DoTimeStep
                CALL    CopyNextToCurrent
                POP     BC
                DJNZ    TimeLoop

Finished:
                JP      Finished

; ------------------------------------------------------------
; Fill the whole current grid with the cool temperature.
; ------------------------------------------------------------

InitializeGrid:
                LD      HL,GridCurrent
                LD      DE,GridCurrent+1
                LD      BC,GRID_SIZE-1
                LD      (HL),COOL_TEMP
                LDIR

                LD      HL,GridNext
                LD      DE,GridNext+1
                LD      BC,GRID_SIZE-1
                LD      (HL),COOL_TEMP
                LDIR
                RET

; ------------------------------------------------------------
; Create a small hot 4x4 block in the middle of the plate.
; Rows 7..10 and columns 7..10 in 1-based human numbering.
; In zero-based indexing that becomes rows 6..9, cols 6..9.
; ------------------------------------------------------------

MakeHotRegion:
                LD      B,4                  ; 4 rows
                LD      HL,GridCurrent+(6*GRID_WIDTH)+6
HotRowLoop:
                PUSH    BC
                LD      C,4                  ; 4 columns
HotColLoop:
                LD      (HL),HOT_TEMP
                INC     HL
                DEC     C
                JR      NZ,HotColLoop

                LD      DE,GRID_WIDTH-4
                ADD     HL,DE
                POP     BC
                DJNZ    HotRowLoop
                RET

; ------------------------------------------------------------
; Perform one diffusion step.
;
; For each interior cell:
; next = (centre + left + right + up + down) / 5
;
; This is not the exact floating-point PDE update from Python, but it
; gives the same qualitative "heat spreads out" behaviour and is much
; more realistic for a small Z80 implementation.
; ------------------------------------------------------------

DoTimeStep:
                ; Start by copying current grid to next grid so the
                ; edge cells stay unchanged.
                CALL    CopyCurrentToNext

                LD      D,1                  ; y = 1 .. 14
RowLoop:
                LD      A,D
                CP      GRID_HEIGHT-1
                RET     NC

                LD      E,1                  ; x = 1 .. 14
ColLoop:
                LD      A,E
                CP      GRID_WIDTH-1
                JR      NC,NextRow

                PUSH    DE
                CALL    UpdateCell
                POP     DE

                INC     E
                JR      ColLoop

NextRow:
                INC     D
                JR      RowLoop

; ------------------------------------------------------------
; Update one interior cell.
; Input:
;   D = row index y
;   E = column index x
; Uses:
;   HL points to centre cell in GridCurrent
;   BC used as a 16-bit running sum
; ------------------------------------------------------------

UpdateCell:
                PUSH    DE
                CALL    GetCurrentAddress
                PUSH    HL

                LD      B,0
                LD      C,(HL)               ; centre

                DEC     HL
                LD      A,(HL)               ; left
                ADD     A,C
                LD      C,A
                JR      NC,NoCarry1
                INC     B
NoCarry1:

                INC     HL
                INC     HL
                LD      A,(HL)               ; right
                ADD     A,C
                LD      C,A
                JR      NC,NoCarry2
                INC     B
NoCarry2:

                POP     HL
                PUSH    HL
                LD      DE,-GRID_WIDTH
                ADD     HL,DE
                LD      A,(HL)               ; up
                ADD     A,C
                LD      C,A
                JR      NC,NoCarry3
                INC     B
NoCarry3:

                POP     HL
                PUSH    HL                   ; keep stack balanced
                LD      DE,GRID_WIDTH
                ADD     HL,DE
                LD      A,(HL)               ; down
                ADD     A,C
                LD      C,A
                JR      NC,NoCarry4
                INC     B
NoCarry4:

                ; Divide the 16-bit sum BC by 5 using repeated subtraction.
                LD      D,0                  ; quotient
DivideBy5:
                LD      A,B
                OR      A
                JR      NZ,DoSubtract
                LD      A,C
                CP      5
                JR      C,StoreAverage

DoSubtract:
                LD      A,C
                SUB     5
                LD      C,A
                JR      NC,NoBorrow
                DEC     B
NoBorrow:
                INC     D
                JR      DivideBy5

StoreAverage:
                LD      A,D
                LD      (QuotientTemp),A
                POP     HL                   ; discard saved centre address
                POP     DE                   ; restore x,y coordinates
                CALL    GetNextAddress
                LD      A,(QuotientTemp)
                LD      (HL),A
                RET

; ------------------------------------------------------------
; Copy GridCurrent to GridNext
; ------------------------------------------------------------

CopyCurrentToNext:
                LD      HL,GridCurrent
                LD      DE,GridNext
                LD      BC,GRID_SIZE
                LDIR
                RET

; ------------------------------------------------------------
; Copy GridNext back into GridCurrent
; ------------------------------------------------------------

CopyNextToCurrent:
                LD      HL,GridNext
                LD      DE,GridCurrent
                LD      BC,GRID_SIZE
                LDIR
                RET

; ------------------------------------------------------------
; Compute address of GridCurrent[y][x]
; Input:
;   D = y, E = x
; Output:
;   HL = address in GridCurrent
; ------------------------------------------------------------

GetCurrentAddress:
                LD      H,0
                LD      L,D
                ADD     HL,HL               ; *2
                ADD     HL,HL               ; *4
                ADD     HL,HL               ; *8
                ADD     HL,HL               ; *16
                LD      A,E
                LD      C,A
                LD      B,0
                ADD     HL,BC
                LD      BC,GridCurrent
                ADD     HL,BC
                RET

; ------------------------------------------------------------
; Compute address of GridNext[y][x]
; Input:
;   D = y, E = x
; Output:
;   HL = address in GridNext
; ------------------------------------------------------------

GetNextAddress:
                LD      H,0
                LD      L,D
                ADD     HL,HL               ; *2
                ADD     HL,HL               ; *4
                ADD     HL,HL               ; *8
                ADD     HL,HL               ; *16
                LD      A,E
                LD      C,A
                LD      B,0
                ADD     HL,BC
                LD      BC,GridNext
                ADD     HL,BC
                RET

; ------------------------------------------------------------
; Storage
; ------------------------------------------------------------

GridCurrent:
                DS      GRID_SIZE

GridNext:
                DS      GRID_SIZE

QuotientTemp:
                DB      00h
