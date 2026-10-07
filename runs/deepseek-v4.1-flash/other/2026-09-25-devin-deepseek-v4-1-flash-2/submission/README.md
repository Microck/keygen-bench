# Keygen Anthem — an original XM keygen tune

`tune.xm` — FastTracker II module (13 patterns x 64 rows, 12 channels, 15 instruments,
6 ticks/row @ 150 BPM, linear frequency table, restart position 0 -> the song loops
from the end back to pattern 0).

## Structure (each pattern = 4 bars = 6.4 s, total ~82.9 s)

| # | Section | Content |
|---|---------|---------|
| 0 | Intro 1  | swelling pads, bell pings, sparse kick/hat |
| 1 | Intro 2  | + bass, arps, hats |
| 2 | Verse A1 | full drums, bass, 16th arps, square lead melody |
| 3 | Verse A2 | melody variation |
| 4 | Chorus B1| B progression, lead + drive bass |
| 5 | Chorus B2| melody variation, crash |
| 6 | A reprise| harmony line added, busier drums, arps "up" |
| 7 | A reprise| leads swapped, tom fill into the break |
| 8 | Break    | pads + arps + lead only, pings |
| 9 | Build    | snare build, riser with portamento up, tempo lifts to 165 BPM |
| 10| Final A  | back to 150 BPM, full arrangement + harmony, crash |
| 11| Final B  | full arrangement + harmony |
| 12| Outro    | three bars of Am-F-C, then a final Am chord that releases and fades
              out before the loop point, so the restart into pattern 0 is clean |

Harmony (instr 10) is generated from the lead with a consonant-interval search
against the current chord, so no harsh seconds occur.

## Instruments (all sample data synthesised from scratch with NumPy)

1 kick (pitch-drop sine + click) 2 snare (noise + 190 Hz body) 3 closed hat
4 open hat 5 crash 6 riser (looped noise, used with E0x portamento)
7 saw+pulse bass (looped) 8 12.5% pulse arp (looped) 9 25% pulse lead (looped)
10 50% pulse harmony (looped) 11/12/13 soft-saw pads, panned L/C/R (looped,
volume-envelope swell) 14 bell ping 15 tom.

Pitched samples are one 32-sample cycle at 8363 Hz preceded by a 4-sample fade,
with a forward loop over the cycle; they are all 16-bit.

## Scripts

* `sounds.py`  — drum/waveform synthesis
* `xmbuild.py` — minimal XM writer (standard layout, FT2-compatible)
* `build_tune.py` — score + arrangement; writes `tune.xm`

Rebuild with: `python3 build_tune.py` (from this directory).

`tune_preview.wav` is a 44.1 kHz/16-bit render of one full pass
(FT2 `--cli render ... --amp 16`), peak 76% FS, no clipping.
