import sys
sys.path.insert(0, "/workspace/scripts")
from ft2util import call
from compose_util import set_cell, set_cell_drum
import song_data as SD

ROWS_PER_BAR = 16
PATTERN_ROWS = 64

CH_KICK, CH_SNARE, CH_HAT, CH_BASS, CH_ARP, CH_LEAD, CH_HARM, CH_SPARK = range(8)

def place_bass(pat, row0, bar, pattern_list, vol_scale=1.0):
    chord = SD.CHORD[bar]
    kind_note = {"root": chord["bass"], "fifth": SD.BASS_FIFTH[bar], "oct": SD.BASS_OCT[bar]}
    for row, kind, vol in pattern_list:
        set_cell(pat, row0+row, CH_BASS, "BASS", kind_note[kind], int(vol*vol_scale))

def place_arp(pat, row0, bar, arp_list, vol_scale=1.0):
    tones = SD.CHORD[bar]["arp"]
    for row, idx, vol in arp_list:
        set_cell(pat, row0+row, CH_ARP, "ARP", tones[idx], int(vol*vol_scale))

def place_lead(pat, row0, lead_list):
    for row, name, vol in lead_list:
        set_cell(pat, row0+row, CH_LEAD, "LEAD", name, vol)

def place_harmony(pat, row0, bar, vol=30):
    note = SD.HARMONY[bar]
    set_cell(pat, row0, CH_HARM, "ARP", note, vol)

def place_sparkle(pat, row0, items):
    for row, name, vol in items:
        set_cell(pat, row0+row, CH_SPARK, "LEAD", name, vol)

def place_kick(pat, row0, rows, vol=62):
    for row in rows:
        set_cell_drum(pat, row0+row, CH_KICK, "KICK", vol)

def place_snare(pat, row0, rows, vol=54, use_clap=False):
    name = "CLAP" if use_clap else "SNARE"
    for row in rows:
        set_cell_drum(pat, row0+row, CH_SNARE, name, vol)

def place_hat(pat, row0, rows_open, vol_closed=40, vol_open=34, step=2, skip_accentless=False):
    for row, is_open in rows_open:
        if is_open:
            set_cell_drum(pat, row0+row, CH_HAT, "HATOPEN", vol_open)
        else:
            accent = vol_closed+10 if row % 8 == 0 else vol_closed
            set_cell_drum(pat, row0+row, CH_HAT, "HATCLOSED", accent)

def clear_pattern(p, rows=PATTERN_ROWS):
    call("pattern_clear", {"pattern": p})
    call("pattern_set_length", {"pattern": p, "rows": rows})

def build_pattern_A(p=0):
    clear_pattern(p)
    for bi, bar in enumerate(SD.BARS):
        row0 = bi*ROWS_PER_BAR
        bp = SD.bass_pattern_main() if bi % 2 == 0 else SD.bass_pattern_alt()
        place_bass(p, row0, bar, bp)
        order = (0,1,2,1) if bar in ("Am","C") else (2,1,0,1)
        place_arp(p, row0, bar, SD.arp_pattern(order))
        place_lead(p, row0, SD.LEAD_A[bar])
        place_harmony(p, row0, bar, vol=28)
        place_kick(p, row0, SD.kick_rows(0))
        place_snare(p, row0, SD.snare_rows())
        place_hat(p, row0, SD.hat_rows())

def build_pattern_B(p=1):
    clear_pattern(p)
    for bi, bar in enumerate(SD.BARS):
        row0 = bi*ROWS_PER_BAR
        bp = SD.bass_pattern_alt() if bi % 2 == 0 else SD.bass_pattern_main()
        place_bass(p, row0, bar, bp)
        order = (2,1,0,1) if bar in ("Am","C") else (0,1,2,1)
        place_arp(p, row0, bar, SD.arp_pattern(order))
        place_lead(p, row0, SD.LEAD_B[bar])
        place_harmony(p, row0, bar, vol=30)
        place_kick(p, row0, SD.kick_rows(1))
        place_snare(p, row0, SD.snare_rows())
        place_hat(p, row0, SD.hat_rows())
        place_sparkle(p, row0, SD.SPARKLE_B[bar])

def build_pattern_C(p=2):
    clear_pattern(p)
    for bi, bar in enumerate(SD.BARS):
        row0 = bi*ROWS_PER_BAR
        bp = SD.bass_pattern_main()
        place_bass(p, row0, bar, bp, vol_scale=0.8)
        order = (0,1,2,1)
        place_arp(p, row0, bar, SD.arp_pattern_sparse(order), vol_scale=0.85)
        place_lead(p, row0, SD.LEAD_C[bar])
        place_harmony(p, row0, bar, vol=26)
        if bi < 3:
            place_kick(p, row0, [0,8], vol=56)
            place_hat(p, row0, [(r, False) for r in range(0,16,4)], vol_closed=30)
        else:
            # build-up into loop restart: busier hats + snare pickup
            place_kick(p, row0, [0,6,8,12], vol=60)
            place_snare(p, row0, [12], vol=50)
            place_hat(p, row0, [(r, False) for r in range(0,16,2)], vol_closed=36)
            place_hat(p, row0, [(14, True)], vol_open=36)

if __name__ == "__main__":
    build_pattern_A(0)
    build_pattern_B(1)
    build_pattern_C(2)
    call("order_set", {"position":0, "pattern":0})
    call("order_set", {"position":1, "pattern":1})
    call("order_set", {"position":2, "pattern":0})
    call("order_set", {"position":3, "pattern":2})
    call("song_set", {"name":"KEYGEN DREAMS", "bpm":150, "speed":6, "length":4, "loop_start":0, "channels":8})
    print("patterns built")
