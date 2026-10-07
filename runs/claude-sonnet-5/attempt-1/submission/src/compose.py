import sys
sys.path.insert(0, '.')
from ftclient import jcall, call
import theory as T
import load_instruments as L

I = {}  # filled after build()

CH = dict(KICK=0, SNARE=1, CLAP=2, HATC=3, HATO=4, FX1=5, BASS=6, LEAD=7,
          LEAD2=8, ARP=9, PADA=10, PADB=11, PADC=12, FX2=13)

ROWS_PER_BAR = 16
BARS_PER_PAT = 4
PAT_ROWS = ROWS_PER_BAR * BARS_PER_PAT

# ---- harmony: Am - F - C - G (i - VI - III - VII in A natural minor) -------
CHORDS = [
    dict(bass="A-2", pad=["A-3", "C-4", "E-4"], lead_root="A-4"),
    dict(bass="F-2", pad=["A-3", "C-4", "F-4"], lead_root="F-4"),
    dict(bass="C-3", pad=["G-3", "C-4", "E-4"], lead_root="C-5"),
    dict(bass="G-2", pad=["G-3", "B-3", "D-4"], lead_root="G-4"),
]


# This FT2 build's default module_render gain (used when the caller omits
# "amp") is a fixed x16 multiply, not a normalizer. A full-mix 14-channel
# module can clip hard at that default gain, so every note volume is scaled
# down by MASTER_GAIN first -- tuned (see analyze.py) so the heaviest
# section still sits safely under full scale even at the default x16 amp.
MASTER_GAIN = 0.50


def clamp_vol(v):
    return max(0, min(64, int(round(v * MASTER_GAIN))))


def note_at(pattern, row, channel, note, instrument, volume):
    if row < 0 or row >= PAT_ROWS:
        return
    # NOTE: the volume *column* has a rendering bug in this FT2 build (it
    # ends up playing back as max(0, vol-16), with vol<16 falling back to a
    # fixed default instead of being quiet/silent). The effect column's "set
    # volume" command (effect 12 / Cxx) renders correctly and linearly across
    # the whole 0..64 range, so every note's volume is set that way instead.
    call("pattern_set_cell", pattern=pattern, row=row, channel=channel,
         note=note, instrument=instrument, effect=12, effect_param=clamp_vol(volume))


def hits(pattern, channel, instrument, rows, volume, note="C-4"):
    for r in rows:
        note_at(pattern, r, channel, note, instrument, volume)


def hits_accent(pattern, channel, instrument, rows, accent_rows, v_hi, v_lo, note="C-4"):
    accent_rows = set(accent_rows)
    for r in rows:
        note_at(pattern, r, channel, note, instrument, v_hi if r in accent_rows else v_lo)


def hits_accent_panflip(pattern, channel, inst_a, inst_b, rows, accent_rows, v_hi, v_lo,
                         note="C-4"):
    """Like hits_accent but alternates between two identical-sounding
    instruments (pre-panned hard left / hard right at load time) for a
    classic ping-pong hi-hat flutter -- avoids needing the volume column and
    a panning effect in the same cell at once."""
    accent_rows = set(accent_rows)
    for i, r in enumerate(rows):
        vol = v_hi if r in accent_rows else v_lo
        inst = inst_a if i % 2 == 0 else inst_b
        note_at(pattern, r, channel, note, inst, vol)


def shape(pattern, channel, instrument, bar_base, root_name, positions, steps, volume):
    for pos, st in zip(positions, steps):
        nm = T.degree_step(root_name, st)
        note_at(pattern, bar_base + pos, channel, nm, instrument, volume)


def pad_chord(pattern, bar_base, row, chord_notes, vol):
    chans = [CH['PADA'], CH['PADB'], CH['PADC']]
    insts = [I['PadL'], I['PadMid'], I['PadR']]
    for ch, inst, nm in zip(chans, insts, chord_notes):
        note_at(pattern, bar_base + row, ch, nm, inst, vol)


