"""
Deep Symbolic Harmony Scanner + Waveform Click/Discontinuity + Tempo Autocorrelation Audit
"""
import sys
import wave
import numpy as np

sys.path.insert(0, "/workspace/src")
from build_tune import assemble_song
from tracker_helpers import SEMI_TO_STR


def pc_name(n):
    return SEMI_TO_STR[(n - 1) % 12].rstrip("-")


def run_harmonic_audit(song: dict):
    """
    Simulate exact active pitched notes per row across all 20 patterns
    and flag any sustained (>=2 rows) harsh b9 (13 semitones mod 12 == 1 and >octave)
    against Bass (Ch 3) or between Lead 1 (Ch 4) and Lead 2 (Ch 5)!
    """
    pats = song["patterns"]
    insts = song["instruments"]
    pitched_insts = {9, 10, 11, 12, 13, 14, 15, 16}

    state_note = [0] * 12
    state_inst = [0] * 12
    state_age  = [0] * 12

    lead_clashes = []
    bass_b9_clashes = []

    for p_idx, pat in enumerate(pats):
        for r in range(pat.rows):
            for ch in range(12):
                n, ins, v, ef, pr = pat.cells[r][ch]
                if n == 97:
                    state_note[ch] = 0
                    state_inst[ch] = 0
                    state_age[ch] = 0
                elif 1 <= n <= 96:
                    state_note[ch] = n
                    if ins != 0:
                        state_inst[ch] = ins
                    state_age[ch] = 0
                    if ef == 14 and (pr >> 4) == 0xC:
                        # Cut within this row
                        pass
                else:
                    state_age[ch] += 1
                    # One-shot instruments decay quickly (Bell ~5 rows, Stab ~2.5 rows)
                    if state_inst[ch] == 16 and state_age[ch] >= 3:
                        state_note[ch] = 0
                    elif state_inst[ch] == 14 and state_age[ch] >= 5:
                        state_note[ch] = 0
                    elif state_inst[ch] not in pitched_insts:
                        state_note[ch] = 0

            # Check Lead 1 (Ch 4) vs Lead 2 (Ch 5) when BOTH are full-volume leads (not quiet echo!)
            n4, n5 = state_note[4], state_note[5]
            if n4 > 0 and n5 > 0 and state_inst[5] == 12:
                iv = abs(n4 - n5) % 12
                if iv in (1, 6):  # semitone or tritone between twin leads!
                    lead_clashes.append((p_idx, r, n4, n5, iv))

            # Check Bass (Ch 3) vs Leads (Ch 4, 5) for harsh minor 9th (n_lead - n_bass) % 12 == 1
            nb = state_note[3]
            if nb > 0:
                for lch in (4, 5):
                    nl = state_note[lch]
                    if nl > 0 and state_inst[lch] in (11, 12):
                        if (nl - nb) % 12 == 1:
                            bass_b9_clashes.append((p_idx, r, nb, lch, nl))

    print("=== SYMBOLIC COUNTERPOINT & HARMONY AUDIT ===")
    print(f"  Twin-Lead (Ch4 vs Ch5 SyncShred) semitone/tritone rows : {len(lead_clashes)}")
    for p_i, r_i, n4, n5, iv in lead_clashes[:15]:
        print(f"    Pos {p_i:02d} Row {r_i:02d}: L1={pc_name(n4)}{(n4-1)//12} vs L2={pc_name(n5)}{(n5-1)//12} (interval mod 12 = {iv})")

    print(f"  Bass vs Lead minor-9th (b9) rows (check if passing/b9 chord or clash): {len(bass_b9_clashes)}")
    for p_i, r_i, nb, lch, nl in bass_b9_clashes[:20]:
        print(f"    Pos {p_i:02d} Row {r_i:02d}: Bass={pc_name(nb)}{(nb-1)//12} vs Ch{lch}={pc_name(nl)}{(nl-1)//12}")


def run_waveform_and_groove_audit(wav_path: str):
    with wave.open(wav_path, "rb") as wf:
        sr = wf.getframerate()
        pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).reshape(-1, 2)
    flt = pcm.astype(np.float64) / 32768.0

    # 1. Second-difference click detector
    d2 = np.max(np.abs(np.diff(flt, n=2, axis=0)), axis=1)
    p9999 = np.percentile(d2, 99.99)
    max_d2 = np.max(d2)
    max_d2_idx = int(np.argmax(d2))
    print("\n=== WAVEFORM CONTINUITY & MICRO-CLICK AUDIT ===")
    print(f"  99.99th pct |d2x/dt2| : {p9999:.4f}  | Global max |d2x/dt2| : {max_d2:.4f} at t={max_d2_idx/sr:.3f}s (Pos {max_d2_idx//(4560*64):02d})")

    # 2. Tempo / Beat Onset Autocorrelation
    hop = 256
    mono = 0.5 * (flt[:, 0] + flt[:, 1])
    n_hops = len(mono) // hop
    env = np.sqrt(np.mean(mono[:n_hops * hop].reshape(n_hops, hop) ** 2, axis=1))
    onset = np.maximum(0.0, np.diff(env))
    onset -= np.mean(onset)
    ac = np.correlate(onset, onset, mode="full")[len(onset) - 1 :]
    ac /= max(ac[0], 1e-12)
    # Search around 100..180 BPM
    lag_min = int((60.0 / 180.0) * sr / hop)
    lag_max = int((60.0 / 100.0) * sr / hop)
    best_lag = lag_min + int(np.argmax(ac[lag_min:lag_max]))
    detected_bpm = 60.0 / (best_lag * hop / sr)
    print("\n=== RHYTHMIC GROOVE & TEMPO LOCK AUDIT ===")
    print(f"  Detected Beat Pulse BPM : {detected_bpm:.2f} BPM (target 145.00 BPM), beat autocorr strength = {ac[best_lag]:.3f}")


if __name__ == "__main__":
    song = assemble_song()
    run_harmonic_audit(song)
    run_waveform_and_groove_audit("/workspace/build/render.wav")
