# Keygen tune production: tools, formats, and workflow

Version 1.0.0  
Research cut-off: 2026-09-04  
Language: English

## Core finding

The ordinary keygen tune was usually tracker music, not a rendered MP3 or WAV. A musician entered notes, instrument numbers, volume values, and effect commands into a vertical pattern grid. The resulting module stored the score together with a small bank of reusable samples. A compact replay engine inside the executable mixed that data into PCM audio at runtime.

The central surviving formats are MOD, XM, S3M, and IT. Their canonical authoring programs were ProTracker, FastTracker II, Scream Tracker 3, and Impulse Tracker. Later Windows-era work could be edited in ModPlug Tracker/OpenMPT or in FT2-compatible tools such as MilkyTracker. The exact program used for a specific tune cannot safely be inferred from its extension alone.

A second route existed: procedural synthesizers such as Farbrausch V2 and 4klang stored note, patch, and synthesis data rather than PCM samples. That route matters to the wider demoscene and appears in keygen-music collections, but it was designed primarily for severe size limits such as 4K intros. It should not be treated as the default explanation for classic keygen music.

## Repository map

- `docs/00-methodology.md`
- `docs/01-historical-toolchain.md`
- `docs/02-how-tracker-composition-works.md`
- `docs/03-sound-design-and-optimization.md`
- `docs/04-formats.md`
- `docs/05-executable-playback.md`
- `docs/06-procedural-synthesis.md`
- `docs/07-case-studies.md`
- `docs/08-modern-reproduction.md`
- `docs/09-faq.md`
- `docs/references.md`
- `data/tool-format-matrix.csv`
- `data/evidence-register.csv`
- `data/archive-examples.csv`
- `tools/module_probe.py`

## Scope

This repository covers music production, file formats, replay technology, and technical history. It contains no keygens, cracks, license-bypass code, protected software, or archived music files.
