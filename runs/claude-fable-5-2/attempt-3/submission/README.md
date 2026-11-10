# Checksum Sunrise

An original keygen-style chiptune for FastTracker II (`tune.xm`). Music only: the package contains
audio data and the scripts that generated it - no key-generation, licensing or protection-related code.

| | |
|---|---|
| Format | XM 1.04, 16 channels, 24 instruments, 28 patterns (64 rows), linear frequency table |
| Tempo / key | speed 3, 140 BPM (16th note = 2 rows), D minor |
| Length | 96 s per pass (13.7 s intro + 82.2 s loop body) |
| Loop | song end -> restart position = order 04 (main theme); the intro plays once |

## Files
- `tune.xm` - the final, editable module (written by the FT2 clone's own `module_save`).
- `tune_preview.wav` - one pass rendered with the FT2 clone at its defaults (44.1 kHz, 16 bit, amp 16).
- `verification.json`, `looptest.txt` - measured facts about the module and the render (see below).
- `src/` - build + verification scripts, `SHA256SUMS.txt` - checksums of every file in the package.

## Arrangement (order list)
| Orders | Bars | Section | What happens |
|---|---|---|---|
| 00-03 | 1-8 | Intro (once) | 0xy chord arpeggios + pluck sequencer with ping-pong echo + pad; kick, tresillo bass, triangle "teaser" melody, fill + noise riser |
| 04-07 | 9-16 | A1 | main theme on the PWM pulse lead (dotted-8th echo), Dm-Bb-F-C / Dm-Bb-C-A |
| 08-11 | 17-24 | A2 | ornamented theme, square 2nd voice answers and then harmonises, sequencer line, ghost snares |
| 12-15 | 25-32 | B1 | chorus Bb-C-Am-Dm / Gm-C-Asus4-A: four-on-the-floor, detuned lead double, harmony in 3rds/6ths, pumping pad |
| 16-19 | 33-40 | C | breakdown: soft triangle melody, sequencer, long pads; kick/arps/snare roll/riser build back up |
| 20-23 | 41-48 | D | 8-bar solo on the detuned-saw lead (pedal-point figures, then scale runs), one-beat stop before the chorus |
| 24-27 | 49-56 | B2 | final chorus (busier hats/bass, sequencer sparkle); last bar = V chord + fill + pickup into order 04 |

## Channels
1 lead - 2 lead echo - 3 second voice - 4 arp chords - 5 pluck sequencer - 6 sequencer echo / chorus lead double -
7 bass - 8 kick - 9 snare - 10 hi-hats - 11 toms + clap - 12 crash + noise riser - 13/15 pad pair A (L/R) -
14/16 pad pair B (L/R)

## Sound design
No instrument envelopes, auto-vibrato or keymaps are used (not available in this FT2 build). All shaping is
baked into the 16-bit sample data or written into the patterns:
- PWM lead: 256 band-limited pulse cycles whose duty sweeps 50% -> 19% -> 50% (looped).
- Plucks and bass: decay / filter-sweep attack, then a one-cycle sustain loop. Pads: triads with a baked fade-in.
- Drums are one-shots with a 4.6 ms pre-roll so FT2's 5 ms voice fade-in does not blunt their transients.
- Stereo: lead, bass, kick stay centred; arp stabs and lead echoes ping-pong left/right, each pad chord is a
  left/right pair of differently-phased samples, the chorus lead gets a +6 cent double on the left.
- Patterns use arpeggio (0xy), tone portamento (3xx), vibrato (4xy), porta up (1xx, noise riser),
  set panning (8xx), volume slides (Axy), note cut (ECx) and the volume column (gating, side-chain "pump").

## Loop design
Every channel is cut on the final tick of the last row (and identically at the end of the intro), so the main
theme always starts from the same state. `src/looptest.py` renders intro + body + body and confirms that the
second pass is sample-identical to the first and that the seam is click-free (see `looptest.txt`).

## Rebuild / verify
```
cd src && python3 build.py tune_raw.xm        # deterministic: fixed RNG seed, same bytes every run
./package.sh /some/output/dir                 # FT2 load+save, preview render, checks, checksums
python3 stems.py; python3 verify.py 0 2 6     # per-channel renders; pitch-tracks lead/2nd voice/bass against the score
```

## Provenance and control notes (SOC 2 / ISO 27001 context)
- Originality / IP: melody, harmony, arrangement and every sample were created in this workspace by the scripts
  in `src/` (NumPy synthesis). No third-party samples, modules, presets or other licensed material were used.
- Integrity and traceability: the build is deterministic and scripted; `SHA256SUMS.txt` covers all deliverables,
  and `verification.json` records the measured render properties (peak, RMS, DC offset, clipping count, end frames).
- Data handling: the files contain no personal data, credentials, customer data or environment details; text
  fields in the module hold only the title and instrument/sample descriptions.
- Operational scope: built offline, no network access, no software installed, writes confined to `/workspace`.
- Scope of the artefact: a music file only. It implements no licensing, serial-number or copy-protection logic.
