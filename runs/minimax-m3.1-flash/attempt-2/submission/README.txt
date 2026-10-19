KEYGEN CODEX  -  an original chiptune / keygen tune for FastTracker II
===================================================================

tune.xm            the module (the actual submission)
tune_preview.wav   one pass of the song order (32.0 s), rendered from tune.xm
tune_loop2x.wav    the same audio twice, i.e. exactly how it loops
src/               the scripts that wrote the music (numpy + the FT2 tool API)
samples/           the raw synthesised sample material (also embedded in the XM)

Music
-----
key        A minor, progression i - VI - III - VII  (Am | F | C | G)
tempo      150 BPM, one pattern row = one 16th note (64 rows = 4 bars)
length     5 patterns x 64 rows = 32 s; the order loops back to pattern 0
           (the last bar is a G major fill, the loop resolves back into Am)

arrangement
  0 intro    sustained pad chords + 16th note arpeggio, a sparse lead motif,
             hats and bass creep in, crash on the last bar -> drop
  1 groove A four on the floor kick, snare on 2 and 4, offbeat open hat,
             8th note bass, 16th arpeggio, lead phrase 1, chord stabs
  2 groove B 16th hats, busier bass, ghost snares, lead phrase 2 (higher)
  3 bridge   breakdown: pad, arp and bass only, drums return in bar 3,
             16th hat + snare build with a crash in bar 4
  4 finale   full energy, 16th hats, crash on every bar, chord stabs on the
             half bar, lead phrase 3 up top, 16th bass run and snare roll
             into the loop

voices (every sample was synthesised from scratch with numpy - no samples
were taken from anywhere, the sound is shaped in the sample data itself)
  kick / snare / closed hat / open hat / crash   percussion, tuned so that
                                                  the samples keep their level
  bass                                           filtered saw bass
  arp                                            25% pulse, 16th arpeggios
  lead                                           50% pulse melody with vibrato
  stab x4 (Am F C G)                             short chord stabs
  pad  x4 (Am F C G)                             one bar sustained chords
