import numpy as np
import base64
import json

def make_pcm(data):
    # Reduce volume by a factor of 4 in the raw sample data to prevent clipping
    data = (data * 0.25)
    data = np.clip(data, -1.0, 1.0).astype(np.float32)
    return base64.b64encode(data.tobytes()).decode('ascii')

sr = 8363

t = np.linspace(0, 0.2, int(0.2*sr), endpoint=False)
env = np.exp(-t * 20)
phase = np.cumsum(2 * np.pi * (50 + 100 * np.exp(-t * 50)) / sr)
kick = np.sin(phase) * env

t = np.linspace(0, 0.25, int(0.25*sr), endpoint=False)
env = np.exp(-t * 15)
noise = np.random.uniform(-1, 1, len(t))
phase = np.cumsum(2 * np.pi * (200 + 100 * np.exp(-t * 30)) / sr)
tone = np.sin(phase) * env
snare = (noise * 0.7 + tone * 0.3) * env

t = np.linspace(0, 0.05, int(0.05*sr), endpoint=False)
env = np.exp(-t * 60)
noise = np.random.uniform(-1, 1, len(t))
hihat = noise * env

pulse25 = np.ones(32)
pulse25[8:] = -1
pulse25 = pulse25 - np.mean(pulse25)

square = np.ones(32)
square[16:] = -1

triangle = np.concatenate([np.linspace(-1, 1, 16, endpoint=False), np.linspace(1, -1, 16, endpoint=False)])

saw = np.linspace(1, -1, 32, endpoint=False)

instruments = [
    {"name": "Kick", "data": kick, "loop": False, "vol": 64},
    {"name": "Snare", "data": snare, "loop": False, "vol": 64},
    {"name": "Hihat", "data": hihat, "loop": False, "vol": 64},
    {"name": "Bass", "data": pulse25, "loop": True, "vol": 48},
    {"name": "Lead", "data": square, "loop": True, "vol": 48},
    {"name": "Arp", "data": triangle, "loop": True, "vol": 32},
    {"name": "Saw", "data": saw, "loop": True, "vol": 32}
]

script = [
    {"name": "module_new", "arguments": {"channels": 10}},
    {"name": "song_set", "arguments": {"bpm": 140, "speed": 3, "name": "Keygen Magic", "length": 8, "loop_start": 0}}
]

for i, inst in enumerate(instruments):
    inst_idx = i + 1
    script.append({"name": "instrument_set", "arguments": {"instrument": inst_idx, "name": inst["name"]}})
    pcm_b64 = make_pcm(inst["data"])
    script.append({"name": "sample_create_from_pcm", "arguments": {"instrument": inst_idx, "sample": 0, "pcm": pcm_b64, "encoding": "float32", "name": inst["name"]}})
    
    flags = 1 if inst["loop"] else 0
    loop_length = len(inst["data"]) if inst["loop"] else 0
    script.append({"name": "sample_set", "arguments": {
        "instrument": inst_idx, 
        "sample": 0, 
        "volume": inst["vol"], 
        "loop_start": 0, 
        "loop_length": loop_length, 
        "flags": flags
    }})

with open('setup.json', 'w') as f:
    json.dump(script, f, indent=2)