# ------------------------------------------------------------ rhythm shapes
SH_ARP8 = (list(range(0, 16, 2)), [0, 2, 4, 2, 0, 1, 2, 0])
SH_ANSWER = ([0, 4, 8, 12, 14], [0, 4, 2, 0, 2])
SH_ARP16 = (list(range(16)), [0, 2, 4, 7] * 4)
SH_ARP8_AIR = (list(range(0, 16, 2)), [0, 4, 7, 4, 0, 4, 7, 4])
SH_BASS_GROOVE = ([0, 4, 6, 8, 12, 14], [0, 0, 7, 0, 0, 7])
SH_BASS_BUSY = (list(range(0, 16, 2)), [0, 0, 7, 0, 0, 0, 7, 0])
SH_BASS_ROOTS = ([0], [0])
SH_BASS_HALF = ([0, 8], [0, 0])


def bar_base(bar):
    return bar * ROWS_PER_BAR


def build_pattern(idx, rows=PAT_ROWS):
    jcall("pattern_set_length", pattern=idx, rows=rows)
    jcall("pattern_clear", pattern=idx)


# --------------------------------------------------------------- sections --

def drums_common(pattern, kick_rows, kick_vol, hat_chan, hat_inst, hat_rows,
                  hat_accent, hat_hi, hat_lo, snare_rows, snare_vol,
                  clap_rows=None, clap_vol=0, openhat_rows=None, openhat_vol=0,
                  bar=0, hat_panflip=False):
    b = bar_base(bar)
    hits(pattern, CH['KICK'], I['Kick'], [b + r for r in kick_rows], kick_vol)
    if hat_panflip:
        hits_accent_panflip(pattern, hat_chan, I['HatClosedA'], I['HatClosedB'],
                             [b + r for r in hat_rows], [b + r for r in hat_accent],
                             hat_hi, hat_lo)
    else:
        hits_accent(pattern, hat_chan, hat_inst, [b + r for r in hat_rows],
                    [b + r for r in hat_accent], hat_hi, hat_lo)
    if snare_rows:
        hits(pattern, CH['SNARE'], I['Snare'], [b + r for r in snare_rows], snare_vol)
    if clap_rows:
        hits(pattern, CH['CLAP'], I['Clap'], [b + r for r in clap_rows], clap_vol)
    if openhat_rows:
        hits(pattern, CH['HATO'], I['HatOpen'], [b + r for r in openhat_rows], openhat_vol)


def P0_intro(idx):
    build_pattern(idx)
    for bar in range(4):
        b = bar_base(bar)
        kick_rows = [0, 8] if bar >= 1 else [0]
        hits(idx, CH['KICK'], I['Kick'], [b + r for r in kick_rows], 46)
        hat_rows = [0, 4, 8, 12] if bar < 2 else [0, 2, 4, 6, 8, 10, 12, 14]
        hits_accent(idx, CH['HATC'], I['HatClosed'], [b + r for r in hat_rows],
                    [b + 0, b + 4, b + 8, b + 12], 30, 18)
        ch = CHORDS[bar]
        pad_vol = 16 + bar * 8
        pad_chord(idx, b, 0, ch['pad'], pad_vol)
        if bar >= 1:
            arp_vol = 16 + (bar - 1) * 8
            shape(idx, CH['ARP'], I['Arp'], b, ch['lead_root'], *SH_ARP8_AIR, arp_vol)
        if bar >= 2:
            hits(idx, CH['BASS'], I['Bass'], [b], 34, note=ch['bass'])
    # tiny lead-in tom pickup into P1
    note_at(idx, bar_base(3) + 14, CH['FX1'], "G-3", I['Tom'], 34)
    note_at(idx, bar_base(3) + 15, CH['FX1'], "E-3", I['Tom'], 30)


def P1_verse(idx):
    build_pattern(idx)
    for bar in range(4):
        b = bar_base(bar)
        ch = CHORDS[bar]
        drums_common(idx, [0, 4, 8, 12], 58, CH['HATC'], I['HatClosed'],
                     [0, 2, 4, 6, 8, 10, 12, 14], [0, 4, 8, 12], 38, 24,
                     [4, 12], 48, bar=bar)
        shape(idx, CH['BASS'], I['Bass'], b, ch['bass'], *SH_BASS_GROOVE, 52)
        pad_chord(idx, b, 0, ch['pad'], 36)
        shape(idx, CH['ARP'], I['Arp'], b, ch['lead_root'], *SH_ARP8, 30)
    # snare roll fill into the drop
    b = bar_base(3)
    for i, r in enumerate([8, 10, 12, 13, 14, 15]):
        note_at(idx, b + r, CH['SNARE'], "C-4", I['Snare'], 34 + i * 5)


