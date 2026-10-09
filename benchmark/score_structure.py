"""Content-based XM sequencing evidence; no audio renderer or external dependencies."""
from __future__ import annotations

from collections import defaultdict
import math

PHRASE_ROWS = 16
MAX_SEQUENCE_ROWS = 65536
MAX_SEQUENCE_EVENTS = 65536
TICKS_PER_BEAT = 24
DEVELOPMENT_BEATS = (4, 8, 16)
# Bound pairwise work by coalescing identical passages and rejecting excessive
# unique content rather than silently scoring only a prefix of the composition.
MAX_PASSAGE_COMPARISONS = 8_000_000
DEVELOPMENT_METHOD = "voice-self-similarity-4-8-16-beats-v1"


def _sample(xm, instrument, note):
    if not 1 <= instrument <= len(xm["instruments"]):
        return None
    inst = xm["instruments"][instrument - 1]
    sample_map = inst.get("sample_map", [0] * 96)
    if not 1 <= note <= len(sample_map):
        return None
    index = sample_map[note - 1]
    if not 0 <= index < len(inst["samples"]):
        return None
    sample = inst["samples"][index]
    return (instrument, index, sample) if sample.get("frames", 0) > 0 else None


def _sequence(xm):
    """Walk one song pass, stopping at a repeated control state or the row limit.

    Fxx, Bxx, Dxx, E6x and EEx affect traversal/timing. This is not an FT2
    voice emulator: envelopes, PCM silence, tick pitch effects, sample endings,
    and instrument-only retriggers are not used to infer audibility.
    """
    channels = xm["channels"]
    memory = [0] * channels
    volume = [64] * channels
    voices = [None] * channels
    audible = [False] * channels
    starts, counts = [0] * channels, [0] * channels
    speed, bpm = max(1, xm["speed"]), max(32, xm["bpm"])
    global_volume = 64
    order = xm["order"][:xm["song_length"]]
    order_index = row = 0
    seen, reached, samples, active_channels = set(), set(), set(), set()
    rows, seconds, warnings = [], 0.0, set()
    row_ticks = []
    ticks = 0
    event_total = 0
    row_cache = {}
    reason = "order_table_end"
    while 0 <= order_index < len(order):
        if len(rows) >= MAX_SEQUENCE_ROWS:
            reason = "row_limit"
            break
        if event_total >= MAX_SEQUENCE_EVENTS:
            reason = "event_limit"
            break
        pattern_index = order[order_index]
        if not 0 <= pattern_index < len(xm["patterns"]):
            reason = "invalid_pattern_reference"
            break
        pattern = xm["patterns"][pattern_index]
        # The reference FT2 loader frees entirely empty patterns and resets them to 64 rows.
        pattern_rows = pattern["rows"] if pattern["cells"] else 64
        if not 0 <= row < pattern_rows:
            reason = "invalid_pattern_row"
            break
        state = (order_index, row, speed, bpm, tuple(starts), tuple(counts), global_volume)
        if state in seen:
            reason = "repeated_control_state"
            break
        seen.add(state)
        reached.add(order_index)
        if pattern_index not in row_cache:
            by_row = defaultdict(list)
            for cell in pattern["cells"]:
                if 0 <= cell[1] < channels:
                    by_row[cell[0]].append(cell)
            row_cache[pattern_index] = by_row
        cells = sorted(row_cache[pattern_index].get(row, ()), key=lambda c: c[1])
        jump = break_row = loop_row = None
        delay = 0
        # Global commands are resolved left-to-right, as tracker channels are.
        for _, channel, _, _, _, effect, param in cells:
            if effect == 0xF:
                if param == 0:
                    warnings.add("F00 is treated as no tempo change")
                elif param < 32:
                    speed = param
                else:
                    bpm = param
            elif effect == 0xB:
                jump = param
            elif effect == 0xD:
                break_row = (param >> 4) * 10 + (param & 15)
            elif effect == 0x10:
                global_volume = min(64, param)
            elif effect == 0xE and param >> 4 == 6:
                count = param & 15
                if count == 0:
                    starts[channel] = row
                elif counts[channel] == 0:
                    counts[channel] = count
                    loop_row = starts[channel]
                else:
                    counts[channel] -= 1
                    if counts[channel]:
                        loop_row = starts[channel]
            elif effect == 0xE and param >> 4 == 14:
                delay = param & 15
            elif effect == 0x11:
                warnings.add("global volume slides are not simulated")
        events = []
        changed = set()
        for _, channel, note, instrument, vol, effect, param in cells:
            changed.add(channel)
            if instrument:
                memory[channel] = instrument
            new_note = 1 <= note <= 96
            delayed = effect == 0xE and param >> 4 == 13
            if delayed and (param & 15) >= speed:
                new_note = False
            if note == 97 or (effect == 0x14 and param == 0):
                voices[channel] = None
            if new_note:
                target = _sample(xm, memory[channel], note)
                porta = effect in (3, 5) or vol >> 4 == 15
                if not porta or voices[channel] is None:
                    voices[channel] = (note, target) if target else None
                else:
                    # A portamento target is sequenced pitch content, but does
                    # not start the sample mapped to that target note.
                    voices[channel] = (note, voices[channel][1])
                if instrument and target:
                    volume[channel] = min(64, max(0, target[2].get("volume", 64)))
            if 0x10 <= vol <= 0x50:
                volume[channel] = vol - 0x10
            if effect == 0xC:
                volume[channel] = min(64, param)
            if effect == 0xE and param >> 4 == 12 and (param & 15) == 0:
                volume[channel] = 0
            voice = voices[channel]
            now_audible = voice is not None and volume[channel] > 0 and global_volume > 0
            if now_audible and (new_note or not audible[channel]):
                pitch, target = voice
                instrument_id, sample_id, _ = target
                events.append((channel, pitch, instrument_id, sample_id))
                samples.add((instrument_id, sample_id))
                active_channels.add(channel)
            audible[channel] = now_audible
            # Slides can make a zero-volume trigger audible later in this row.
            before_slide = volume[channel]
            if effect in (5, 6, 0xA) and param:
                volume[channel] += ((param >> 4) or -(param & 15)) * max(0, speed - 1)
            if vol >> 4 in (6, 7):
                volume[channel] += (1 if vol >> 4 == 7 else -1) * (vol & 15) * max(0, speed - 1)
            elif vol >> 4 in (8, 9):
                volume[channel] += (1 if vol >> 4 == 9 else -1) * (vol & 15)
            if effect == 0xE and param >> 4 in (10, 11):
                volume[channel] += (1 if param >> 4 == 10 else -1) * (param & 15)
            volume[channel] = min(64, max(0, volume[channel]))
            if voice and before_slide == 0 and volume[channel] > 0 and global_volume > 0:
                pitch, target = voice
                instrument_id, sample_id, _ = target
                events.append((channel, pitch, instrument_id, sample_id))
                samples.add((instrument_id, sample_id))
                active_channels.add(channel)
                audible[channel] = True
            if effect == 0xE and param >> 4 == 12 and (param & 15) < speed:
                volume[channel] = 0
                audible[channel] = False
        # A global-volume command can reveal a previously muted voice.
        for channel, voice in enumerate(voices):
            if channel in changed:
                continue
            now_audible = voice is not None and volume[channel] > 0 and global_volume > 0
            if now_audible and not audible[channel]:
                pitch, target = voice
                instrument_id, sample_id, _ = target
                events.append((channel, pitch, instrument_id, sample_id))
                samples.add((instrument_id, sample_id))
                active_channels.add(channel)
            audible[channel] = now_audible
        rows.append(tuple(sorted(events)))
        row_ticks.append(ticks)
        ticks += speed * (delay + 1)
        event_total += len(events)
        seconds += 2.5 * speed / bpm * (delay + 1)
        if loop_row is not None and (jump is not None or break_row is not None):
            warnings.add("simultaneous E6x and Bxx/Dxx use jump/break precedence")
        if jump is not None or break_row is not None:
            order_index = jump if jump is not None else order_index + 1
            row = break_row if break_row is not None else 0
            starts, counts = [0] * channels, [0] * channels
        elif loop_row is not None:
            row = loop_row
        elif row + 1 < pattern_rows:
            row += 1
        else:
            order_index += 1
            row = 0
            starts, counts = [0] * channels, [0] * channels
    return rows, samples, active_channels, reached, seconds, reason, sorted(warnings), row_ticks, ticks


