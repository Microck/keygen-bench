"""Content-based XM sequencing evidence; no audio renderer or external dependencies."""
from __future__ import annotations

from collections import Counter, defaultdict
import math

PHRASE_ROWS = 16
MAX_SEQUENCE_ROWS = 65536
MAX_SEQUENCE_EVENTS = 65536


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
    command_phrases = []
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
        if len(rows) % PHRASE_ROWS == 0:
            command_phrases.append(defaultdict(list))
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
                command_phrases[-1][channel].append((len(rows) % PHRASE_ROWS, note))
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
    return rows, samples, active_channels, reached, seconds, reason, sorted(warnings), command_phrases


def structure_metrics(xm: dict, audible_channels: set[int] | None = None) -> dict:
    """Measure recurring sequence content, not pattern/instrument counts.

    Sixteen traversed rows form a phrase, independent of pattern boundaries.
    A motif is four successive notes on one channel: inter-onset row distances,
    pitch intervals, and resolved instrument/sample identities. Transposition
    preserves it. Every pitch, including percussion pitches, is treated alike.
    Motifs need a second non-overlapping occurrence. Complete recurring phrases
    also count, so sparse recurring parts need not contain four notes.

    Optional zero-based audible channels come from auxiliary rendered stems.
    Their filter is applied after traversal, retaining all global commands.

    Coverage = phrases with triggers at >=2 row positions / all phrases.
    Recurrence = fraction of note events covered by recurring motifs/phrases.
    Development = mean event-weighted supported fraction per adjacent active
    phrase pair. A changed channel must share motifs covering >=50% of its own
    events in each phrase; unchanged channels and unsupported changes remain in
    the denominator. Both note commands and audible row/pitch content must
    change; instrument/volume changes alone cannot establish development.
    Exact duplicate full-song channel trajectories receive one scoring vote,
    weighted by their event count, but raw event/channel diagnostics remain.
    Arrangement = coverage * sqrt(recurrence * development).
    """
    rows, used, channels, reached, seconds, reason, warnings, command_phrases = _sequence(xm)
    if audible_channels is not None:
        rows = [tuple(event for event in row if event[0] in audible_channels) for row in rows]
        used = {(event[2], event[3]) for row in rows for event in row}
        channels = {event[0] for row in rows for event in row}
    trajectories = defaultdict(list)
    for row_index, row in enumerate(rows):
        for channel, note, instrument, sample in row:
            trajectories[channel].append((row_index, note, instrument, sample))
    unique_channels = {}
    for channel, trajectory in trajectories.items():
        command_trajectory = tuple(tuple(phrase.get(channel, ())) for phrase in command_phrases)
        unique_channels.setdefault((tuple(trajectory), command_trajectory), channel)
    scoring_channels = set(unique_channels.values())
    phrases = []
    for offset in range(0, len(rows), PHRASE_ROWS):
        events = tuple((r, *event) for r, row in enumerate(rows[offset:offset + PHRASE_ROWS]) for event in row)
        phrases.append(events)
    # Relative pitch per channel makes a transposed phrase the same motif.
    normalized = []
    for events in phrases:
        anchors = {}
        normalized.append(tuple((r, ch, note - anchors.setdefault(ch, note), inst, sample)
                                for r, ch, note, inst, sample in events))
    phrase_counts = Counter(p for p in normalized if p)
    motif_occurrences = defaultdict(list)
    phrase_motifs = [defaultdict(set) for _ in phrases]
    phrase_channels = []
    for phrase_index, events in enumerate(phrases):
        per_channel = defaultdict(list)
        for event_index, event in enumerate(events):
            per_channel[event[1]].append((event_index, event))
        phrase_channels.append(per_channel)
        for channel, notes in per_channel.items():
            for start in range(len(notes) - 3):
                window = notes[start:start + 4]
                first_row, _, first_note, _, _ = window[0][1]
                motif = (channel, tuple((event[0] - first_row, event[2] - first_note, event[3], event[4])
                                        for _, event in window))
                indices = tuple(index for index, _ in window)
                motif_occurrences[motif].append((phrase_index, indices))
                phrase_motifs[phrase_index][motif].update(indices)
    covered = [set() for _ in phrases]
    recurrent_motif_count = 0
    for motif, occurrences in motif_occurrences.items():
        first_phrase, first_indices = occurrences[0]
        # Four-note windows sharing notes do not prove recurrence by themselves.
        if any(p != first_phrase or min(indices) > max(first_indices) for p, indices in occurrences[1:]):
            recurrent_motif_count += 1
            for phrase_index, indices in occurrences:
                covered[phrase_index].update(indices)
    for index, fingerprint in enumerate(normalized):
        if fingerprint and phrase_counts[fingerprint] > 1:
            covered[index].update(range(len(phrases[index])))
    event_count = sum(map(len, phrases))
    scoring_event_count = sum(len(trajectories[channel]) for channel in scoring_channels)
    recurrent_event_count = sum(
        phrases[index][event_index][1] in scoring_channels
        for index, indices in enumerate(covered) for event_index in indices
    )
    recurrence = recurrent_event_count / scoring_event_count if scoring_event_count else 0.0
    sequencing_phrases = sum(len({event[0] for event in events}) >= 2 for events in phrases)
    coverage = sequencing_phrases / len(phrases) if phrases else 0.0
    transitions = development_count = 0
    development_fraction_sum = 0.0
    active_channel_events = changed_channel_events = supported_channel_events = 0
    for index in range(1, len(phrases)):
        previous, current = phrases[index - 1], phrases[index]
        if not previous or not current:
            continue
        transitions += 1
        previous_channels, current_channels = phrase_channels[index - 1:index + 1]
        shared = phrase_motifs[index - 1].keys() & phrase_motifs[index].keys()
        previous_shared, current_shared = defaultdict(set), defaultdict(set)
        for motif in shared:
            channel = motif[0]
            previous_shared[channel].update(phrase_motifs[index - 1][motif])
            current_shared[channel].update(phrase_motifs[index][motif])
        transition_events = transition_supported = 0
        for channel in scoring_channels & (previous_channels.keys() | current_channels.keys()):
            before = previous_channels.get(channel, ())
            after = current_channels.get(channel, ())
            channel_events = len(before) + len(after)
            transition_events += channel_events
            if (command_phrases[index - 1].get(channel, ())
                    == command_phrases[index].get(channel, ())):
                continue
            # Timbre identities still help establish recurrence, but cannot
            # themselves establish melodic/rhythmic development.
            if tuple((event[0], event[2]) for _, event in before) == tuple(
                (event[0], event[2]) for _, event in after
            ):
                continue
            changed_channel_events += channel_events
            if (before and after
                    and len(previous_shared[channel]) >= len(before) / 2
                    and len(current_shared[channel]) >= len(after) / 2):
                transition_supported += channel_events
        active_channel_events += transition_events
        supported_channel_events += transition_supported
        if transition_supported:
            development_count += 1
            development_fraction_sum += transition_supported / transition_events
    development = development_fraction_sum / transitions if transitions else 0.0
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
        "Sixteen-row phrase boundaries and four-note motifs can miss longer, irregular, or continuously developing forms.",
        "Development requires shared four-note motifs on the changed channel covering at least half its events in each adjacent phrase.",
        "Development averages supported-event fractions over active phrase transitions; each denominator includes both phrases' changed and unchanged channel events, including entries/exits.",
        "Development event totals count interior phrases twice; controlled_development is the mean transition fraction, not the ratio of those totals.",
        "Exact duplicate full-song audible event and note-command channel trajectories count once for recurrence and development; raw note/channel/motif counts still include copies.",
        "Duplicate detection retains instrument/sample identities; differently identified sample copies remain distinct.",
        "Note commands are compared before volume gating; instrument/sample index or volume changes alone are not development. Sparse, timbral, or envelope-only development may be missed.",
        "Used sample lengths are unique referenced sample lengths at C4, not cumulative playback time.",
    ]
    return {
        "arrangement_score": round(coverage * math.sqrt(recurrence * development), 6),
        "sequence_coverage": round(coverage, 6),
        "motif_recurrence": round(recurrence, 6),
        "controlled_development": round(development, 6),
        "phrase_rows": PHRASE_ROWS,
        "phrase_count": len(phrases),
        "sequencing_phrases": sequencing_phrases,
        "distinct_phrase_contents": len(set(p for p in phrases if p)),
        "distinct_transposition_normalized_phrases": len(phrase_counts),
        "recurrent_motif_count": recurrent_motif_count,
        "developed_transitions": development_count,
        "active_phrase_transitions": transitions,
        "development_transition_fraction_sum": round(development_fraction_sum, 6),
        "development_active_channel_events": active_channel_events,
        "development_changed_channel_events": changed_channel_events,
        "development_supported_channel_events": supported_channel_events,
        "scoring_note_ons": scoring_event_count,
        "scoring_channels_used": len(scoring_channels),
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
