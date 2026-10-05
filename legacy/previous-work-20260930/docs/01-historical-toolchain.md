# Historical toolchain

## The short list

The programs most relevant to the classic workflow are:

- ProTracker and its Soundtracker/NoiseTracker lineage for Amiga MOD files;
- Scream Tracker 3 for S3M files on DOS;
- FastTracker II for XM files on DOS;
- Impulse Tracker for IT files on DOS;
- ModPlug Tracker/OpenMPT for Windows-era editing and playback of several module families;
- MilkyTracker as a later, cross-platform FT2-style MOD/XM environment;
- compact replay libraries such as uFMOD, MiniFMOD, and BASS/BASSMOD for runtime playback;
- Farbrausch V2 and 4klang for the separate procedural-synthesis route.

This is a toolchain map, not a claim that every listed program was equally common in every group or period.

## Amiga: ProTracker and MOD

Classic Amiga tracker music established the basic production model: a small set of sampled instruments, four playback channels, vertically scrolling patterns, an order list, and compact effect commands. ProTracker 2.x became a defining editor and replayer for the 31-sample MOD family.

The maintained `pt2-clone` project aims to reproduce ProTracker 2.3D and the sound of Amiga playback closely. The preserved ProTracker 2.3D help text documents the original tracker environment and effect-oriented workflow.

Why it mattered later:

- the MOD structure was simple and portable;
- short samples and four channels forced economical arranging;
- the music could be replayed without shipping a long rendered recording;
- the characteristic effect vocabulary carried into later PC formats.

A Windows keygen containing a MOD did not necessarily mean the tune was composed on an Amiga. MOD remained an exchange and delivery format long after the original platform.

## DOS: Scream Tracker 3 and S3M

Scream Tracker 3’s S3M format expanded the PC tracker model with more channels, a richer effect set, sample instruments, and optional AdLib/OPL-style instruments. S3M also influenced the command vocabulary later used by Impulse Tracker.

The important production distinction is that S3M is not simply “a recording.” It stores song orders, patterns, channel events, instruments, and sample or FM-instrument data for a replayer to interpret.

## DOS: FastTracker II and XM

FastTracker II is the canonical authoring program for XM. Its major practical additions over classic MOD included:

- up to 32 channels in the original FT2 model;
- 8-bit and 16-bit sample support;
- instruments that map one or more samples across notes;
- volume and panning envelopes;
- instrument vibrato;
- packed pattern data;
- a larger effect vocabulary.

The modern `ft2-clone` project states that its XM player was ported from original FastTracker II source for accuracy. MilkyTracker likewise identifies itself as an FT2-inspired tracker and saves MOD/XM.

XM was especially suitable for small scene executables because it balanced richer instrumentation with a self-contained module and broad replay-library support.

## DOS: Impulse Tracker and IT

Impulse Tracker’s IT format extended the S3M-style model with advanced instrument behavior, New Note Actions, filters, more flexible sample mapping, and sample compression. Those features permitted high polyphony without assigning every overlapping note to a permanently separate pattern channel.

Jeffrey Lim’s original source repository contains the tracker, playback code, sample compression/decompression routines, pattern editor, instrument editor, and supporting documentation.

## Windows: ModPlug Tracker and OpenMPT

ModPlug Tracker brought a multi-format tracker workflow into native Windows. Its maintained successor, OpenMPT, can edit and replay MOD, XM, S3M, IT, and its own MPTM format.

For keygen-style delivery, a musician could work in OpenMPT but export a conservative XM or IT file for an older replay library. OpenMPT’s compatibility-export documentation exists precisely because tracker-specific extensions can break or change playback in other engines.

## Cross-platform: MilkyTracker

MilkyTracker recreates the FT2-style user experience and focuses on accurate XM replay, with ProTracker-compatible MOD modes. Its manual documents a complete production environment:

- pattern and order editing;
- sample loading and editing;
- waveform generators and synthesis functions;
- forward and ping-pong loops;
- instruments and envelopes;
- effect commands;
- module optimization;
- WAV rendering for checking output.

This makes it a strong modern tool for reconstructing the sample-based workflow without requiring DOS.

## Replay engines were separate programs or libraries

The program that played a tune inside an executable was usually not the program that composed it.

### uFMOD

uFMOD is an assembly-language XM replay library designed for size- and speed-critical software. Its project describes support for XM effects, compact operation, compressed samples, and XMStrip for reducing an XM file.

### MiniFMOD

MiniFMOD was a stripped XM replayer derived from FMOD-era code. Its documentation describes static linking, memory/resource loading, and a build process that could omit effect implementations unused by a selected song.

### BASS and BASSMOD

BASS provides runtime MOD-music support for XM, IT, S3M, MOD, MTM, UMX, and MO3. It can load music from memory and mix it through a compact library. Historical software also used the module-only BASSMOD line.

### Other replayers

Custom replayers, FMOD variants, libmodplug, and group-specific code also existed. Modern equivalents include libopenmpt and libxmp. An extension alone cannot reveal which one was linked into an executable.

## Procedural synthesizers: a different branch

Farbrausch V2 and 4klang do not primarily store a bank of PCM instrument samples in the same way as XM or IT.

- V2 uses compact song and synthesizer data, commonly associated with `.v2m`.
- 4klang provides a VST instrument for composition and an assembly synth core plus exported song data for inclusion in a very small executable.

The official 4klang repository states that it was built for 4K intros, where the entire executable can be limited to 4096 bytes.

These systems explain some scene music, especially size-coded demos. They should be considered an adjacent or occasional keygen route, not evidence that ordinary XM/MOD keygen tunes were generated procedurally.