def P2_chorusA(idx):
    build_pattern(idx)
    note_at(idx, 0, CH['FX1'], "C-4", I['Crash'], 50)
    for bar in range(4):
        b = bar_base(bar)
        ch = CHORDS[bar]
        drums_common(idx, [0, 4, 8, 12, 14], 62, CH['HATC'], I['HatClosed'],
                     list(range(16)), [0, 4, 8, 12], 42, 22,
                     [4, 12], 54, clap_rows=[4, 12], clap_vol=38,
                     openhat_rows=[14], openhat_vol=30, bar=bar, hat_panflip=True)
        shape(idx, CH['BASS'], I['Bass'], b, ch['bass'], *SH_BASS_BUSY, 56)
        pad_chord(idx, b, 0, ch['pad'], 42)
        shape(idx, CH['ARP'], I['Arp'], b, ch['lead_root'], *SH_ARP8_AIR, 20)
        shape(idx, CH['LEAD'], I['Lead'], b, ch['lead_root'], *SH_ARP8, 58)
        echo_pos = [p + 1 for p in SH_ARP8[0]]
        shape(idx, CH['LEAD2'], I['Lead2'], b, ch['lead_root'], echo_pos, SH_ARP8[1], 24)


def P3_chorusB(idx):
    build_pattern(idx)
    note_at(idx, 0, CH['FX1'], "C-4", I['Crash'], 40)
    for bar in range(4):
        b = bar_base(bar)
        ch = CHORDS[bar]
        drums_common(idx, [0, 4, 8, 12, 14], 62, CH['HATC'], I['HatClosed'],
                     list(range(16)), [0, 4, 8, 12], 42, 22,
                     [4, 12], 54, clap_rows=[4, 12], clap_vol=38,
                     openhat_rows=[14], openhat_vol=30, bar=bar, hat_panflip=True)
        shape(idx, CH['BASS'], I['Bass'], b, ch['bass'], *SH_BASS_BUSY, 56)
        pad_chord(idx, b, 0, ch['pad'], 44)
        shape(idx, CH['LEAD'], I['Lead'], b, ch['lead_root'], *SH_ANSWER, 60)
        harmony_root = T.degree_step(ch['lead_root'], -2)
        shape(idx, CH['LEAD2'], I['Lead2'], b, harmony_root, *SH_ANSWER, 42)
        echo_pos = [p + 2 for p in SH_ANSWER[0] if p + 2 <= 15]
        echo_steps = SH_ANSWER[1][:len(echo_pos)]
        shape(idx, CH['FX2'], I['Lead2'], b, ch['lead_root'], echo_pos, echo_steps, 22)
    # descending tom fill -> breakdown
    b = bar_base(3)
    for r, nm in zip([8, 10, 12, 14], ["C-4", "A-3", "G-3", "E-3"]):
        note_at(idx, b + r, CH['FX1'], nm, I['Tom'], 46)


def P4_breakdown(idx):
    build_pattern(idx)
    for bar in range(4):
        b = bar_base(bar)
        ch = CHORDS[bar]
        hits(idx, CH['KICK'], I['Kick'], [b + 0], 34)
        hits_accent(idx, CH['HATC'], I['HatClosed'], [b + r for r in [0, 4, 8, 12]],
                    [b + 0], 22, 16)
        pad_chord(idx, b, 0, ch['pad'], 46)
        shape(idx, CH['ARP'], I['Arp'], b, ch['lead_root'], *SH_ARP8_AIR, 26)
        note_at(idx, b + 0, CH['LEAD'], ch['lead_root'], I['Lead'], 30)
        if bar == 0:
            hits(idx, CH['BASS'], I['Bass'], [b], 24, note=ch['bass'])


