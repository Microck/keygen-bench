"""
Master builder for 'Cybernetic Fugue' (/workspace/submission/tune.xm)
"""
import sys
import os

sys.path.insert(0, "/workspace/src")
from synth import build_all_instruments
from xm_builder import build_and_render, write_xm, ft2_call
from sections_ab import build_patterns_00_to_09
from sections_cd import build_patterns_10_to_19
from tracker_helpers import CH_LEAD2, I_LEAD2


def assemble_song():
    insts = build_all_instruments()
    pats = build_patterns_00_to_09() + build_patterns_10_to_19()

    # Ensure Pos 02 Row 0 resolves Ch 5 (Lead 2) cleanly from both Pos 01 and Pos 19!
    pats[2].set(0, CH_LEAD2, "A-5", I_LEAD2, 48, 14, 0xC4)
    pats[2].set(2, CH_LEAD2, "off")

    orders = list(range(20))
    loop_start = 2  # Seamless loop back to Pos 02 (Main Keygen Hook Drop!)
    return {
        "song_name": "Cybernetic Fugue",
        "channels": 12,
        "bpm": 145,
        "speed": 6,
        "orders": orders,
        "loop_start": loop_start,
        "patterns": pats,
        "instruments": insts,
    }


def main():
    song = assemble_song()
    res = build_and_render(
        raw_xm_path="/workspace/build/tune_raw.xm",
        final_xm_path="/workspace/submission/tune.xm",
        wav_path="/workspace/build/render.wav",
        **song,
    )
    print("Built /workspace/submission/tune.xm:")
    print("  module_info:", res["module_info"]["content"][0]["text"])
    print("  render_info:", res["render_info"]["content"][0]["text"])

    # Also render a dedicated seamless loop-transition verification WAV:
    # Order = [18, 19, 2, 3] so we can inspect the exact Pos 19 -> Pos 02 loop seam!
    write_xm(
        "/workspace/build/loop_test.xm",
        "LoopSeamCheck",
        song["channels"], song["bpm"], song["speed"],
        [18, 19, 2, 3], 0,
        song["patterns"], song["instruments"]
    )
    ft2_call("module_load", {"path": "/workspace/build/loop_test.xm"})
    ft2_call("module_render", {"path": "/workspace/build/loop_test.wav", "rate": 44100, "bits": 16})
    # Restore final submission module in FT2 persistent session!
    ft2_call("module_load", {"path": "/workspace/submission/tune.xm"})
    print("Restored /workspace/submission/tune.xm in active FT2 session.")


if __name__ == "__main__":
    main()
