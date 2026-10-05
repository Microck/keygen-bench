keygen: chromakey  (FastTracker II XM, 10 channels, 155 BPM, speed 6)

An original chip/keygen tune in A minor. All samples are synthesized from
scratch with NumPy (gen_samples.py): bandlimited pulse lead/bass/arp
single-cycle waves, a detuned-saw pad with a seamless 32768-sample loop,
and analog-style drums (kick, snare, claps, hats, crash, wind riser).

Arrangement (order list 0-9, patterns of 64 rows):
  pos0  pat0  intro: pad + arps fade in, wind riser
  pos1  pat1  groove enters: kick/snare/hats, octave bass, chip arps
  pos2  pat2  theme A1  (Am F C G)   <- loop restart position
  pos3  pat3  theme A2 + snare fill
  pos4  pat4  theme B1  (F G Am Am), claps
  pos5  pat5  theme B2  (F G E E), fill
  pos6  pat2  theme A1 reprise
  pos7  pat3  theme A2
  pos8  pat6  breakdown: pad + sparse arps, kick re-enters
  pos9  pat7  build: snare roll, wind, rising E-major lead -> loops to pos2

The song restart is set to position 2, so the loop runs A1-A2-B1-B2-A1-A2-
breakdown-build and resolves (E major dominant) cleanly back into the
A-minor theme. Echo channel and key-offs are placed so nothing hangs over
the seam. Rendered peak 0.90, no clipping.

Channels: kick, snare, hats, bass, lead, lead-echo, arpL, arpR, pad, fx.
Chip arps use effect 0xy (4/7 and 3/7) on looped single-cycle waves.
