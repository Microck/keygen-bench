SERIAL DREAMS  -  an original keygen / chiptune-trance loop for FastTracker II
=============================================================================
Key/scale : A natural minor        Tempo : 140 BPM (speed 6, 16th-note rows)
Form      : 10 channels, 6 patterns (64 rows = 4 bars each)
Progression (1 bar each, repeats): Am - F - C - G   (i - VI - III - VII)

Arrangement (order), restart/loop point = position 1 (intro plays once):
  0 intro  | 1 GROOVE | 2 themeA | 3 themeA' | 2 | 3 | 4 break | 5 CLIMAX
  | 2 | 3 | 4 break | 5 CLIMAX  --> loops back to position 1 (GROOVE)
The loop turns the V chord (G) at the end of the climax back into the i (Am)
at the groove, so the seam resolves musically; sustained voices are keyed off
on the last row so nothing smears across the restart.

Sound design (all samples synthesised in NumPy, no external audio):
  bass  - decaying saw pluck (one-shot, baked envelope)
  arp   - warm saw/pulse single-cycle, driven by the 0xy arpeggio effect
          (0x37 minor / 0x47 major triads) for the shimmering chord bed
  lead  - 30% band-limited pulse; a dotted-8th echo + diatonic-3rd harmony
  pad   - soft triangle/saw blend
  kick/snare/hats/crash - synthesised drums (pitch-swept kick, noise+tone snare)
Tonal samples are single cycles (FR 33487, len 256 -> C-4 = 130.81 Hz); pitch
comes from the tracker, dynamics from the volume column, width from panning.

Reproduce:
  python3 make_samples.py     # writes /workspace/samples/*.wav
  python3 build.py            # writes /workspace/build_batch.json
  ft2 batch /workspace/build_batch.json   # builds + saves tune.xm + preview
