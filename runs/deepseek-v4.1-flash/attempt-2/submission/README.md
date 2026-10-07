# "Keygen Loop" — original keygen tune (FastTracker II / XM)

**File:** `tune.xm` (8 channels, 11 patterns/orders, 140 BPM, speed 6, ~75 s)
**Loop:** restart position = order **1** (order 0 is a 4-bar intro that plays once).
The outro pattern (order 10) ends on an E7 bar that resolves straight into the Am
downbeat of order 1, so the module loops seamlessly.

## Structure (each pattern = 4 bars, 16 rows/bar)
| order | pattern | content |
|---|---|---|
| 0 | intro | drums build, bass + stab arp, rising lead scale into the theme |
| 1-2 | A1 / A2 | main theme (Am F C G / Am F Dm E7) |
| 3-4 | A3 / A4 | theme repeated with harmony voice (diatonic 3rd below), fuller drums |
| 5 | break | drums drop out, pad + slow lead + sparkle arps, rebuild in bar 3-4 |
| 6-7 | B1 / B2 | second theme (Dm Bb F C / Dm Bb E7 E7); bar 4 of B2 is a drum break |
| 8-9 | A5 / A6 | climax: 16th "gallop" bass, four-on-the-floor, high sparkle arp |
| 10 | outro | Am F Dm E7 turnaround with snare roll back to order 1 |

## Sounds (all synthesized from scratch with NumPy, 16-bit, no external samples)
| # | name | description | root / rel-note |
|---|---|---|---|
| 1 | Bass | pulse + sub, pitch drop attack, ~0.5 s pluck | A-1, rel +39 |
| 2 | Lead | PWM pulse (additive, band-limited) + detuned layers, vibrato via effect | A-4, rel +3 |
| 3 | Arp | narrow 12.5% pulse, fast decay chip pluck | C-5, rel 0 |
| 4 | Pad | 5 detuned saws + sub, slow swell | C-4, rel +12 |
| 5 | Kick | sine sweep 160->45 Hz + noise click | rel +12 |
| 6 | Snare | band-passed noise + 190/330 Hz body | rel +24 (4x rate) |
| 7 | Hat | high-passed noise, 11 ms decay | rel +24 |
| 8 | OpenHat | high-passed noise, 85 ms decay | rel +24 |
| 9 | Crash | high-passed noise + metallic partials | rel +24 |
| 10 | Pluck | short-note lead variant (fast decay) | A-4, rel +3 |

Volume is shaped in the sample data itself (no envelopes in this FT2 build);
pattern volume column + vibrato (4x85) effects are used for expression.

## Rendering notes
- The module peaks at ~0.90 FS with the tool's default render settings (amp 16) at
  22050/32000/44100/48000 Hz — no clipping.
- `preview.wav` is a 44.1 kHz render of one pass (intro + loop body).
- `src/` holds the Python generators (sample synthesis + pattern/score generation).
