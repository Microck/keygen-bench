# Methodology and confidence rules

## Research question

The investigation asks two separate questions:

1. Which programs or classes of programs were used to create music associated with keygens, cracktros, trainers, and related scene executables?
2. What technical process turned a composition into audio heard from a small executable?

Those questions are easy to blur. “Program used” can mean at least five different things:

| Layer | Meaning |
|---|---|
| Authoring tracker | Where notes, patterns, instruments, and effects were entered |
| Sample tool | Where source sounds were recorded, synthesized, cropped, looped, or converted |
| Converter/optimizer | A tool that rewrote or stripped a module after composition |
| Replay engine | Code that decoded and mixed the module at runtime |
| Executable toolchain | Compiler, resource compiler, linker, or compressor used around the music |

A module header may identify only one of those layers. An XM field reading `MOD2XM 1.0`, for example, identifies a conversion/export step. It does not identify the original composer, tracker, sample editor, or player library.

## Source hierarchy

### Tier A: direct technical evidence

- original source code or documentation from a tracker or replayer;
- official project manuals;
- an actual module header, magic value, metadata field, or file tree entry;
- source code demonstrating a player’s intended loading method.

### Tier B: strongly corroborated context

- maintained format documentation from OpenMPT or libopenmpt;
- faithful source restorations or clones based on original code;
- a public archive’s own description and index;
- several independent primary projects describing the same workflow.

### Tier C: interpretation

- explanations of why a technique saved space;
- reconstruction of a likely production sequence;
- stylistic observations about “keygen sound”;
- claims about what was common across the entire scene.

## Corpus rule

The `sxiii/keygen-music` repository is used as a convenience corpus, not as a statistically representative sample of every era, country, group, or platform. Its README describes a collection derived from KeygenMusic.net, not a controlled historical census.

Therefore:

- a path in the archive proves that the archive contains that file association;
- an extension proves the stored format when the file is valid;
- a header can prove a title or exporter field;
- the archive does not prove that every named executable originally shipped with exactly that byte-for-byte file;
- collection-wide averages should not be generalized to all keygen music.

## Attribution rule

Format and tool attribution are kept separate.

| Observation | Safe conclusion | Unsafe conclusion |
|---|---|---|
| File ends in `.xm` and has an XM magic header | It is an XM module | It was definitely composed in FastTracker II |
| XM tracker field says `MilkyTracker` | MilkyTracker wrote or last saved that file | Every musical idea and sample originated there |
| Field says `MOD2XM 1.0` | A converter/exporter touched the file | The original tracker was MOD2XM |
| File is played by uFMOD in source code | That build used uFMOD for XM playback | The composer used uFMOD to write the tune |
| Archive filename includes a group name | The collection associates the file with that group/release | Authorship is conclusively established |

## Terminology

### Tracker

A sequencer organized around rows, channels, notes, instruments, and effects. Patterns are arranged in an order list.

### Module

A self-contained tracked-music file containing a score and usually sample or instrument data. MOD, XM, S3M, and IT are module formats.

### Replayer

Code that interprets a module and produces PCM audio. Playback behavior is part of the musical result because trackers disagree on edge cases and effect semantics.

### Chiptune or chip-style

Used here as a sonic description unless a file is known to target an actual sound chip. Many keygen tunes sound chip-like while using ordinary PCM samples and a software mixer.

### Procedural synth music

Music stored as compact score and synthesis parameters, rendered by a software synthesizer at runtime. V2M and 4klang projects belong here rather than to the conventional sampled-module path.

## Reproducibility

The repository includes:

- a machine-readable tool/format matrix;
- a claim register with confidence and caveats;
- selected public archive paths, sizes, and blob hashes;
- a dependency-free module-header inspector for XM, IT, S3M, and common MOD signatures;
- unit tests built from synthetic headers, not copyrighted songs.

No third-party music files are included.
