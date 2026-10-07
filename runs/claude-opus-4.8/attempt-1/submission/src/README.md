# midnight keygen

An original keygen-style chiptune, composed in FastTracker II (XM) with all
instrument material synthesized from scratch in Python/NumPy.

* Key / mode : A minor
* Tempo      : 140 BPM (speed 6, 16 rows/bar, 64-row patterns = 4 bars)
* Channels   : 12
* Length     : 68.5 s of unique material; loops seamlessly from the end of the
               BUILD pattern back to order position 2 (the main theme), so the
               intro plays once and the groove loops forever.

## Form (song order -> pattern)
0 P0  intro (pad + sub, arp builds in)         } play once
1 P1  intro (adds bassline, hats, light kick)  }
2 P2  MAIN theme A        (Am F C G)   <- loop restart point
3 P3  MAIN theme A'
4 P4  B-section           (Dm F C E, dramatic V)
5 P5  B-section answer    (Am F C G)
6 P8  CLIMAX (soaring chorus lead + octave harmony, fuller drums, crash)
7 P9  CLIMAX answer
8 P6  BREAKDOWN (drums drop, pad/arp + sparse lead)
9 P7  BUILD (snare roll riser) --> back to P2

Progressions are i-VI-III-VII in A minor with a iv-VI-III-V turn in the
B-section; six distinct lead phrases keep the loop fresh.

## Sound design (see gen_samples.py)
* Melodic/harmonic voices are single 256-sample band-limited cycles
  (pulse 25% lead, pulse 16% harmony, 50% square arps, saw bass, warm
  saw+sine pad, sine sub), looped and tuned with relative_note=36.
  Arps are plucked with per-row volume-slide (Axy); chords use a two-voice
  root+fifth pad detuned/panned L-R for width.
* Drums are one-shots: pitch-dropping sine kick with click, FFT-shaped
  noise snare/hats (spectrally tilted so they are bright but not fizzy),
  clap and metallic crash. Tuned with relative_note=29.

## Rebuild
1. `python3 gen_samples.py`            # writes samples/*.wav
2. load the samples per build_instr.py (relative_note / loop / pan / finetune)
3. run composer.py to emit the pattern/order data, then save as XM.

The authoritative samples are included in ./samples/ and are embedded in
tune.xm, which is fully self-contained.
