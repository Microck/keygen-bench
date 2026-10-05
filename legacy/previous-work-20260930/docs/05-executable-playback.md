# Executable playback and replay engines

## Runtime architecture

A small scene executable commonly followed this audio path:

```text
module bytes
    ↓
module replayer
    ↓
software mixer
    ↓
PCM buffers
    ↓
waveOut, DirectSound, or another audio backend
```

The UI and unrelated executable logic were separate from the music data and player.

## Packaging

Common ways to ship the music included:

- a Windows resource;
- a compiled byte array;
- a custom executable section;
- appended data;
- a separate module file beside the executable.

A generic model was:

```text
initialize audio
locate module bytes
load module from memory
enable looping
start playback
stop and release audio on exit
```

## uFMOD

uFMOD is an assembly-language XM replayer aimed at size- and speed-critical applications. It supports compact XM playback and includes tools such as XMStrip for reducing modules.

## MiniFMOD

MiniFMOD is a stripped XM player derived from the FMOD ecosystem. Historical documentation describes static linking, resource/memory loading, and compile-time removal of unused XM effects.

## BASS / BASSMOD

BASS supports module playback for XM, IT, S3M, MOD, MTM, UMX, and MO3 and can load music from memory. Historical BASSMOD was a module-focused relative.

## Modern archival players

libopenmpt and libxmp are useful current multi-format replayers. Their existence is not evidence that an older keygen used them.

## Why compatibility mattered

Two replay engines can differ in:

- tick rounding;
- effect memory;
- interpolation;
- volume ramping;
- clipping;
- panning;
- envelope behavior;
- loop handling.

That is why a tune had to be tested in its intended player, not only in the tracker.

## Synchronization

Tracker playback naturally exposes order, pattern, row, and tick positions. Scene programs could use those positions to synchronize text, color changes, logos, or other visual events.

## Verifying a specific executable

A defensible player attribution requires source code, imports, strings, code signatures, resource metadata, or other executable-side evidence. A detached module does not identify its runtime replay library.
