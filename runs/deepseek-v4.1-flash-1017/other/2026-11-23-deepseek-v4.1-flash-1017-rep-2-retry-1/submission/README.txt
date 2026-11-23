KEYGEN.EXE  --  original chiptune keygen theme
=============================================

tune.xm          FastTracker II module (10 channels, 14 instruments, 9 patterns)
preview_mono22k.wav   preview render (mono, 22.05 kHz)
src/             Python source that generates the module and all sample data

Music
-----
150 BPM, speed 6, A natural minor, 4-bar phrases.

Order list and form:
  P0  intro    -- arps + pad, soft kick/hats, snare roll and tom fill
  P1  A1       -- main hook, full band
  P2  A2       -- hook variation, pluck answer, snare build
  P3  B1       -- lift: F-G-E-Am, harmonised lead, driving bass, 16th hats
  P4  B2       -- climax, octave arps, crash accents
  P5  break    -- Dm-Am-F-E, half-time, rebuild in the last bar
  P6  A3       -- hook returns with harmony, final phrase lifted an octave
  P7  A4       -- variation with drum fill
  P8  outro    -- Am-F-G-E turnaround

Restart position = order 1, so P0 (the intro) plays once and the module then
loops P1..P8 forever.  P8 ends on E major which resolves to the Am downbeat at
the start of P1, so the loop point is seamless both harmonically and
rhythmically (the last bar is a drum fill that lands on the P1 downbeat).

Sound design
------------
All instruments are short one-cycle/one-shot samples generated with NumPy.
Tonal voices are 4-cycle / 3-cycle wavetables so the timbre shimmers while it
loops; percussion is synthesized (pitch-swept kick with click layers, noise +
tone snare, metallic tone-cluster hats, inharmonic crash, pitched toms).
Voices are RMS-matched so the pattern volume column is a meaningful mix.

Generating
----------
  python3 src/compose.py out.xm
(src/songdata.py holds the composition, src/instruments.py the synthesis,
src/xm2.py the XM writer.)
