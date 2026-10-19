=====================================================================
 NEONKEYGEN - an original "keygen style" chiptune for FastTracker II
=====================================================================

FILES
  tune.xm        the module (FastTracker II .xm).  Load and press play -
                 it loops forever from pattern 0 back to pattern 0.
  preview.wav    rendered preview, one full loop (51.2 s).
  gen_samples.py synthesises every instrument from scratch (NumPy).
  compose.py     writes every pattern cell (notes/volumes/effects).
  build.sh       loads samples+instruments+patterns into FT2, renders,
                 saves tune.xm.
  analyze.py     render statistics used while mixing the tune.
  samples/       the 15 instrument samples exactly as used by the module.

THE TUNE
  Key      D minor (Bb major colour, C# in the A bar -> harmonic minor)
  Tempo    150 BPM, speed 6 (1 row = 1/16 note), 32 rows = 1 bar
  Length   32 bars = 16 patterns x 32 rows = 51.2 s, loops seamlessly
  Harmony  Dm | Bb | F | C   with  Gm | A  for the two build bars and
           Bb | F | C | Dm  for the break.

  bars  0- 3  intro        pad + 16th arpeggios + bass + drums,
                            lead joins at bar 2 with the hook's tail
  bars  4-11  theme A      full hook, 16th hats, offbeat chord stabs,
                            second phrase with a rising run
  bars 12-15  build        16th-note bass, two-octave arpeggio sweep,
                            fast ascending lead, C# leading into A7
  bars 16-19  break        half-time drums, soft pad, the hook restated
                            an octave down as long notes with vibrato
                            (effect 4) - darker and fully sustained
  bars 20-27  reprise       hook again + counter melody (LEAD2),
                            variation of the hook, tom/snare fills
  bars 28-31  climax       hook restated, extra 16th counter figure,
                            then a descending 16th turnaround run
  -> bar 31 is a C major bar, bar 0 is D minor: the dominant resolves
     straight back into the loop, so there is no seam.

INSTRUMENTS (15)
   1 LEAD      50% pulse, bright, long sustain   - melody
   2 LEAD2     25% pulse, thin                   - counter melody
   3 ARP       12.5% pulse blip                  - 16th arpeggios
   4 BASS      low-passed 50% pulse, punchy      - driving bass
   5 PAD       soft filtered saw, slow attack    - intro / break
   6 KICK      sine pitch-drop + click
   7 SNARE     band-passed noise + 196 Hz body
   8 HAT       metallic squares + high-passed noise
   9 OPENHAT   long noise decay
  10 TOM       pitch-dropping sine (fills)
  11 CRASH     long bright noise
  12 CHORD Dm  baked triad stabs - one instrument per chord, all
  13 CHORD Bb  played on a single channel (chord changes every bar)
  14 CHORD F
  15 CHORD C

  Every sample was synthesised and envelope-shaped in the PCM itself
  (this FT2 build has no usable envelopes), baked at 32 kHz and
  pre-tuned so that FT2 note 60 sounds as middle C (261.63 Hz -
  verified in the render to within 0.01 cents).
  Stereo placement: arp/hat/openhat left, pad/chords/crash right,
  lead/lead2/bass/kick/snare centred.

  All the music lives in the patterns: 1650 written cells across
  16 patterns and 12 channels (drum pattern per section, note-by-note
  bass and melody, 16th arpeggio figures, volume levels, vibrato).

REPRODUCING
  python3 gen_samples.py
  python3 compose.py
  bash build.sh
  ft2 call module_render '{"path":"preview.wav","rate":44100}'
  ft2 call module_save   '{"path":"tune.xm","format":"xm"}'