def P5_build(idx):
    build_pattern(idx)
    note_at(idx, 0, CH['FX2'], "C-4", I['Riser'], 60)
    for bar in range(4):
        b = bar_base(bar)
        ch = CHORDS[bar]
        pad_chord(idx, b, 0, ch['pad'], 44 + bar * 2)
        arp_sh = SH_ARP8 if bar < 2 else SH_ARP16
        arp_vol = 22 + bar * 6
        shape(idx, CH['ARP'], I['Arp'], b, ch['lead_root'], *arp_sh, arp_vol)
        if bar >= 1:
            hits(idx, CH['KICK'], I['Kick'], [b + r for r in [0, 4, 8, 12]], 50 + bar * 4)
        if bar >= 2:
            hits(idx, CH['SNARE'], I['Snare'], [b + r for r in [4, 12]], 46)
            hits(idx, CH['CLAP'], I['Clap'], [b + r for r in [4, 12]], 36)
        hat_rows = [0, 2, 4, 6, 8, 10, 12, 14] if bar < 3 else list(range(16))
        hits_accent(idx, CH['HATC'], I['HatClosed'], [b + r for r in hat_rows],
                    [b + 0, b + 4, b + 8, b + 12], 30 + bar * 4, 18 + bar * 2)
    b = bar_base(3)
    for i, r in enumerate([8, 10, 12, 13, 14, 15]):
        note_at(idx, b + r, CH['SNARE'], "C-4", I['Snare'], 36 + i * 5)
    shape(idx, CH['BASS'], I['Bass'], b, CHORDS[3]['bass'], [8, 10, 12, 13, 14, 15],
          [0, 0, 0, 2, 4, 7], 50)
    # pitch-rising riser stab on the last beat, screaming into the drop
    note_at(idx, b + 12, CH['LEAD2'], "A-3", I['Lead2'], 56)
    for r in range(13, 16):
        call("pattern_set_cell", pattern=idx, row=b + r, channel=CH['LEAD2'],
             effect=1, effect_param=24)


SH_FLOURISH = (list(range(0, 16, 2)), [0, 1, 2, 3, 4, 5, 6, 7])


def P6_drop(idx):
    build_pattern(idx)
    note_at(idx, 0, CH['FX1'], "C-4", I['Crash'], 56)
    for bar in range(4):
        b = bar_base(bar)
        ch = CHORDS[bar]
        drums_common(idx, [0, 4, 8, 12, 14], 64, CH['HATC'], I['HatClosed'],
                     list(range(16)), [0, 4, 8, 12], 46, 24,
                     [4, 12], 58, clap_rows=[4, 12], clap_vol=42,
                     openhat_rows=[14], openhat_vol=34, bar=bar, hat_panflip=True)
        shape(idx, CH['BASS'], I['Bass'], b, ch['bass'], *SH_BASS_BUSY, 60)
        pad_chord(idx, b, 0, ch['pad'], 46)
        if bar < 3:
            shape(idx, CH['LEAD'], I['Lead'], b, ch['lead_root'], *SH_ARP8, 64)
            harmony_root = T.degree_step(ch['lead_root'], -2)
            shape(idx, CH['LEAD2'], I['Lead2'], b, harmony_root, *SH_ARP8, 48)
        else:
            # climactic rising flourish for the final bar of the drop
            shape(idx, CH['LEAD'], I['Lead'], b, ch['lead_root'], *SH_FLOURISH, 64)
            shape(idx, CH['LEAD2'], I['Lead2'], b, T.degree_step(ch['lead_root'], -2),
                  *SH_FLOURISH, 46)
        stab_note = T.degree_step(ch['lead_root'], -7)
        hits(idx, CH['FX2'], I['Stab'], [b + 6, b + 14], 34, note=stab_note)


