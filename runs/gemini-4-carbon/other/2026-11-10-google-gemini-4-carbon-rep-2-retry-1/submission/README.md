# Cybernetic Fugue — Original FastTracker II Keygen Module (`tune.xm`)

- **Format:** FastTracker II Extended Module (`.xm` v1.04, linear frequency table)
- **Channels:** 12
- **Tempo / Speed:** 145 BPM, Speed 6 (58.0 Hz chip-arpeggio tick rate, 64 rows/pattern)
- **Length & Loop:** 20 patterns (80 bars, 2m 12.35s one-shot), seamless restart at `loop_start = 2` (Position 02, Bar 9 Main Hook Drop)
- **Key & Harmony:** F# Minor / A Major / F# Harmonic Minor (with secondary dominants and neo-baroque counterpoint)

## 17 Original NumPy-Synthesized Instruments
All samples are synthesized from scratch in `/workspace/submission/src/synth.py` at `SR = 33452 Hz` (`relative_note = +24, finetune = +4`, exact `128`-sample C-4 cycle) with timbral envelopes, filter sweeps, FM index curves, periodic 64/128-cycle PWM & ensemble modulation, and zero-DC click-free loops shaped directly in 16-bit PCM:
1. `01:Kick-Cyber909` — F#1-tuned punchy keygen kick
2. `02:Snare-KeySnap` — Dual-mode punchy snare with crisp wire snap
3. `03:Clap-Tight909` — Multi-burst handclap
4. `04:Rim-DigiTick` — Crisp digital tracker rimshot
5. `05:HatC-CrispXOR` — 6-oscillator metallic closed hi-hat
6. `06:HatO-Sizzle` — Open hi-hat (choked naturally by `HatC` on Ch 2)
7. `07:Crash-StarBst` — Shimmering stereo crash cymbal
8. `08:Tom-Electro` — Pitched electronic synth tom for stereo fills
9. `09:Bass-RazorFM` — YM2612-inspired 2-op FM + saw-pulse keygen bass
10. `10:Bass-AcidSync` — Resonant SVF sweep acid bass
11. `11:Lead-HeroPWM` — Periodic 64-cycle PWM + chorus hero lead
12. `12:Lead-SyncShrd` — Hard-sync formant harmony & solo lead
13. `13:Chip-Pulse25` — Bandlimited pulse wave for 58Hz `0xy` chip chords & sweeps
14. `14:Bell-CrystlDX` — FM glass harpsichord-bell pluck
15. `15:Pad-LushEnsmb` — 128-cycle 5-voice periodic supersaw/PWM ensemble pad
16. `16:Stab-PolyBrss` — Phase-dispersed resonant synth-brass chord stab
17. `17:FX-CyberRiser` — 1-bar resonant filter sweep + harmonic shimmer riser

## Arrangement & Tracker Structure
- **Pos 00–01 (Bars 1–8):** *Cracktro Boot Sequence* — Harpsichord-bell arpeggios, warm ensemble pad, stereo ping-pong hook tease, twin-lead baroque fanfare, and Bar-8 riser/tom build.
- **Pos 02–05 (Bars 9–24, `loop_start = 2`):** *Section A: Neon Cipher* — Driving keygen hook with dotted-16th stereo tracker echo (`Pos 02–03`), expanding into harmonized twin leads in 3rds/6ths (`Pos 04–05`).
- **Pos 06–09 (Bars 25–40):** *Section B: Skyline Overdrive* — Uplifting chorus (`Dmaj7 - E - C#m7 - F#m7/F#7 - Bm7 - E7 - Amaj7`) with propulsive 16th arcade bass, contrapuntal lead dialogue, and 2-octave sweeping chip arpeggios.
- **Pos 10–11 (Bars 41–48):** *Section C1: Ring0 Sanctuary* — Intimate dynamic breakdown featuring a 2-voice neo-baroque canon (`Bell` + `SyncShred`) awakening into a squelchy 16th `AcidSync` pulse.
- **Pos 12–13 (Bars 49–56):** *Section C2: Virtuoso Shred Duel* — Wide Left/Right neo-classical 16th-note trading solos locking into synchronized parallel 3rds and an explosive riser build.
- **Pos 14–17 (Bars 57–72):** *Section D: Grand Climax Reprise* — Main hook + high descant counter-melody + climax chorus finale peaking on `C#6`.
- **Pos 18–19 (Bars 73–80):** *Coda & Seamless Loop Turnaround* — Syncopated stab/lead riff and dominant `C#7 -> C#7b9` turnaround resolving cleanly back into `Pos 02` (`loop_start = 2`).
