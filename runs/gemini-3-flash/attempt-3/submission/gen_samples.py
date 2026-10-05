import numpy as np
import wave
import struct

def save_wav(filename, data, rate=44100):
    with wave.open(filename, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes((data * 32767).astype(np.int16).tobytes())

rate = 44100

# Kick: Pitch down sine sweep
t_kick = np.linspace(0, 0.1, int(rate * 0.1))
kick = np.sin(2 * np.pi * 150 * np.exp(-t_kick * 30)) * np.exp(-t_kick * 20)
save_wav('kick.wav', kick)

# Snare: Noise with decay
t_snare = np.linspace(0, 0.15, int(rate * 0.15))
snare = (np.random.rand(len(t_snare)) * 2 - 1) * np.exp(-t_snare * 30)
save_wav('snare.wav', snare)

# Hi-hat: Short noise
t_hh = np.linspace(0, 0.05, int(rate * 0.05))
hh = (np.random.rand(len(t_hh)) * 2 - 1) * np.exp(-t_hh * 100)
save_wav('hh.wav', hh)

# Square Wave: For lead (loopable)
t_square = np.linspace(0, 1/440, int(rate/440), endpoint=False)
square = np.sign(np.sin(2 * np.pi * 440 * t_square))
save_wav('square.xml_ready.wav', square) # Will need to set loop

# Pulse Wave: 25% duty cycle
pulse = np.where((t_square * 440) % 1.0 < 0.25, 1.0, -1.0)
save_wav('pulse.wav', pulse)

# Triangle Wave
triangle = 2 * np.abs(2 * (t_square * 440 - np.floor(t_square * 440 + 0.5))) - 1
save_wav('triangle.wav', triangle)

