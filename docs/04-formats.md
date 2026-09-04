# Formats and what they contain

| Format | Canonical tracker | Main sound model | Notes |
|---|---|---|---|
| MOD | ProTracker lineage | PCM samples | Simple pattern/order model; many variants |
| S3M | Scream Tracker 3 | PCM samples and optional AdLib/OPL instruments | More channels and S3M-style effects |
| XM | FastTracker II | PCM samples grouped into instruments | Envelopes, multisampling, 8/16-bit samples, packed patterns |
| IT | Impulse Tracker | Samples plus advanced instruments | New Note Actions, filters, sample compression |
| MO3 | MO3/BASS ecosystem | Module score with compressed samples | Module structure retained while samples are compressed |
| MIDI | Many sequencers | Event data only | Requires external or embedded synthesizer |
| V2M | Farbrausch V2 | Procedural synth patches plus score | Real-time synthesis |
| 4klang export | 4klang | Procedural modular synth | Built for tiny intros |

## MOD

Classic MOD stores a title, sample table, order list, pattern data, and sample data. Common 31-sample signatures such as `M.K.` appear near offset 1080.

## S3M

S3M stores orders, patterns, channel settings, sample instruments, optional OPL instruments, and tracker/version fields.

## XM

XM starts with:

```text
Extended Module: 
```

Its preheader stores module name, tracker/writer field, and version. The main header stores song length, restart position, channel count, pattern count, instrument count, speed, tempo, and order data.

The tracker field identifies the program or converter that wrote that saved file, not necessarily the original composing program.

## IT

IT starts with:

```text
IMPM
```

It supports separate sample and instrument objects, advanced note actions, filters, sample compression, channel pan/volume settings, and creation/compatibility fields.

## MIDI

MIDI stores performance events rather than final waveform data. The same MIDI can sound very different depending on the synthesizer or sound bank.

## Procedural formats

V2M and 4klang-style exports encode notes, automation, patches, and synthesis state. The executable includes a real-time synth instead of a bank of PCM samples.

## Platform-specific chip formats

Collections also include SID, YM, SC68, AHX, NSF, SAP, SPC, and related formats. These belong to different platform-specific playback systems and should not be collapsed into one XM/MOD workflow.
