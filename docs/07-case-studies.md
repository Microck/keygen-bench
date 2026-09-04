# Evidence and case studies

## Public keygen-music corpus

The `sxiii/keygen-music` repository describes itself as a collection of keygen music gathered from the KeygenMusic.net megapack. It is used here as a convenience corpus, not as a controlled census of the entire scene.

Representative archived formats include XM, IT, MOD, MIDI, SC68, V2M, S3M, SID, YM, AHX, NSF, MO3, and others.

## Concrete XM header example

An archived file associated with `APACHE - Titan Quest 1.08 +13 trn.xm` has:

- size: 11,065 bytes;
- blob SHA: `8c569a1a07fd2bfea209c2c42c8983f869a25b10`;
- XM magic: `Extended Module: `;
- module title: `antipasti#16`;
- tracker/exporter field: `MOD2XM 1.0`.

That proves an XM conversion/writer step. It does not prove the original composing tracker, composer identity, or runtime replay engine.

## Replay-engine evidence

uFMOD and MiniFMOD document a workflow where an XM is authored separately, optionally stripped or optimized, then loaded from memory/resource data by a small replay engine.

MiniFMOD is particularly useful evidence because its historical docs describe compiling out unused effects, directly connecting song command choices to player size.

## Procedural evidence

4klang’s official repository shows the alternate production chain:

```text
VSTi project → compact song/patch export → assembly synth core → runtime rendering
```

This is direct evidence for procedural demoscene audio, not evidence that all keygen tunes used that method.

## Confidence summary

| Claim | Confidence |
|---|---|
| Tracker modules were a major delivery form | High |
| XM/MOD/IT/S3M were central module formats | High |
| Every XM was composed in FastTracker II | False |
| A detached module identifies its runtime player | False |
| 4klang was built for 4K intros | High |
| Procedural synths were the dominant keygen route | Not established |
