# KeyGen Synth - Original Keygen Tune

## Overview
An original, energetic keygen-style chiptune composition made with FastTracker II and synthesized instruments.

## Technical Specifications
- **Format**: XM (FastTracker II Extended Module)
- **Channels**: 4 (stereo pair)
- **Tempo**: 140 BPM
- **Speed**: 4 ticks/row
- **Pattern Length**: 32 rows per pattern
- **Song Structure**: 5 song order positions
- **Total Duration**: ~23 seconds

## Arrangement

### Channels
- **Channel 0**: Lead Melody (bright, energetic synth)
- **Channel 1**: Bass Line (deep bass with harmonics)
- **Channel 2**: Pad/Chords (smooth, sustained background)
- **Channel 3**: Drums/Percussion (kick and snare)

### Patterns
1. **Pattern 0 (Intro)**: 32 rows
   - Establishes the groove with drums and bass
   - Introduces pad chords in the second half
   - No lead melody yet
   - Sets up for the main theme

2. **Pattern 1 (Main)**: 32 rows
   - Full arrangement with lead melody
   - Catchy, memorable melody in the lead channel
   - Bass line follows chord progression (C-Am-F-G)
   - Pad provides harmonic support
   - Driving drum pattern

### Song Order
1. Position 0: Pattern 0 (Intro)
2. Position 1: Pattern 1 (Main A)
3. Position 2: Pattern 1 (Main A - repeated)
4. Position 3: Pattern 1 (Main A - repeated)
5. Position 4: Pattern 0 (Outro/return to loop start)

## Harmony & Melody
- **Key**: C Major
- **Scale**: Natural Major (C D E F G A B)
- **Chord Progression**: C - Am - F - G (repeated)
- **Lead Melody**: Arpeggiated patterns and scalar runs following the chord progression
  - Verse 1: C-E-G-E (arpeggio), D-F-A-F, E-G-B-G, C-E-G-F
  - Verse 2: D-F#-A-F#, E-G-B-G, F-A-C-A, G-B-D-B
  
## Instrumentation

### 1. Lead Synth
- Harmonic composition: Fundamental + 2nd + 3rd harmonics
- Fast attack (50ms), medium decay
- Bright, punchy character
- Suitable for memorable melodies

### 2. Bass Synth
- Deep sine wave base with 2nd harmonic
- Very fast attack (10ms), longer release (300ms)
- Provides rhythmic and harmonic foundation
- Plays root notes of the chord progression

### 3. Pad Synth
- Multiple sine waves (220, 330, 440 Hz)
- Slow attack (200ms), slow decay (500ms)
- Creates warm, sustained background
- Supports harmonic movement

### 4. Percussion Synth
- High-frequency click (800-2000 Hz sweep)
- Exponential decay for realistic drum character
- Two-voice pattern (kick/snare simulation)
- Provides rhythmic drive

## Rhythm & Groove
- **Drum Pattern**: Kick on main beats (every 4 rows), snare on backbeats
- **Bass**: Steady root note movement with chord changes every 8 rows
- **Lead**: Eighth note rhythms with rests for syncopation
- **Overall Feel**: Energetic, driving keygen style with infectious grooves

## Loop Structure
The module is designed to loop cleanly:
- Starts at position 0 (intro)
- Returns to loop start (position 0) after position 4
- Creates a cohesive cycle that sounds natural when repeated
- Total loop time: ~23 seconds

## Music Theory & Composition
This piece follows classic keygen/chiptune composition principles:
- Simple, memorable melody easy to recognize and recall
- Solid harmonic foundation using common chord progressions
- Energetic, driving rhythm that propels the listener forward
- Layered arrangement with distinct roles for each instrument
- Efficient use of patterns and reuse to create complexity from simplicity
- Appropriate timbres for the era of electronic music

## Synthesis Approach
All instruments were synthesized using:
- **Tool**: NumPy/Python for waveform generation
- **Sample Rate**: 8000 Hz (appropriate for classic keygen aesthetic)
- **Duration**: 2 seconds per sample
- **Technique**: Additive synthesis with shaped envelopes
  - Fundamental frequency + harmonics
  - Custom ADSR-like envelopes (Attack-Decay-Sustain)
  - Realistic instrument character achieved through timbre shaping

## Playback Notes
- Compatible with FastTracker II and other XM-capable trackers
- Designed for looping playback
- Clean loop points ensure seamless repetition
- Suitable for menu screens, demos, or intros in games/software

---
Created: 2024
Format: FastTracker II XM Module
Genre: Keygen/Chiptune
