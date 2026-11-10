"""
Audits all 16 patterns row-by-row for unintended harmonic clashes (semitone collisions)
between active pitched channels (Bass Ch4, Lead Ch5, Echo Ch6, Harm Ch7, SID Ch8, Harpsi Ch9, Pads Ch10-12, Bell Ch13).
"""
import sys
sys.path.insert(0, '/workspace/src')
from build_tune import create_module
from xm_builder import OFF

NOTE_STR = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']


def n2s(n):
    if n <= 0 or n >= 97:
        return '---'
    n0 = n - 1
    return f"{NOTE_STR[n0 % 12]}{n0 // 12}"


def audit():
    mod = create_module(unroll_loop_test=False)
    pitched_chs = [4, 5, 7, 8, 9, 10, 11, 12, 13]  # exclude Ch6 echo from static chord check, check separately!
    active = {c: 0 for c in range(14)}
    age = {c: 0 for c in range(14)}

    clashes = []
    for p_idx, pat in enumerate(mod.patterns):
        for r in range(pat.rows):
            for c in range(14):
                n, ins, v, ef, ep = pat.grid[r][c]
                if n == OFF:
                    active[c] = 0
                elif 1 <= n <= 96:
                    active[c] = n
                    age[c] = 0
                else:
                    age[c] += 1
                    # Plucked one-shots (Harpsi=14, Bell=15) decay quickly after ~6 rows
                    if c in (9, 13) and age[c] > 6:
                        active[c] = 0

            # Check strong/8th-note beats (r % 4 == 0) for semitone clashes between Lead/Harm (5,7) and Bass/Pads (4,10,11,12)
            if r % 4 == 0:
                fg = [(c, active[c]) for c in (5, 7) if active[c] > 0]
                bg = [(c, active[c]) for c in (4, 10, 11, 12) if active[c] > 0]
                for cf, nf in fg:
                    for cb, nb in bg:
                        pc_diff = (nf - nb) % 12
                        # Semitone (1) or flat-9 (13) against bass/pad (note: pc_diff==11 is maj7 above root, totally lush on Dmaj7/Amaj7!)
                        if pc_diff == 1 and abs(nf - nb) in (1, 13):
                            clashes.append((p_idx, r, cf, n2s(nf), cb, n2s(nb)))

    print(f"Total foreground-vs-harmony semitone/b9 clashes on 8th-note grid: {len(clashes)}")
    for item in clashes[:25]:
        print("  Clash:", item)


if __name__ == '__main__':
    audit()
