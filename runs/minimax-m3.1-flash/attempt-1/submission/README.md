# NEON KEYGEN

An original keygen / chiptune tracker tune, built as a real 18-channel XM module
with the FastTracker II bridge in this workspace.

* `tune.xm`      – the module (the deliverable)
* `preview.wav`  – a rendered preview of the whole arrangement (51.2 s)
* `scripts/`     – the source that generated the samples and the module

## The music

Key of A minor, 150 BPM, 4/4, 16 rows per bar, 4 bars per pattern, 8 patterns
(32 bars) of music.

| pattern | bars | section | what happens |
|---------|------|---------|--------------|
| 0 INTRO  | 1-4  | Am F C G | sparse 16th-note arpeggio, pad, bass enters in bar 3, bell counter-line, riser into the drop |
| 1 A      | 5-8  | Am F C G | full groove: arps, bass, drums, lead hook, plucks |
| 2 A2     | 9-12 | Am F C E | as A plus off-beat chord stabs, busier lead and a drum fill |
| 3 B      | 13-16| Dm Am F G | contrasting phrase with the FM bell on top, fill at the end |
| 4 BREAK  | 17-20| Am F C G | drums and bass drop out, pad + stabs + bell, re-arms the tension |
| 5 BUILD  | 21-24| Am F C G | drums back in, 16th-note snare roll and riser into the climax |
| 6 CLIMAX | 25-28| Am F C E | everything at once: lead on top, bell, stabs, full drums |
| 7 OUTRO  | 29-32| Am F C G | the hook returns, drums thin out, pad tail carries over the loop point |

Harmony: i - VI - III - VII (Am F C G) with a V (E major) lift in the second
and sixth patterns and a Dm turn in the B section. The lead hook is built from
A minor pentatonic / aeolian material with a 6th and a 7th colour note.

## The instruments

Every voice is a single hand-generated sample (numpy, 8363 Hz, band limited
additive synthesis / noise models - see `scripts/synth.py`):

| channel | instrument | sound |
|---------|-----------|-------|
| 0 | ARPA  | 50 % pulse, upper 16th-note arpeggio |
| 1 | ARPB  | 12.5 % pulse, lower counter arpeggio |
| 2 | LEAD  | 25 % pulse, the melody |
| 3 | BASS  | rounded saw bass |
| 4 | SUB   | sine sub bass |
| 5 | KICK  | pitch-swept sine kick |
| 6 | SNARE | noise + 185 Hz body |
| 7 | HAT   | high-passed noise |
| 8 | OHAT  | open hat |
| 9-11 | STAB1-3 | one-shot percussive chord stabs (root / third / fifth) |
| 12 | BELL  | 2-operator FM bell |
| 13 | PLUCK | filtered noise + tone pluck |
| 14 | FX    | crash |
| 15 | PAD   | soft detuned saw pad |
| 16 | RISER | noise riser |
| 17 | RIM   | rim shot (build-up roll) |

Dynamics are done with the `Cxx` (set volume) effect on every note cell and
with the instrument volumes; the pad, the lead and the bell are released with
key-off cells at the end of a pattern, since this tracker build has no
instrument envelopes. The stabs are one-shot percussive tones, so they decay
by themselves.

## Rebuilding

```
python3 scripts/synth.py     # writes the sample wavs
python3 scripts/build.py     # builds the module through the ft2 bridge
```

`scripts/score.py` holds the composition (chords, bass line, arpeggio figures,
melodies, drum maps) and `scripts/build.py` turns it into pattern cells.

## Notes on this tracker build

* Tempo: rows play at `2.5 * speed / bpm` seconds. The module stores
  speed 6 / 150 BPM, i.e. 0.1 s per row = 4 rows per beat = 150 BPM.
* Tuning: this build sounds a looped sample one octave above its natural
  pitch at clone note 61 (and a one-shot sample at its natural pitch on clone
  note 73), so `scripts/build.py` maps every midi note accordingly - the
  script contains the measured mapping, the score itself is written in plain
  midi note numbers.
* This build has no instrument envelopes, so all shaping is baked into the
  samples; the `Cxx` effect (set volume) is used for the dynamic levels and
  key-off cells release the pad and the lead at the end of a pattern.
* The order list is `0 1 2 3 4 5 6 7` with the restart position at 0, so the
  piece loops straight back into the intro; the tail of the outro (no drums,
  thinning arpeggio, releasing pad) was written to make that seam clean.