def _overlap(left, right):
    """Jaccard similarity on nonempty onset/pitch sets."""
    intersection = len(left & right)
    return intersection / (len(left) + len(right) - intersection)


def _development(rows, row_ticks, ticks):
    """Compare each voice with other passages, never borrowing another's coherence."""
    scales = []
    for beats in DEVELOPMENT_BEATS:
        width = beats * TICKS_PER_BEAT
        count = ticks // width
        grouped = defaultdict(lambda: defaultdict(set))
        for position, row in zip(row_ticks, rows):
            passage = position // width
            if passage >= count:
                break
            for channel, note, _, _ in row:
                grouped[passage][channel].add((position % width, note))
        # Counts retain the time occupied by repeats without storing an NxN SSM.
        passages = defaultdict(int)
        for voices in grouped.values():
            content = tuple(sorted({tuple(sorted(voice)) for voice in voices.values()}))
            passages[content] += 1
        passages[()] += count - len(grouped)
        entries = []
        for content, repeats in passages.items():
            if repeats:
                voices = [(frozenset(voice), frozenset((t, p - voice[0][1]) for t, p in voice))
                          for voice in content]
                entries.append((voices, repeats))
        voice_count = sum(len(voices) for voices, _ in entries)
        if voice_count * voice_count > MAX_PASSAGE_COMPARISONS:
            raise ValueError("development exceeds the bounded unique-passage comparison limit")
        value = recurrence = contrast = 0.0
        if count >= 2:
            for index, (voices, repeats) in enumerate(entries):
                for absolute, shape in voices:
                    strongest = 0.0
                    difference = 0.0
                    for other_index, (others, other_repeats) in enumerate(entries):
                        if other_index == index or not others:
                            continue
                        closest = related = 0.0
                        for other_absolute, other_shape in others:
                            closest = max(closest, _overlap(absolute, other_absolute))
                            # Exact copies establish repetition, not a relationship
                            # between changed ideas. Exclude them even when another
                            # voice makes the containing passage different.
                            if absolute != other_absolute:
                                related = max(related, _overlap(shape, other_shape))
                        strongest = max(strongest, related)
                        difference += (1 - closest) * other_repeats
                    difference /= count - 1
                    weight = repeats / (count * len(voices))
                    recurrence += weight * strongest
                    contrast += weight * difference
                    value += weight * strongest ** 2 * difference
        scales.append({"beats": beats, "complete_passages": count,
                       "distinct_passages": sum(bool(content) for content in passages),
                       "recurrence": round(recurrence, 6), "contrast": round(contrast, 6),
                       "development": round(value, 6)})
    return {"arrangement_score": round(sum(s["development"] for s in scales) / len(scales), 6),
            "development_method": DEVELOPMENT_METHOD, "development_scales": scales}