def P7_outro(idx):
    build_pattern(idx)
    for bar in range(4):
        b = bar_base(bar)
        ch = CHORDS[bar]
        fade = bar < 3
        kv = 58 if fade else 50
        drums_common(idx, [0, 4, 8, 12], kv, CH['HATC'], I['HatClosed'],
                     [0, 2, 4, 6, 8, 10, 12, 14], [0, 4, 8, 12], 36, 22,
                     [4, 12] if bar < 3 else [], 48, bar=bar)
        shape(idx, CH['BASS'], I['Bass'], b, ch['bass'], *SH_BASS_GROOVE, 50 if bar < 3 else 40)
        pvol = 36 if bar < 3 else max(16, 36 - 7 * (bar))
        pad_chord(idx, b, 0, ch['pad'], pvol)
        shape(idx, CH['ARP'], I['Arp'], b, ch['lead_root'], *SH_ARP8, 26 if bar < 3 else 16)
        if bar == 3:
            note_at(idx, b + 0, CH['LEAD'], ch['lead_root'], I['Lead'], 40)
    # final-bar turnaround: fill + downlifter cueing the loop back to P0
    b = bar_base(3)
    for i, r in enumerate([8, 10, 11, 12, 13, 14, 15]):
        note_at(idx, b + r, CH['SNARE'], "C-4", I['Snare'], 30 + i * 4)
    note_at(idx, b + 0, CH['FX2'], "C-4", I['Downlifter'], 54)


def P9_verse2(idx):
    build_pattern(idx)
    for bar in range(4):
        b = bar_base(bar)
        ch = CHORDS[bar]
        drums_common(idx, [0, 4, 8, 12], 58, CH['HATC'], I['HatClosed'],
                     [0, 2, 4, 6, 8, 10, 12, 14], [0, 4, 8, 12], 40, 26,
                     [4, 12], 50, clap_rows=[12], clap_vol=30, bar=bar)
        shape(idx, CH['BASS'], I['Bass'], b, ch['bass'], *SH_BASS_GROOVE, 54)
        pad_chord(idx, b, 0, ch['pad'], 38)
        shape(idx, CH['ARP'], I['Arp'], b, ch['lead_root'], *SH_ARP8, 32)
        if bar >= 2:
            note_at(idx, b + 0, CH['LEAD2'], ch['lead_root'], I['Lead2'], 26)
    # snare roll fill into the drop (bigger this time)
    b = bar_base(3)
    for i, r in enumerate([6, 8, 10, 12, 13, 14, 15]):
        note_at(idx, b + r, CH['SNARE'], "C-4", I['Snare'], 30 + i * 5)


def P8_chorusA2(idx):
    build_pattern(idx)
    note_at(idx, 0, CH['FX1'], "C-4", I['Crash'], 46)
    for bar in range(4):
        b = bar_base(bar)
        ch = CHORDS[bar]
        drums_common(idx, [0, 4, 8, 12, 14], 62, CH['HATC'], I['HatClosed'],
                     list(range(16)), [0, 4, 8, 12], 44, 24,
                     [4, 12], 56, clap_rows=[4, 12], clap_vol=40,
                     openhat_rows=[14], openhat_vol=32, bar=bar, hat_panflip=True)
        shape(idx, CH['BASS'], I['Bass'], b, ch['bass'], *SH_BASS_BUSY, 58)
        pad_chord(idx, b, 0, ch['pad'], 44)
        shape(idx, CH['ARP'], I['Arp'], b, ch['lead_root'], *SH_ARP8_AIR, 22)
        shape(idx, CH['LEAD'], I['Lead'], b, ch['lead_root'], *SH_ARP8, 60)
        harmony_root = T.degree_step(ch['lead_root'], -2)
        shape(idx, CH['LEAD2'], I['Lead2'], b, harmony_root, *SH_ARP8, 40)
        stab_note = T.degree_step(ch['lead_root'], -7)
        hits(idx, CH['FX2'], I['Stab'], [b + 6, b + 14], 30, note=stab_note)


def main():
    global I
    I = L.build()

    P0, P1, P2, P3, P4, P5, P6, P7, P8, P9 = range(10)
    P0_intro(P0)
    P1_verse(P1)
    P2_chorusA(P2)
    P3_chorusB(P3)
    P4_breakdown(P4)
    P5_build(P5)
    P6_drop(P6)
    P7_outro(P7)
    P9_verse2(P9)
    P8_chorusA2(P8)

    order = [P0, P1, P2, P3, P9, P8, P3, P4, P5, P6, P7]
    for pos, pat in enumerate(order):
        jcall("order_set", position=pos, pattern=pat)
    jcall("song_set", name="Unlock Sequence", length=len(order), loop_start=0, bpm=150, speed=6)
    print("order:", order, "total patterns authored: 10")


if __name__ == "__main__":
    main()
    print(jcall("module_info"))
