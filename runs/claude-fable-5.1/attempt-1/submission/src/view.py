import sys
sys.argv = ['x']
src = open('/workspace/src/compose.py').read().split('# ---------------------------------------------------------------- emit tool calls')[0]
exec(src)
NAMES = ["C-","C#","D-","D#","E-","F-","F#","G-","G#","A-","A#","B-"]
def nn(n):
    if n == 97: return "off"
    n -= 1; return f"{NAMES[n%12]}{n//12}"
CH = ["KICK","SNAR","HAT ","BASS","ARP ","LEAD","ECHO","PADL","PADR","ARP2","FX  ","ECH2","CRSH","HARM"]
def show(pi, chans, rows=range(64)):
    p = patterns[pi]
    print(f"=== pattern {pi} ===")
    print("    " + " | ".join(f"{CH[c]:^12s}" for c in chans))
    for r in rows:
        line = f"{r:02d}  "
        for c in chans:
            cell = p.get(r, c)
            n = nn(cell["note"]) if "note" in cell else "..."
            i = f"{cell['instrument']:02d}" if "instrument" in cell else ".."
            v = f"{cell['volume']:02X}" if "volume" in cell else ".."
            fx = f"{cell['effect']:X}{cell['effect_param']:02X}" if "effect" in cell else "..."
            line += f"{n} {i} {v} {fx} | "
        print(line)
if __name__ == "__main__":
    pi = int(sys.argv[1]) if len(sys.argv) > 1 else 2
