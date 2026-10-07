"Keygen Bounce" - an original FastTracker II (XM) keygen tune
============================================================

  tune.xm            the module  (10 channels, 12 patterns, 150 BPM, speed 6)
  tune_preview.wav   44.1 kHz stereo render of tune.xm (one pass = 76.8 s)
  src/compose.py     builds tune.xm (patterns, orders, instruments, mix)
  src/xmlib.py       small spec-conformant XM writer used by compose.py
  src/gen_samples.py renders every instrument sample with NumPy
  src/dump.py        XM reader / pattern dumper used while checking the tune

Form
----
  order 0-1   intro      pad + arpeggio, then bass/kick/snare build, lead pickup
  order 2-3   main A     Am | F | C | G        full drums, bass, arps, lead
  order 4-5   main B     Dm | F | C | E        new melody, harmonic-minor E
  order 6     breakdown  Am | F | Dm | E       drums out, snare roll back in
  order 7-10  reprise    A and B again with a detuned doubled lead + extras
  order 11    turnaround Am | F | G | E        zap + crash back into order 0

  Restart position is 0, so the tune loops seamlessly from the turnaround
  straight into the intro pad and crash.

Sound
-----
  Every sample is 22050 Hz, 16-bit, one-shot (no loops), generated with NumPy:
    lead / lead2  detuned 25% pulse leads (chorus double)
    arp           short plucky pulse used for 16th-note chord arpeggios
    bass          pulse + sub-sine bass, C-4 reference (sounds 43-82 Hz)
    kick snare clap hat ohat tom crash zap
    pad / pad2    detuned saw pad, root + third voices
  Samples use the standard XM convention relative note +16 / finetune +104 so
  that C-4 plays a 22050 Hz sample at its recorded pitch.

  All note dynamics live in the XM volume column (sample volume is uniform),
  so the balance is preserved no matter how the module is rendered.

Build:  python3 src/gen_samples.py && python3 src/compose.py
