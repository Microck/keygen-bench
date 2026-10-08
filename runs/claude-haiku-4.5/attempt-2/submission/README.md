# Keygen Tune - Original Composition

## Overview
An original high-energy keygen tune composed in FastTracker II with custom synthesized instruments. The tune features a driving rhythm, catchy melodies, and clean looping structure typical of classic keygen music.

## Musical Specifications

### Tempo & Timing
- **BPM:** 135 (fast, energetic pace)
- **Speed:** 6 ticks per row
- **Time Signature:** 4/4
- **Pattern Length:** 64 rows per pattern
- **Duration:** ~49 seconds total (7 patterns × ~7 seconds each, looping)

### Key & Harmony
- **Key:** C minor (energetic, slightly dark mood)
- **Harmonic Progression:** 
  - Verse: i-III-VI-i (Cm-Eb-G-Cm)
  - Lead melodies explore the minor scale with chromatic variations

### Instrumentation

#### 1. Kick Drum (Instrument 1)
- Pitched kick: sine wave sweep (150Hz → 40Hz)
- Fast exponential decay with amplitude envelope
- Pattern: Strong on beats 1 & 3 (verses), double-time on chorus

#### 2. Hi-Hat Cymbal (Instrument 2)
- White noise filtered for brightness
- Sharp attack, rapid decay
- Creates off-beat rhythmic texture (eighth-note patterns)
- More frequent in chorus sections

#### 3. Bass (Instrument 3)
- Square wave with pulse-width modulation
- Fundamental: ~50Hz
- Plays simple riff pattern: C-Eb-G-C
- Provides harmonic foundation with groove

#### 4. Lead Synth (Instrument 4)
- Sawtooth wave with harmonic richness
- Frequency: ~220Hz (A3)
- Multiple arpeggio patterns and melodic phrases
- More prominent in chorus sections

### Composition Structure

| Pos | Pattern | Name | Description |
|-----|---------|------|-------------|
| 0 | 0 | Intro | Kick + hi-hat only, minimal arrangement |
| 1 | 1 | Build-up | Bass enters with simple riff |
| 2 | 2 | Verse 1 | Lead arpeggio added, all elements present |
| 3 | 3 | Chorus | Lead plays active melody, increased hi-hat |
| 4 | 4 | Verse 2 | Repeat verse with bass variation |
| 5 | 5 | Chorus 2 | Final chorus with higher register melody |
| 6 | 6 | Outro | Wind-down to intro for clean loop |

### Technical Details
- **Channels:** 4
- **Total Patterns:** 7
- **Loop Point:** Position 0 (infinite loop)
- **Sample Rate Rendering:** 44100 Hz, 16-bit

## Sound Design Notes

All instruments were synthesized using NumPy and loaded as base64-encoded PCM samples:

1. **Kick Drum:** Frequency sweep simulates classic drum machine kick patterns
2. **Hi-Hat:** Noise-based with high-frequency emphasis for realistic cymbal character
3. **Bass:** Simple square wave with PWM creates solid, punchy low-end
4. **Lead Synth:** Rich harmonic content from sawtooth wave allows melodic expression

Envelope shaping was critical to prevent clicks and clicks while maintaining percussive character.

## Composition Approach

The tune follows classic keygen structure:
- **Minimal intro** builds anticipation
- **Progressive arrangement** adds instruments gradually
- **Energetic chorus** with active lead melody
- **Variation** prevents repetition fatigue in looping context
- **Smooth outro** transitions naturally back to intro

## Files

- `tune.xm` - Final FastTracker II module (editable format)
- `README.md` - This documentation

## Quality Assessment

- ✓ Rendered to WAV without clipping (-10.4dB peak)
- ✓ Clean loop transition from end to beginning
- ✓ Proper MIDI note mapping for all instruments
- ✓ Balanced mix with good energy throughout
- ✓ Typical keygen tune length and structure

---
Composed using FastTracker II with Python/NumPy synthesis tools.
