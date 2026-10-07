# Keygen Tune — "Access Granted"

An original 8-channel FastTracker II keygen module in A minor.

## Specs
- Format: XM, 8 channels, 16-bit samples
- Tempo: 150 BPM, speed 6 (16th-note grid), 64-row patterns (4 bars each)
- Length: 10 patterns. Intro (P0–P1) plays once; loop body P2–P9 repeats.
- Loop: song loop_start = 2 (pattern order pos 2). P9 (turnaround, ends on
  E = V of Am) resolves seamlessly back into P2 (verse on Am). Measured loop
  seam discontinuity ~59/32767 (0.3%) — inaudible.

## Harmony (A minor)
- Verses / reprise: Am – F – C – G
- Chorus A: C – G – Am – F     Chorus B: C – G – Am – G
- Bridge: Dm – F – C – E       Bridge build: Dm – F – E – E
- Turnaround: F – G – Am – E (V→i into the loop)
All arp notes are chord tones; all lead/bell notes diatonic (G# only over E as
the harmonic-minor leading tone).

## Arrangement (6.4 s per pattern)
P0 intro (bass+arp+pad) · P1 build (drums enter) · P2 verseA · P3 verseB ·
P4 chorusA (+bell, stabs) · P5 chorusB · P6 bridge (breakdown) ·
P7 bridge-build (fill) · P8 reprise (+bell) · P9 turnaround (fill).

## Channels
0 kick · 1 snare · 2 hats(closed/open) · 3 bass · 4 arp(pluck) ·
5 pad/stab · 6 lead · 7 bell

## Instruments (all synthesized in NumPy, gen_samples.py)
1 bass (DC-free saw+sub) · 2 lead (28% pulse) · 3 pad (warm saw) ·
4 stab (square-ish, chorus chords) · 5 pluck (bright arp, per-harmonic decay) ·
6 kick (pitch-drop sine+click) · 7 snare (tone+noise) ·
8 hat / 9 open-hat (4–11 kHz band-passed noise) · 10 bell (FM).

## Sound-design notes / pitfalls solved
- FT2 uses the classic 8363 Hz C-4 reference. Single-cycle length 256 with
  relative_note = 36, finetune = 2 → concert pitch (verified across A1–A5).
- sample_create_from_pcm stores 8-bit by default (adds DC + harshness). Setting
  the 16-bit flag (0x10) — flags 17 for looped, 16 for one-shot — preserves full
  16-bit quality and removed a large DC offset that was wasting ~3 dB headroom.
- All looped single-cycle waveforms are built from integer harmonics and
  zero-meaned (dc_remove) so they loop click-free.
- Lead uses vibrato (effect 4) on held notes for expression (no envelopes in
  this build; all shaping is in the sample data).

## Mix
Peak ≈ -4 dBFS, no clipping, DC ≈ 0, crest ≈ 12 dB. Four-on-the-floor kick,
bass-forward "smiley" EQ, tasteful stereo (arp/pad left, hats/bell/stab right;
bass, kick, snare, lead centered — fully mono-compatible).

## Rebuild
    python3 gen_samples.py         # -> create_samples.json, meta_samples.json
    python3 compose.py             # -> song_batch.json
    # then: module_new(8ch) ; batch create_samples ; batch meta_samples ;
    #       batch song_batch ; song_set(length=10, loop_start=2) ; save xm
