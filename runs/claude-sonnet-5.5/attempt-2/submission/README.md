# Cipher Rain - keygen-style tracker tune (FastTracker II / XM)

**Music only.** The deliverable is `tune.xm`: an editable FastTracker II module (16 channels, 21 patterns of 64 rows,
65 instruments, 150 BPM, speed 6, 134.4 s per pass). "Keygen" refers to the tracker-music genre (chip pulse arpeggios, supersaw leads,
four-on-the-floor drums). The module is passive audio data - it contains no executable code and no software-protection
or licence-bypass logic of any kind.

## Musical overview
* Key A minor, 150 BPM, 1 row = 1/16 note. Harmony: Andalusian line Am-G-F-E (A, intro, recap), F-G-Am-E (chorus),
  Am-F-C-G / E (drop), F-C-G-Am / F-C-G-E (breakdown + build).
* Form (patterns): intro 0-1 | A1 2-3 | A2 4-5 | B1 6-7 | B2 8-9 | breakdown 10 + build 11 | drop C1 12-13 | C2 14-15 |
  half-time bridge 16 (Dm-Am-F-E, new melody) | A3 17-18 | turnaround 19-20, then loop to **restart order 2**.
* Three hooks: A (arch-shaped arpeggio hook, teased on the chip pulse in the intro), B (long-note chorus melody with a
  little vibrato), C (3-3-2 syncopated drop riff). Ping-pong dotted-eighth echoes, side-chain style pad pumping
  (volume-column slides), trance-gated pads in the build, filter-open arps (dark -> mid -> bright samples).
* All sounds are synthesised from scratch with NumPy (kick, snare, hats, crash, tom, 5-voice supersaw, PWM pulse, sub/saw
  bass, chord pads and stabs as single-channel chord samples, FM bell, formant "aah", noise riser, impact). The shaping
  (attacks, decays, filter sweeps, chorus) is baked into the sample data; no envelopes are used.

## Loop behaviour
* The last row of the last pattern (order 20, row 63) is a one-row stop-time: every channel is cut, so nothing hangs over
  the seam and the restart (order 2, Am downbeat with crash + kick + hook) starts from silence. Harmony flows E (V) -> Am (i).
* Verified: rendering from the restart order is sample-identical to the tail of the full render (cold start == warm
  start), the first and last frames are 0.0, and no click is detectable at the seam.

## Build / reproduce
`cd src && python3 package.py` regenerates every sample, builds the XM, round-trips it through the FT2 engine
(`module_load` / `module_save`), validates it and renders `preview.wav`. The build is deterministic (fixed seeds, no
external inputs, no network access). `src/` holds all generator code.

## Design decisions and the controls they address
(Alignment notes for the audit trail - not a certification statement. Control references: ISO/IEC 27001:2022 Annex A,
SOC 2 Trust Services Criteria.)

| Decision | Why | Controls |
|---|---|---|
| Every sound is synthesised in code; no samples, presets or code from third parties | no licence / IP exposure, nothing to attribute or revoke | ISO A.5.32; SOC 2 CC (legal & contractual) |
| Deterministic generator (fixed seeds), single build entry point, sources shipped with the module | reproducible, reviewable, change-controlled output | ISO A.8.9, A.8.28, A.8.32; SOC 2 CC8.1 |
| FT2 round-trip + independent structure validation + render-equality check | processing integrity of the delivered artefact | SOC 2 PI1; ISO A.8.29 |
| SHA-256 manifest and build log kept next to the module | tamper evidence and audit evidence | ISO A.8.15, A.5.33; SOC 2 CC7 / PI1 |
| No paths, host names, user names or free text in the module; no network use in tooling | data minimisation / leakage prevention | ISO A.8.12, A.5.34; SOC 2 C1 |
| Peak below full scale at default amplitude, bounded values, loop seam verified, small bounded file set | the artefact plays back safely and predictably anywhere | SOC 2 A1; ISO A.8.6 |

## Governance notes (SOC 2 / ISO 27001 alignment)
* **Provenance / IP (legal & licensing):** 100 % original composition and procedurally generated sounds; no third-party
  samples, presets, MIDI or code were used or embedded. Reproducible from `src/`.
* **Integrity:** `MANIFEST.sha256` lists SHA-256 digests of every file in this directory; `build_log.txt` records the
  automated checks (XM structure validation, render equality between the generator output and the FT2-saved file,
  loop-seam check, clipping / DC checks). Final-module hash is recorded below.
* **Confidentiality / data minimisation:** no personal data, credentials, host names or file-system paths are stored in
  the module (text fields are only the title and generic instrument names); scripts perform no network access.
* **Availability / robustness:** peak level below full scale at the default render amplitude (no clipping), strictly
  bounded values (notes, volumes, effects validated), loop seam verified, directory far below the 128 MiB / 4096-file
  limits and contains only regular files (no links or special files).
* **Change management / traceability:** single deterministic build entry point, sources versioned alongside the output,
  all calibration constants (mix gains) in `src/mixer.py`.

## Final artefact digests (SHA-256)
* tune.xm      8e7be7e56f9556227558e3fbb028f0dfbd18f5d5da7b054348a9acc55b9fe070
* preview.wav  769751f26ded23e8c57542f03e6415dd87eafcc0a1d2c88a3072aea2f0ec400b
