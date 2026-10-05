Circuit Breaker - original keygen tune (FastTracker II XM module)
================================================================
File      : tune.xm
Preview   : preview.wav (44.1 kHz 16-bit stereo render of tune.xm)

Style     : keygen / demoscene chiptune-techno hybrid
Tempo     : 150 BPM, speed 6 (one row = 1/16 note, 64 rows = 4 bars)
Key       : A minor with harmonic-minor dominant (E major) cadences
Length    : 18 patterns = 72 bars = 1:55, loops cleanly at order 0

Structure :
  P0  intro      : arp + hats + bell motif        (Am F C G)
  P1  intro 2    : + bass + kick                  (Am F C G)
  P2  theme A    : lead melody hook               (Am F C G)
  P3  theme A'   : hook answer / turnaround       (Am F E E)
  P4/P5          : theme A with counter-line
  P6  breakdown  : pads + arp + bells, no drums   (F C G Am)
  P7  build      : bass + snare roll crescendo    (F C E E)
  P8-P11 chorus  : theme B melody, 2nd time with harmony (F G Am Am / F G E Am)
  P12/P13 solo   : continuous 16th note chip runs (Am F C G / Am F E E)
  P14/P15        : theme A reprise, full band
  P16/P17 outro  : thinning out, ends on E -> loops back to Am at P0

Instruments (14, all original, synthesised with NumPy):
  1 kick (pitch-swept sine + click)      8 saw lead / counter voice
  2 snare (noise + tonal body)           9 arp blip (square)
  3 clap (multi-burst noise)            10/11 minor / major chord stab
  4/5 closed / open hi-hat              12/13 minor / major pad
  6 bass (additive saw + sub)           14 bell / pluck (inharmonic FM-ish)
  7 lead (25% pulse + detune)

Channels: 1 lead | 2 counter | 3 arp | 4 chords/pad | 5 bass | 6 kick | 7 snare | 8 hats

Sample design notes:
  Samples are 8-bit, delta encoded, and written so that each sample frame is
  duplicated in the data block (length counts those duplicated frames), which
  both this toolchain and any standard XM player reproduce at the right pitch
  and duration. relative_note is set so that C-4 sounds as synthesised.

Source scripts:
  make_samples.py  - synthesises every instrument sample and emits the load calls
  compose.py       - writes the whole arrangement (patterns, order, mix)
  analyze.py       - level / spectrum report of a render
  qc.py            - melody pitch verification against the intended notes
