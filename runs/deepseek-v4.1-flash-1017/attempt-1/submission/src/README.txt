Keygen Runner  --  FastTracker II module (XM, 24 channels, 10 patterns)

Build:   python3.build order is song9.py (imports gen3.py -> xmlib.py + sounds3.py)
         via exec(); writes candidate.xm.
Final:   /workspace/submission/tune.xm

Structure (64 rows per pattern, 4 bars, speed 6, BPM 164, A natural minor):
  P0  intro        Am  F  G  E   pad + chip arp + keygen chime-bell hook
  P1  intro build  Am  F  G  E   + bass, hats, snare roll
  P2  verse 1      Am  F  C  G
  P3  verse 2      Am  F  C  G
  P4  chorus 1     F   C  G  Am
  P5  chorus 2     F   C  G  Am
  P6  bridge       Dm  Dm E  E   (drums drop, arp doubles)
  P7  verse 3      Bm  G  D  A   (+2 semitone lift)
  P8  final chorus G   D  A  Bm   (+2 semitone lift)
  P9  outro        G   A  Bm E   (E = dominant, resolves back to Am)

Loop: restart position = 2, so the intro plays once and the tune cycles
      verse -> chorus -> bridge -> verse -> chorus -> outro -> verse.
      P9 ends on E major which resolves naturally into P2's A minor.

All sounds are original, synthesized with NumPy:
  - looped single-cycle band-limited pulses/saws/triangles (relative note 24)
    for lead, harmony, arps, bass, pads, organ, bell
  - one-shot percussion (kick, snare, clap, hats, crash, riser, shaker, tick)
Instrument volume envelopes and fade-out (key-off) shape notes;
no sample loops rely on external data.
