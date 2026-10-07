import numpy as np, wave, subprocess, os, sys
names = ["KICK","SNARE","HAT","BASS","ARP","LEAD","ECHO","PADL","PADR","ARP2","FX","ECHO2","CRASH","HARM"]
regions = {"intro": (0, 12.8), "verse": (12.8, 38.4), "chorus": (38.4, 51.2), "break": (51.2, 64.0), "chorus2": (64.0, 76.8), "post": (76.8, 83.2)}
rows = []
for ch in range(14):
    env = dict(os.environ, ONLY_CH=str(ch), RENDER_PATH=f"/workspace/ch_{ch}.wav", SAVE_PATH="/workspace/ch_tmp.xm")
    subprocess.run(["python3", "src/compose.py"], env=env, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["ft2", "batch", "build.json"], check=True, stdout=subprocess.DEVNULL)
    w = wave.open(f"/workspace/ch_{ch}.wav", "rb"); d = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, 2).astype(float)
    line = f"{names[ch]:6s} peak={np.abs(d).max():6.0f} |"
    for r, (a, b) in regions.items():
        seg = d[int(a * 44100):int(b * 44100)]
        rms = np.sqrt(np.mean(seg ** 2))
        line += f" {r}={20*np.log10(rms/32768+1e-9):6.1f}"
    print(line)
