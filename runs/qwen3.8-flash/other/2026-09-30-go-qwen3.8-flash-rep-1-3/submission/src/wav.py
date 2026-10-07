import numpy as np, wave, struct, os

def save_wav(path, data, rate=44100):
    """data: float array in -1..1 (mono)"""
    d = np.asarray(data, dtype=np.float64)
    d = np.clip(d, -0.999, 0.999)
    i16 = (d * 32767.0).astype(np.int16)
    w = wave.open(path, 'wb')
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(rate)
    w.writeframes(i16.tobytes())
    w.close()

def load_wav(path):
    w = wave.open(path,'rb')
    n = w.getnframes(); rate = w.getframerate(); sw = w.getsampwidth()
    raw = w.readframes(n)
    if sw == 2:
        a = np.frombuffer(raw, dtype=np.int16).astype(np.float64)/32768.0
    elif sw == 4:
        a = np.frombuffer(raw, dtype=np.int32).astype(np.float64)/2147483648.0
    else:
        a = np.frombuffer(raw, dtype=np.uint8).astype(np.float64)/128.0 - 1.0
    w.close()
    return a, rate
