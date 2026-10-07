# Neon Checksum — keygen tune (FastTracker II XM)

Original composition in classic keygen/chiptune style. Everything is synthesized
from scratch with NumPy (gen_samples.py) and sequenced into a real 12-channel
XM module (compose.py emits ft2 batch calls).

- Key: A minor · Tempo: 150 BPM, speed 6 (rows = 16ths) · 9 patterns x 64 rows
- Form: intro | groove | verse x2 | bell breakdown | build | chorus x2 | cooldown
- Loop: song restart position = 1 (intro plays once; 8-pattern loop ≈ 51.2 s)
  Cooldown ends on G/E-pedal + chromatic bass pickup (G#) resolving to Am at the
  loop point, where a crash masks the seam — loops cleanly.
- Instruments (16): punch kick, snare, clap, hats, crash (shaped noise), pluck
  bass (band-limited saw/square hybrid, baked decay, looped sustain), 25% pulse
  lead, 50% square chord-arp (classic 0xy arpeggio effect), 12.5% pulse sparkle,
  FM bell, wide detuned-saw chord pads (minor & major chord baked into looped
  samples, L/R detuned pair), noise riser.
- Tricks: volume-column mixing with master/channel gain map, ping-pong echo
  channel (3-row delay, 8xx panning), chromatic leading-tone basslines,
  vibrato on held lead notes, snare-roll builds.

Rebuild: python3 gen_samples.py && python3 compose.py && ft2 batch build/song_batch.json
