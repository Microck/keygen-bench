import json
import subprocess

def ft2_call(tool, args):
    cmd = f"ft2 call {tool} '{json.dumps(args)}'"
    subprocess.run(cmd, shell=True, check=True)

def set_note(p, r, c, note, inst, vol=None, fx=None, fxp=None):
    args = {"pattern": p, "row": r, "channel": c, "note": note, "instrument": inst}
    if vol is not None: args["volume"] = vol
    if fx is not None: args["effect"] = fx
    if fxp is not None: args["effect_param"] = fxp
    ft2_call("pattern_set_cell", args)

def drums(p, snare=True, hh=True):
    for r in range(0, 64, 16): 
        set_note(p, r, 0, "C-4", 1) # Kick
    if snare:
        for r in range(16, 64, 32): 
            set_note(p, r, 1, "C-4", 2) # Snare
            if r == 48: # add a little double snare sometimes
                set_note(p, r+12, 1, "C-4", 2, vol=30)
    if hh:
        for r in range(0, 64, 4):
            v = 40 if r % 8 == 4 else 20
            set_note(p, r, 2, "C-4", 3, vol=v)

def bass(p, root="G-2"):
    # Classic tracker bass rhythm: root, skip, root, skip...
    for r in range(0, 64, 8):
        set_note(p, r, 3, root, 5)
        set_note(p, r+4, 3, root, 5, vol=30)

# Pattern 0: Intro (Kick + Arp)
drums(0, snare=False, hh=False)
for r in range(64):
    n = ["G-4", "Bb-4", "D-5", "G-5"][r % 4]
    set_note(0, r, 5, n, 6, vol=30)

# Pattern 1: Intro (Drums + Bass)
drums(1)
bass(1)

# Pattern 2: Main Theme A
drums(2)
bass(2)
# Lead Melody (G minor)
mel = [(0,"G-4"), (4,"Bb-4"), (8,"C-5"), (12,"D-5"), (16,"G-4"), (20,"Bb-4"), (24,"C-5"), (30,"D-5"),
       (32,"F-5"), (36,"D-5"), (40,"C-5"), (44,"Bb-4"), (48,"G-4"), (56,"F-4")]
for r, n in mel: set_note(2, r, 4, n, 4)

# Pattern 3: Main Theme B
drums(3)
bass(3, "Eb-2")
mel_b = [(0,"Eb-5"), (8,"D-5"), (16,"C-5"), (24,"Bb-4"), (32,"G-4"), (40,"Bb-4"), (48,"C-5"), (52,"D-5"), (56,"F-5")]
for r, n in mel_b: set_note(3, r, 4, n, 4)

# Pattern 4: Arp Section
drums(4, snare=True, hh=True)
bass(4, "C-2")
for r in range(64):
    n = ["C-4", "Eb-4", "G-4", "C-5"][r % 4]
    set_note(4, r, 5, n, 6, vol=40)

# Pattern 5: Solo/Breakdown
drums(5, snare=False, hh=True)
bass(5, "G-2")
for r in range(0, 64, 16):
    set_note(5, r, 4, "G-5", 4)
    set_note(5, r+8, 4, "F-5", 4)

# Order
order = [0, 1, 2, 3, 2, 3, 4, 5]
for i, p in enumerate(order):
    ft2_call("order_set", {"position": i, "pattern": p})
ft2_call("song_set", {"length": len(order)})