def structure_metrics(xm: dict, audible_channels: set[int] | None = None) -> dict:
    """Measure multiscale sequenced development; counts remain artifact diagnostics.

    Channel numbers and sample identities do not define musical identity. Each
    complete passage contributes equally, and distinct voices contribute equally
    within it. Global commands still run on excluded PCM-silent channels.
    """
    rows, used, channels, reached, seconds, reason, warnings, row_ticks, ticks = _sequence(xm)
    if audible_channels is not None:
        rows = [tuple(event for event in row if event[0] in audible_channels) for row in rows]
        used = {(event[2], event[3]) for row in rows for event in row}
        channels = {event[0] for row in rows for event in row}
    development = _development(rows, row_ticks, ticks)
    # Retain the existing sparse-sequencing artifact cap independently of v8.
    phrases = [rows[offset:offset + PHRASE_ROWS] for offset in range(0, len(rows), PHRASE_ROWS)]
    sequencing_phrases = sum(sum(bool(row) for row in phrase) >= 2 for phrase in phrases)
    coverage = sequencing_phrases / len(phrases) if phrases else 0.0
    event_count = sum(map(len, rows))
    used_samples = []
    for instrument, sample_index in sorted(used):
        sample_seconds = float(xm["instruments"][instrument - 1]["samples"][sample_index]["seconds_at_c4"])
        if not math.isfinite(sample_seconds) or sample_seconds < 0:
            sample_seconds = 0.0
        used_samples.append({"instrument": instrument, "sample": sample_index, "seconds_at_c4": sample_seconds})
    used_instruments = sorted({instrument for instrument, _ in used})
    limitations = [
        "Static sequencing evidence, not a measurement of musical quality or PCM audibility.",
        "Stops at order-table end or first repeated control state; restart tail is excluded.",
        "Voice envelopes, sample endings, PCM silence, instrument-only retriggers, and tick pitch effects are not simulated.",
        "Volume-slide parameter memory is not simulated; note delays/cuts only affect trigger eligibility and row audibility.",
        "E6x loop markers reset on order transitions; unusual FT2 loop/break combinations may differ.",
        "Development compares complete 4-, 8- and 16-beat passages on a 24-tick beat grid; incomplete tails supply no evidence.",
        "Each voice combines its own transposition-normalized recurrence and absolute-pitch contrast; these are not listener ratings.",
        "Channel/instrument identities and exact duplicate voices are ignored; distinct voices receive equal, not loudness-based, weight.",
        "Exact onset matching can miss expressive timing, and first-note normalization can miss ornamented motif starts.",
        "Through-composed, timbral and envelope-only development can be underestimated; pitches including percussion are treated alike.",
        "Used sample lengths are unique referenced sample lengths at C4, not cumulative playback time.",
    ]
    return {
        **development,
        "sequence_coverage": round(coverage, 6),
        "phrase_rows": PHRASE_ROWS,
        "phrase_count": len(phrases),
        "sequencing_phrases": sequencing_phrases,
        "sequenced_note_ons": event_count,
        "note_ons": event_count,
        "note_ons_per_second": round(event_count / seconds, 6) if seconds else 0.0,
        "channels_used": len(channels),
        "used_channels": sorted(channels),
        "instruments_used": len(used_instruments),
        "used_instruments": used_instruments,
        "used_samples": used_samples,
        "used_sample_seconds_total": round(sum(s["seconds_at_c4"] for s in used_samples), 6),
        "used_longest_sample_seconds": round(max((s["seconds_at_c4"] for s in used_samples), default=0.0), 6),
        "sequence_rows": len(rows),
        "sequence_seconds": round(seconds, 6),
        "reached_orders": sorted(reached),
        "sequence_stop_reason": reason,
        "sequence_complete": reason in ("order_table_end", "repeated_control_state"),
        "sequence_method": "static-xm-control-flow-v1",
        "sequence_warnings": warnings,
        "sequence_limitations": limitations,
    }
