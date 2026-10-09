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

    def test_short_cycle_cannot_earn_long_scale_development(self):
        notes = [49, 52, 56, 52]
        patterns = [phrase(notes), phrase([note + 5 for note in notes])]
        repeated = structure_metrics(module([patterns[0]], [0] * 8))
        cycle = structure_metrics(module(patterns, [0, 1] * 4))
        self.assertEqual(repeated["arrangement_score"], 0)
        self.assertGreater(cycle["development_scales"][0]["development"], 0)
        self.assertEqual([s["development"] for s in cycle["development_scales"][1:]], [0, 0])
        self.assertLess(cycle["arrangement_score"], 1 / 3)

    def test_related_passages_beat_random_content(self):
        notes = [49, 52, 56, 52, 49, 52, 56, 59]
        related = structure_metrics(module([phrase([n + shift for n in notes])
                                             for shift in (0, 5, 0, 7, 0, 5, 0, 7)]))
        rng = random.Random(27)
        random_content = structure_metrics(module([phrase(rng.sample(range(25, 85), 8)) for _ in range(8)]))
        self.assertGreater(related["arrangement_score"], random_content["arrangement_score"])
        for got in (related, random_content):
            json.dumps(got, allow_nan=False)
            self.assertTrue(math.isfinite(got["arrangement_score"]))
            self.assertGreaterEqual(got["arrangement_score"], 0)
            self.assertLessEqual(got["arrangement_score"], 1)

    def test_sparse_motifs_and_channel_handoffs_retain_credit(self):
        patterns = [phrase([n + shift for n in (49, 52, 56)]) for shift in (0, 5, 0, 7) * 2]
        original = structure_metrics(module(deepcopy(patterns)))
        self.assertGreater(original["arrangement_score"], 0)
        for index, pattern in enumerate(patterns):
            pattern["cells"] = [(row, index % 2, *rest) for row, _, *rest in pattern["cells"]]
        handed = structure_metrics(module(patterns, channels=2))
        # Handoffs inside a longer passage still split sequenced voices; at the
        # complete motif's own scale channel identity must make no difference.
        self.assertEqual(handed["development_scales"][0], original["development_scales"][0])

    def test_repeated_accompaniment_cannot_certify_randomized_lead(self):
        rng = random.Random(41)
        patterns = [phrase(rng.sample(range(25, 85), 8)) for _ in range(8)]
        alone = structure_metrics(module(deepcopy(patterns)))
        for pattern in patterns:
            pattern["cells"].extend(phrase([7] * 16, channel=1)["cells"])
        accompanied = structure_metrics(module(patterns, channels=2))
        self.assertLessEqual(accompanied["arrangement_score"], alone["arrangement_score"])

    def test_accompaniment_note_density_does_not_set_voice_weight(self):
        results = []
        for hits in (4, 16):
            patterns = [phrase([n + shift for n in (49, 52, 56)]) for shift in (0, 5) * 4]
            for pattern in patterns:
                pattern["cells"].extend(phrase([7] * hits, channel=1)["cells"])
            results.append(structure_metrics(module(patterns, channels=2)))
        self.assertEqual(results[0]["arrangement_score"], results[1]["arrangement_score"])

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
            self.assertEqual(got["arrangement_score"], baseline["arrangement_score"])
            self.assertEqual(got["development_scales"], baseline["development_scales"])

    def test_instrument_slots_and_nonzero_volume_are_not_development(self):
        notes = [49, 52, 56, 52, 49, 52, 56, 59]
        original, changed = phrase(notes), phrase(notes, instrument=2)
        changed["cells"] = [(r, ch, n, inst, 0x30, fx, param) for r, ch, n, inst, _, fx, param in changed["cells"]]
        xm = module([original, changed], [0, 1] * 4)
        xm["instruments"].append(deepcopy(xm["instruments"][0]))
        self.assertEqual(structure_metrics(xm)["arrangement_score"], 0)

    def test_beat_grid_is_independent_of_row_density_and_bpm(self):
        xm = module([phrase([n + shift for n in (49, 52, 56)]) for shift in (0, 5, 0, 7) * 2])
        baseline = structure_metrics(xm)
        expanded = deepcopy(xm)
        expanded["speed"] = 3
        expanded["bpm"] = 180
        for pattern in expanded["patterns"]:
            pattern["rows"] *= 2
            pattern["cells"] = [(row * 2, *rest) for row, *rest in pattern["cells"]]
        self.assertEqual(structure_metrics(expanded)["development_scales"], baseline["development_scales"])

    def test_silence_padding_and_incomplete_tail_cannot_add_development(self):
        xm = module([phrase([n + shift for n in (49, 52, 56)]) for shift in (0, 5) * 4])
        baseline = structure_metrics(xm)["arrangement_score"]
        xm["patterns"].append({"rows": 64, "cells": []})
        xm["order"].append(len(xm["patterns"]) - 1)
        xm["song_length"] += 1
        self.assertLessEqual(structure_metrics(xm)["arrangement_score"], baseline)
        short = module([phrase([49, 52], rows=7)])
        self.assertEqual(structure_metrics(short)["arrangement_score"], 0)

    def test_repeating_unrelated_sections_cannot_certify_development(self):
        rng = random.Random(41)
        patterns = [phrase(rng.sample(range(25, 85), 8)) for _ in range(4)]
        repeated = module(patterns, [0, 0, 1, 1, 2, 2, 3, 3])
        self.assertLess(structure_metrics(repeated)["arrangement_score"], 0.05)
        # A different backing channel must not turn an exact melody copy into
        # evidence of a related transformation either.
        repeated["channels"] = 2
        for index, pattern in enumerate(patterns):
            pattern["cells"].extend(phrase([7] * (index + 1), channel=1)["cells"])
        self.assertLess(structure_metrics(repeated)["arrangement_score"], 0.1)

    def test_coalesced_similarity_matches_direct_pairwise_reference(self):
        # Independent, deliberately slow reference for the 4-beat public rule.
        patterns = [phrase([n + shift for n in (49, 52, 56)]) for shift in (0, 5, 0, 7, 0, 5)]
        voices = [set((r * 6, n) for r, _, n, *_ in p["cells"]) for p in patterns]
        shapes = [set((t, p - min(v)[1]) for t, p in v) for v in voices]
        def similarity(left, right):
            return len(left.intersection(right)) / len(left.union(right))
        expected = 0
        for i, voice in enumerate(voices):
            recurrence = max((similarity(shapes[i], shapes[j]) for j in range(len(voices))
                              if voice != voices[j]), default=0.0)
            contrast = sum(1 - similarity(voice, other) for j, other in enumerate(voices) if j != i) / (len(voices) - 1)
            expected += recurrence ** 2 * contrast / len(voices)
        got = structure_metrics(module(patterns))["development_scales"][0]["development"]
        self.assertAlmostEqual(got, expected, places=6)

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
