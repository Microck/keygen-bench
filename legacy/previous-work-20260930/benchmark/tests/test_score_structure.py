"""Consumer contracts for deterministic XM sequence evidence."""
from __future__ import annotations

from copy import deepcopy
import json
import math
import random
import unittest

from benchmark.score_structure import structure_metrics


def sample(seconds=0.1, volume=64):
    return {"frames": max(1, int(seconds * 8363)), "seconds_at_c4": seconds, "volume": volume}


def module(patterns, order=None, channels=1):
    order = list(range(len(patterns))) if order is None else order
    return {"channels": channels, "speed": 6, "bpm": 125, "song_length": len(order),
            "restart": 0, "order": order, "patterns": patterns,
            "instruments": [{"sample_map": [0] * 96, "samples": [sample()]}]}


def phrase(notes, instrument=1, channel=0, rows=16):
    return {"rows": rows, "cells": [(index * rows // len(notes), channel, note, instrument, 0, 0, 0)
                                     for index, note in enumerate(notes)]}


class StructureMetricsTests(unittest.TestCase):
    def test_duplicate_pattern_ids_do_not_change_score(self):
        notes = [49, 52, 56, 52, 49, 52, 56, 59]
        motifs = [phrase(notes), phrase([note + 5 for note in notes])]
        shared = structure_metrics(module(motifs, [0, 1, 0, 1]))
        copied = structure_metrics(module([deepcopy(motifs[index]) for index in (0, 1, 0, 1)]))
        self.assertGreater(shared["arrangement_score"], 0)
        self.assertEqual(shared, copied)

    def test_unused_samples_instruments_and_silent_channels_add_no_credit_or_caps(self):
        xm = module([phrase([49, 52, 56, 52]), phrase([54, 57, 61, 57])], [0, 1, 0, 1])
        baseline = structure_metrics(xm)
        padded = deepcopy(xm)
        padded["instruments"][0]["samples"].append(sample(900))
        padded["instruments"].append({"sample_map": [0] * 96, "samples": [sample(1200, volume=0)]})
        padded["instruments"].append({"sample_map": [0] * 96, "samples": [sample(1800)]})
        padded["channels"] = 2
        for pattern in padded["patterns"]:
            pattern["cells"].extend((row, 1, 60, 2, 0, 0, 0) for row in range(16))
        self.assertEqual(baseline, structure_metrics(padded))

    def test_excluded_pcm_silent_channel_cannot_add_recurrence_or_samples(self):
        rng = random.Random(41)
        xm = module([phrase(rng.sample(range(25, 85), 8)) for _ in range(4)])
        baseline = structure_metrics(xm, {0})
        padded = deepcopy(xm)
        padded["channels"] = 2
        padded["instruments"].append({"sample_map": [0] * 96, "samples": [sample(900)]})
        for pattern in padded["patterns"]:
            pattern["cells"].extend((row, 1, 49, 2, 0, 0, 0) for row in range(0, 16, 2))
        self.assertEqual(structure_metrics(padded, {0}), baseline)
        excluded = structure_metrics(padded, set())
        self.assertEqual(excluded["arrangement_score"], 0)
        self.assertEqual(excluded["used_samples"], [])
        self.assertEqual(excluded["note_ons"], 0)

    def test_excluded_channel_still_controls_global_tempo(self):
        xm = module([phrase([49, 52, 56, 59])], channels=2)
        xm["patterns"][0]["cells"].append((0, 1, 0, 0, 0, 0xF, 100))
        got = structure_metrics(xm, {0})
        self.assertEqual(got["sequence_seconds"], 2.4)
        self.assertEqual(got["note_ons"], 4)
        self.assertAlmostEqual(got["note_ons_per_second"], 4 / 2.4, places=6)

    def test_sample_map_and_instrument_memory_choose_only_played_samples(self):
        xm = module([{"rows": 16, "cells": [(0, 0, 49, 1, 0, 0, 0),
                                               (4, 0, 53, 0, 0, 0, 0),
                                               (8, 0, 97, 0, 0, 0, 0),
                                               (12, 0, 49, 0, 0, 0, 0)]}])
        xm["instruments"][0]["samples"] = [sample(0.2), sample(0.4), sample(900)]
        xm["instruments"][0]["sample_map"][48] = 1
        got = structure_metrics(xm)
        self.assertEqual(got["used_instruments"], [1])
        self.assertEqual([(s["instrument"], s["sample"]) for s in got["used_samples"]], [(1, 0), (1, 1)])
        self.assertAlmostEqual(got["used_sample_seconds_total"], 0.6)
        self.assertAlmostEqual(got["used_longest_sample_seconds"], 0.4)
        self.assertEqual(got["sequenced_note_ons"], 3)

    def test_portamento_sequences_pitch_without_starting_target_sample(self):
        xm = module([{"rows": 16, "cells": [(0, 0, 49, 1, 0, 0, 0),
                                            (4, 0, 53, 0, 0, 3, 4),
                                            (8, 0, 56, 0, 0, 3, 4)]}])
        xm["instruments"][0]["samples"].append(sample(900))
        xm["instruments"][0]["sample_map"][52] = 1
        xm["instruments"][0]["sample_map"][55] = 1
        got = structure_metrics(xm)
        self.assertEqual(got["sequenced_note_ons"], 3)
        self.assertEqual(got["sequence_coverage"], 1)
        self.assertEqual(got["used_longest_sample_seconds"], 0.1)

    def test_repeated_and_transposed_motifs_beat_scrambled_notes(self):
        notes = [49, 52, 56, 52, 49, 52, 56, 59]
        repeated = structure_metrics(module([phrase(notes)], [0] * 8))
        developed = structure_metrics(module([phrase([note + transpose for note in notes])
                                              for transpose in (0, 5, 0, 7, 0, 5, 0, 7)]))
        rng = random.Random(27)
        scrambled = structure_metrics(module([phrase(rng.sample(range(25, 85), 8)) for _ in range(8)]))
        self.assertGreater(repeated["motif_recurrence"], scrambled["motif_recurrence"])
        self.assertEqual(repeated["controlled_development"], 0)
        self.assertEqual(repeated["arrangement_score"], 0)
        self.assertGreater(developed["arrangement_score"], scrambled["arrangement_score"])
        self.assertGreater(developed["arrangement_score"], repeated["arrangement_score"])
        self.assertEqual(developed["controlled_development"], 1.0)
        self.assertEqual(developed["distinct_transposition_normalized_phrases"], 1)
        for got in (repeated, developed, scrambled):
            json.dumps(got, allow_nan=False)
            self.assertTrue(math.isfinite(got["arrangement_score"]))
            self.assertGreaterEqual(got["arrangement_score"], 0)
            self.assertLessEqual(got["arrangement_score"], 1)

    def test_pitch_class_and_percussion_are_not_penalized(self):
        pitched = structure_metrics(module([phrase([49] * 8)], [0, 0]))
        percussion = structure_metrics(module([phrase([7] * 8)], [0, 0]))
        self.assertEqual(pitched["arrangement_score"], percussion["arrangement_score"])
        self.assertEqual(pitched["motif_recurrence"], percussion["motif_recurrence"])
        self.assertGreater(percussion["motif_recurrence"], 0)

    def test_rhythmic_development_does_not_depend_on_pitch_number(self):
        scores = []
        for note in (7, 49):
            first = phrase([note] * 8)
            second = deepcopy(first)
            second["cells"] = [(row + (row >= 8), *rest)
                               for row, *rest in second["cells"]]
            scores.append(structure_metrics(module([first, second])))
        self.assertGreater(scores[0]["arrangement_score"], 0)
        self.assertEqual(scores[0]["arrangement_score"], scores[1]["arrangement_score"])

    def test_repeated_accompaniment_cannot_certify_randomized_lead(self):
        rng = random.Random(41)
        patterns = [phrase(rng.sample(range(25, 85), 8)) for _ in range(8)]
        alone = structure_metrics(module(deepcopy(patterns)))
        for pattern in patterns:
            pattern["cells"].extend(phrase([7] * 16, channel=1)["cells"])
        accompanied = structure_metrics(module(patterns, channels=2))
        self.assertGreater(accompanied["motif_recurrence"], alone["motif_recurrence"])
        for got in (alone, accompanied):
            self.assertEqual(got["controlled_development"], 0)
            self.assertEqual(got["developed_transitions"], 0)
            self.assertEqual(got["arrangement_score"], 0)

    def test_independently_recurring_unrelated_pitches_are_not_development(self):
        first = phrase([49, 52, 56, 52, 49, 52, 56, 59])
        unrelated = phrase([31, 78, 44, 68, 53, 29, 83, 37])
        got = structure_metrics(module([first, unrelated], [0, 0, 1, 1, 0, 0, 1, 1]))
        self.assertEqual(got["motif_recurrence"], 1)
        self.assertEqual(got["controlled_development"], 0)
        self.assertEqual(got["arrangement_score"], 0)

    def test_retained_motif_supports_changed_melody(self):
        original = phrase([49, 52, 56, 52, 49, 52, 56, 59])
        transformed = phrase([49, 52, 56, 52, 58, 61, 65, 61])
        repeated = structure_metrics(module([original], [0, 0]))
        developed = structure_metrics(module([original, transformed]))
        self.assertGreater(developed["controlled_development"], repeated["controlled_development"])
        self.assertGreater(developed["arrangement_score"], repeated["arrangement_score"])
        self.assertEqual(developed["developed_transitions"], 1)
        self.assertEqual(developed["development_supported_channel_events"],
                         developed["development_active_channel_events"])

    def test_shared_motif_must_cover_half_of_each_changed_channel_phrase(self):
        first = [49, 52, 56, 52, 27, 85, 33, 76]
        second = [49, 52, 56, 52, 82, 31, 73, 42, 65]
        patterns = [{"rows": 16, "cells": [(row, 0, note, 1, 0, 0, 0)
                                          for row, note in enumerate(notes)]}
                    for notes in (first, second)]
        for order in ([0, 1], [1, 0]):
            with self.subTest(order=order):
                got = structure_metrics(module(patterns, order))
                self.assertGreater(got["motif_recurrence"], 0)
                self.assertEqual(got["controlled_development"], 0)

    def test_supported_development_is_weighted_against_unchanged_events(self):
        patterns = [phrase(notes) for notes in ([49, 52, 56, 52], [54, 57, 61, 57])]
        melody = structure_metrics(module(deepcopy(patterns)))
        for pattern in patterns:
            pattern["cells"].extend(phrase([7] * 16, channel=1)["cells"])
        accompanied = structure_metrics(module(patterns, channels=2))
        self.assertEqual(accompanied["developed_transitions"], melody["developed_transitions"])
        self.assertEqual(accompanied["development_supported_channel_events"],
                         melody["development_supported_channel_events"])
        self.assertEqual(accompanied["development_active_channel_events"],
                         melody["development_active_channel_events"] * 5)
        self.assertAlmostEqual(accompanied["controlled_development"],
                               melody["controlled_development"] / 5)
        self.assertLess(accompanied["arrangement_score"], melody["arrangement_score"])

    def test_development_averages_transition_fractions_including_channel_entries(self):
        notes = [49, 52, 56, 52]
        patterns = [phrase([note + shift for note in notes]) for shift in (0, 5, 7)]
        for pattern in patterns[1:]:
            pattern["cells"].extend(phrase([7] * 16, channel=1)["cells"])
        got = structure_metrics(module(patterns, channels=2))
        # First transition includes one drum phrase; the second includes two.
        expected = (8 / (8 + 16) + 8 / (8 + 32)) / 2
        self.assertAlmostEqual(got["controlled_development"], expected, places=6)
        self.assertEqual(got["active_phrase_transitions"], 2)
        self.assertEqual(got["developed_transitions"], 2)
        self.assertEqual(got["development_supported_channel_events"], 16)
        self.assertEqual(got["development_active_channel_events"], 64)

    def test_duplicate_channels_and_channel_permutation_do_not_buy_score(self):
        patterns = [phrase(notes) for notes in ([49, 52, 56, 52], [54, 57, 61, 57])]
        for pattern in patterns:
            pattern["cells"].extend(phrase([7] * 16, channel=1)["cells"])
        xm = module(patterns, channels=2)
        baseline = structure_metrics(xm)
        duplicated = deepcopy(xm)
        duplicated["channels"] = 3
        for pattern in duplicated["patterns"]:
            pattern["cells"].extend((row, 2, *rest) for row, channel, *rest in list(pattern["cells"])
                                    if channel == 0)
        permuted = deepcopy(duplicated)
        for pattern in permuted["patterns"]:
            pattern["cells"] = [(row, 2 - channel, *rest)
                                for row, channel, *rest in reversed(pattern["cells"])]
        for candidate in (duplicated, permuted):
            got = structure_metrics(candidate)
            self.assertGreater(got["note_ons"], baseline["note_ons"])
            for key in ("arrangement_score", "motif_recurrence", "controlled_development",
                        "development_supported_channel_events", "development_active_channel_events",
                        "scoring_note_ons", "scoring_channels_used"):
                self.assertEqual(got[key], baseline[key], key)

    def test_instrument_indices_and_volume_alone_are_not_development(self):
        notes = [49, 52, 56, 52, 49, 52, 56, 59]
        for changed_instrument, volume in ((False, 0x10), (False, 0x30), (True, 0x30)):
            with self.subTest(changed_instrument=changed_instrument, volume=volume):
                original, changed = phrase(notes), phrase(notes)
                changed["cells"] = [
                    (row, channel, note, 2 if changed_instrument and row >= 8 else inst,
                     volume if row >= 8 else 0x50, effect, param)
                    for row, channel, note, inst, _, effect, param in changed["cells"]
                ]
                xm = module([original, changed], [0, 1, 0, 1])
                xm["instruments"].append(deepcopy(xm["instruments"][0]))
                got = structure_metrics(xm)
                self.assertGreater(got["motif_recurrence"], 0)
                self.assertEqual(got["development_changed_channel_events"], 0)
                self.assertEqual(got["controlled_development"], 0)
                self.assertEqual(got["arrangement_score"], 0)

    def test_jump_excludes_unreachable_long_sample(self):
        xm = module([{"rows": 16, "cells": [(0, 0, 49, 1, 0, 0xB, 2)]},
                     phrase([49, 52, 56, 52], instrument=2), phrase([49, 52, 56, 52])])
        xm["instruments"].append({"sample_map": [0] * 96, "samples": [sample(900)]})
        got = structure_metrics(xm)
        self.assertEqual(got["reached_orders"], [0, 2])
        self.assertEqual(got["sequence_rows"], 17)
        self.assertEqual(got["used_instruments"], [1])
        self.assertEqual(got["used_longest_sample_seconds"], 0.1)
        self.assertEqual(got["note_ons"], 5)
        self.assertAlmostEqual(got["note_ons_per_second"], 5 / (17 * 0.12), places=6)

    def test_pattern_loop_tempo_and_delay_affect_traversed_time(self):
        xm = module([{"rows": 4, "cells": [(0, 0, 49, 1, 0, 0xE, 0x60),
                                            (1, 0, 52, 0, 0, 0xE, 0x62),
                                            (2, 0, 56, 0, 0, 0xF, 3),
                                            (3, 0, 59, 0, 0, 0xE, 0xE2)]}])
        got = structure_metrics(xm)
        self.assertEqual(got["sequence_rows"], 8)
        self.assertEqual(got["sequenced_note_ons"], 8)
        self.assertAlmostEqual(got["sequence_seconds"], 6 * 0.12 + 0.06 + 3 * 0.06)
        self.assertEqual(got["sequence_stop_reason"], "order_table_end")

    def test_bcd_pattern_break_skips_initial_rows(self):
        xm = module([{"rows": 32, "cells": [(0, 0, 0, 0, 0, 0xD, 0x12)]},
                     {"rows": 16, "cells": [(0, 0, 49, 2, 0, 0, 0), (12, 0, 49, 1, 0, 0, 0)]}])
        xm["instruments"].append({"sample_map": [0] * 96, "samples": [sample(900)]})
        got = structure_metrics(xm)
        self.assertEqual(got["sequence_rows"], 5)
        self.assertEqual(got["used_instruments"], [1])

    def test_backward_jump_terminates_at_repeated_control_state(self):
        xm = module([{"rows": 16, "cells": [(0, 0, 49, 1, 0, 0, 0),
                                             (3, 0, 52, 0, 0, 0xB, 0)]}])
        got = structure_metrics(xm)
        self.assertEqual(got["sequence_rows"], 4)
        self.assertEqual(got["sequence_stop_reason"], "repeated_control_state")
        self.assertTrue(got["sequence_complete"])

    def test_silence_and_single_baked_trigger_have_no_sequence_coverage(self):
        silent = structure_metrics(module([{"rows": 32, "cells": []}]))
        baked = structure_metrics(module([phrase([49], rows=64)]))
        for got in (silent, baked):
            self.assertEqual(got["sequence_coverage"], 0)
            self.assertEqual(got["arrangement_score"], 0)
        self.assertEqual(silent["used_sample_seconds_total"], 0)
        self.assertEqual(silent["used_channels"], [])

    def test_invalid_order_is_reported_not_presented_as_complete(self):
        got = structure_metrics(module([], [9]))
        self.assertFalse(got["sequence_complete"])
        self.assertEqual(got["sequence_stop_reason"], "invalid_pattern_reference")
        self.assertEqual(got["arrangement_score"], 0)


if __name__ == "__main__":
    unittest.main()
