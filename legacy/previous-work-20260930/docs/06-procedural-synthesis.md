# Procedural synthesizers: V2 and 4klang

Tracker modules and procedural synth songs solve the same delivery problem differently.

```text
sample-module route: patterns + instruments + PCM samples + replayer
procedural route: score + synth patches + automation + real-time synth engine
```

## Farbrausch V2

Farbrausch's public tools preserve the V2 synthesizer and related V2M playback code. A V2M-style package stores compact musical events and synthesizer state rather than a conventional bank of PCM samples.

Typical concept:

1. create patches in the V2 editor/plugin environment;
2. sequence notes and controls;
3. export compact V2M data;
4. include the V2 player/synth in the executable;
5. render audio at runtime.

## 4klang

The official 4klang repository includes a VSTi, example projects, a synth core, and assembly data intended for inclusion in tiny executables. Its documented primary target is the 4K intro.

The production chain is approximately:

```text
VSTi project → compact patch/song export → assembly synth core → runtime rendering
```

## Relevance to keygen music

Procedural synth formats overlap with the broader scene and appear in keygen-music collections. That does not establish them as the dominant route for classic keygen tunes.

A file with an XM, MOD, S3M, or IT header belongs to the sampled-module route unless other direct evidence says otherwise.
