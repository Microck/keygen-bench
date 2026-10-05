import json, subprocess, base64, math
import numpy as np

def run_batch(calls, path="/tmp/_batch.json"):
    with open(path, "w") as f:
        json.dump(calls, f)
    out = subprocess.run(["ft2", "batch", path], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError("ft2 batch failed: " + out.stdout + out.stderr)
    lines = out.stdout.strip().splitlines()
    results = []
    for ln in lines:
        try:
            results.append(json.loads(ln))
        except Exception:
            results.append(ln)
    return results

def call(name, args):
    out = subprocess.run(["ft2", "call", name, json.dumps(args)], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError("ft2 call failed: " + out.stdout + out.stderr)
    return out.stdout.strip()

def pcm_b64_int16(arr):
    arr = np.clip(arr, -32768, 32767).astype('<i2')
    return base64.b64encode(arr.tobytes()).decode()

BASE_RATE = 8363.0
REF_C4 = 261.625565  # MIDI 60

def xm_note_from_midi(midi):
    return midi - 60 + 49

def calibrate(cycle_length, base_rate=BASE_RATE, ref=REF_C4):
    """Return (relative_note, finetune) so that XM note49 (our C-4) plays `ref` Hz
    for a sample whose one-cycle loop length is cycle_length samples, assuming
    native engine reference: note49/relnote0/finetune0 reads sample at base_rate sps."""
    f_exact = base_rate / cycle_length
    delta = 12.0 * math.log2(ref / f_exact)
    rel = round(delta)
    fine = round((delta - rel) * 128)
    if fine > 127:
        fine -= 128; rel += 1
    if fine < -128:
        fine += 128; rel -= 1
    return int(rel), int(fine)

def freq_of_midi(midi):
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))

def find_best_length(lo, hi, ref=REF_C4, base_rate=BASE_RATE):
    """Search integer cycle lengths in [lo,hi] for the one whose rel-note
    (with finetune fixed at 0) comes closest to aligning note49 exactly to `ref`.
    Returns (length, relative_note, cents_error)."""
    best = None
    for L in range(lo, hi + 1):
        f_exact = base_rate / L
        delta = 12.0 * math.log2(ref / f_exact)
        rel = round(delta)
        frac = delta - rel
        cents = frac * 100.0
        if best is None or abs(cents) < abs(best[2]):
            best = (L, int(rel), cents)
    return best

SR_DRUM = BASE_RATE * 4.0   # native playback rate when relative_note=24, finetune=0
REL_DRUM = 24

def sample_calls(instrument, pcm_array, name, cycle_length=None, relative_note=0,
                  finetune=0, loop=False, volume=64, panning=128, rate=44100,
                  tmpdir="/tmp/_samples"):
    """Build the (load/meta/name) call sequence for one sample, going
    through a temp WAV file + sample_load so large arrays never hit the
    inline JSON size limit."""
    import os, wave as _wave
    os.makedirs(tmpdir, exist_ok=True)
    safe = "".join(c if c.isalnum() else "_" for c in name)
    path = os.path.join(tmpdir, f"i{instrument}_{safe}.wav")
    arr = np.clip(pcm_array, -32768, 32767).astype('<i2')
    w = _wave.open(path, 'wb')
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(int(rate))
    w.writeframes(arr.tobytes())
    w.close()
    length = len(arr)
    loop_len = cycle_length if loop else 0
    flags = (17 if loop else 16)
    return [
        {"name": "sample_load", "arguments": {
            "path": path, "instrument": instrument, "sample": 0}},
        {"name": "sample_set", "arguments": {
            "instrument": instrument, "sample": 0, "name": name,
            "volume": volume, "panning": panning,
            "finetune": int(finetune), "relative_note": int(relative_note),
            "loop_start": 0, "loop_length": int(loop_len), "flags": flags}},
        {"name": "instrument_set", "arguments": {"instrument": instrument, "name": name}},
    ]
