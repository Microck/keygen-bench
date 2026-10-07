"""XM module builder matching the FT2 clone's binary format."""
import struct
import numpy as np

NOTE_NAMES = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']

def note_name(n):
    if n is None or n <= 0 or n > 96: return None
    return f"{NOTE_NAMES[(n-1)%12]}{(n-1)//12}"

def name_to_note(s):
    s = s.strip().upper()
    if s in ('---','OFF'): return 97
    if s == '...': return 0
    base = s[:2]
    idx = NOTE_NAMES.index(base)
    octv = int(s[2:])
    return idx + 1 + octv*12

SR = 8363  # Create samples at the C-4 playback rate so envelope times are correct
R_BASE = 8363.0   # FT2 playback rate for C-4 (XM note 49)
C4_HZ = 261.625565  # musical frequency of middle C (C-4)

def freq_of(note):
    """Musical frequency (Hz) of XM note number. C-4 = note 49 = 261.63 Hz."""
    return C4_HZ * (2.0 ** ((note - 49) / 12.0))

def playback_rate(note):
    """FT2 clone playback rate (samples/sec) for XM note number."""
    return R_BASE * (2.0 ** ((note - 49) / 12.0))

def sample_freq_for_note(note):
    """Frequency (Hz) to synthesize in a sample (created at SR=8363) so that
    playing `note` produces the correct musical pitch.
    Since SR = R_BASE, this is just the musical frequency of the note."""
    return freq_of(note)

# ---------- Sample synthesis ----------

def _env(n, attack, decay, sustain, release):
    """Simple ADSR envelope, n samples, times in seconds."""
    e = np.ones(n)
    a = max(1, int(attack))
    d = max(1, int(decay))
    r = max(1, int(release))
    if a < n:
        e[:a] = np.linspace(0, 1, a)
    if a+d < n:
        e[a:a+d] = np.linspace(1, sustain, d)
    if a+d < n:
        e[a+d:] = sustain
    if r < n:
        e[-r:] *= np.linspace(1, 0, r)
    return e

def synth(kind, dur, sr=8363, freq=440.0, **kw):
    """Synthesize a mono float32 sample in [-1, 1]."""
    n = max(1, int(dur*sr))
    t = np.arange(n)/sr
    if kind == 'saw':
        H = kw.get('harmonics', 24)
        s = np.zeros(n)
        for h in range(1, H+1):
            s += np.sin(2*np.pi*freq*h*t) / h
        s *= 2.0/np.pi
    elif kind == 'pulse':
        w = kw.get('width', 0.25)
        s = np.where(np.sin(2*np.pi*freq*t) > (1-2*w), 1.0, -1.0).astype(float)
    elif kind == 'square':
        s = np.where(np.sin(2*np.pi*freq*t) >= 0, 1.0, -1.0)
    elif kind == 'tri':
        ph = (t*freq) % 1.0
        s = 4*np.abs(ph-0.5)-1
    elif kind == 'sine':
        s = np.sin(2*np.pi*freq*t)
    elif kind == 'noise':
        rng = np.random.default_rng(kw.get('seed', 0))
        s = rng.uniform(-1, 1, n)
    elif kind == 'kick':
        f0 = kw.get('f0', 150); f1 = kw.get('f1', 45)
        dec = kw.get('decay', 0.12)
        f = f0 + (f1-f0)*np.exp(-t/dec)
        ph = 2*np.pi*np.cumsum(f)/sr
        s = np.sin(ph)*np.exp(-t/dec)
        s += 0.5*np.sin(2*np.pi*kw.get('click', 900)*t)*np.exp(-t/0.004)
    elif kind == 'snare':
        rng = np.random.default_rng(kw.get('seed', 1))
        s = rng.uniform(-1, 1, n)*np.exp(-t/kw.get('decay', 0.09))
        s += 0.6*np.sin(2*np.pi*kw.get('tone', 190)*t)*np.exp(-t/0.05)
    elif kind == 'hat':
        rng = np.random.default_rng(kw.get('seed', 2))
        s = rng.uniform(-1, 1, n)*np.exp(-t/kw.get('decay', 0.035))
        # high-pass-ish: subtract moving average
        k = 8
        if n > k:
            ma = np.convolve(s, np.ones(k)/k, mode='same')
            s = s - ma
    elif kind == 'clap':
        rng = np.random.default_rng(kw.get('seed', 3))
        s = np.zeros(n)
        for off in kw.get('offsets', [0, 0.011, 0.022]):
            m = int(off*sr)
            if m < n:
                seg_len = min(n-m, int(0.06*sr))
                seg = rng.uniform(-1, 1, seg_len)*np.exp(-np.arange(seg_len)/(0.015*sr))
                s[m:m+seg_len] += seg
    elif kind == 'fm':
        I = kw.get('index', 4.0); ratio = kw.get('ratio', 1.0)
        mod = I*np.sin(2*np.pi*freq*ratio*t)
        s = np.sin(2*np.pi*freq*t + mod)
    elif kind == 'pluck':
        H = kw.get('harmonics', 12)
        s = np.zeros(n)
        for h in range(1, H+1):
            s += np.sin(2*np.pi*freq*h*t) / (h**1.3)
        s *= np.exp(-t/kw.get('decay', 0.3))
    elif kind == 'bass':
        H = kw.get('harmonics', 8)
        s = np.zeros(n)
        for h in range(1, H+1):
            s += np.sin(2*np.pi*freq*h*t) / (h**1.1)
        s *= 2/np.pi
    elif kind == 'organ':
        s = (np.sin(2*np.pi*freq*t) + 0.5*np.sin(2*np.pi*2*freq*t)
             + 0.33*np.sin(2*np.pi*3*freq*t) + 0.25*np.sin(2*np.pi*4*freq*t))
    elif kind == 'chipbass':
        s = np.where(np.sin(2*np.pi*freq*t) >= 0, 1.0, -1.0)
        s += 0.35*np.where(np.sin(2*np.pi*2*freq*t) >= 0, 1.0, -1.0)
    elif kind == 'supersaw':
        # detuned saw stack
        s = np.zeros(n)
        for det in kw.get('detunes', [-0.06, -0.02, 0.0, 0.02, 0.06]):
            f = freq * (1 + det)
            H = kw.get('harmonics', 16)
            ss = np.zeros(n)
            for h in range(1, H+1):
                ss += np.sin(2*np.pi*f*h*t + kw.get('phase', 0)) / h
            s += ss * (2.0/np.pi) / len(kw.get('detunes', [0]))
    elif kind == 'softlead':
        # mellow sine-ish lead with slight harmonics
        s = (np.sin(2*np.pi*freq*t) 
             + 0.25*np.sin(2*np.pi*2*freq*t) 
             + 0.1*np.sin(2*np.pi*3*freq*t))
    elif kind == 'arp':
        # fast-decaying pluck, good for arpeggios
        s = np.zeros(n)
        for h in range(1, kw.get('harmonics', 8)+1):
            s += np.sin(2*np.pi*freq*h*t) / h
        s *= 2/np.pi
        s *= np.exp(-t/kw.get('decay', 0.12))
    elif kind == 'metal':
        # inharmonic metallic hit
        rng = np.random.default_rng(kw.get('seed', 7))
        s = np.zeros(n)
        for ratio in kw.get('ratios', [1.0, 1.414, 1.732, 2.0, 2.449, 2.828]):
            s += np.sin(2*np.pi*freq*ratio*t) * np.exp(-t/kw.get('decay', 0.2))
        s += 0.3*rng.uniform(-1,1,n)*np.exp(-t/0.01)
    elif kind == 'bell':
        s = np.zeros(n)
        for ratio, amp in kw.get('partials', [(1.0,1.0),(2.0,0.5),(3.0,0.3),(4.2,0.2),(5.4,0.1)]):
            s += amp*np.sin(2*np.pi*freq*ratio*t)*np.exp(-t/kw.get('decay', 1.2))
    else:
        raise ValueError(f"unknown sample kind: {kind}")
    # Apply envelope
    env = _env(n, kw.get('attack', 0.003), kw.get('decay_time', 0.0),
               kw.get('sustain', 1.0), kw.get('release', 0.06))
    s = s * env
    # Optional lowpass (simple one-pole)
    if kw.get('lowpass', 0) > 0:
        cutoff = kw['lowpass']
        alpha = 1.0 - np.exp(-2*np.pi*cutoff/sr)
        y = np.zeros(n)
        acc = 0.0
        for i in range(n):
            acc += alpha * (s[i] - acc)
            y[i] = acc
        s = y
    # Normalize
    m = np.abs(s).max()
    if m > 1e-9:
        s = s / m * kw.get('gain', 0.85)
    return s.astype(np.float32)

def make_sample_for_note(kind, note, dur, sr=8363, **kw):
    """Create a sample at SR=8363 (C-4 playback rate) that plays at the correct
    musical pitch for any note. The frequency in the sample equals the musical
    frequency of the note, and envelope times are correct at C-4."""
    kw2 = dict(kw)
    kw2['freq'] = sample_freq_for_note(note)
    return synth(kind, dur, sr, **kw2)

# ---------- 16-bit delta encoding ----------

def delta_encode_16bit(samples_float):
    """Convert float samples to 16-bit delta-encoded bytes."""
    i16 = np.clip(samples_float * 32767, -32768, 32767).astype('<i2')
    deltas = np.diff(i16.astype(np.int32), prepend=0)
    deltas = np.clip(deltas, -32768, 32767).astype('<i2')
    return deltas.tobytes()

# ---------- XM Module ----------

class XM:
    def __init__(self, name="untitled", channels=8, speed=6, bpm=140):
        self.name = name
        self.channels = channels
        self.speed = speed
        self.bpm = bpm
        self.orders = []
        self.loop_start = 0
        self.patterns = []       # list of {'rows': int, 'cells': [[cell]*ch]*rows}
        self.instruments = []    # list of {'name': str, 'samples': [sample_dict]}
        self.global_vol = 64
        self.master_vol = 48

    def new_pattern(self, rows=64):
        p = {'rows': rows, 'cells': [[None]*self.channels for _ in range(rows)]}
        self.patterns.append(p)
        return len(self.patterns) - 1

    def set_cell(self, pat, row, ch, note=None, ins=None, vol=None, eff=None, effp=None):
        p = self.patterns[pat]
        c = p['cells'][row][ch] or {}
        if note is not None:
            c['note'] = name_to_note(note) if isinstance(note, str) else int(note)
        if ins is not None: c['ins'] = ins
        if vol is not None: c['vol'] = vol
        if eff is not None: c['eff'] = eff
        if effp is not None: c['effp'] = effp
        p['cells'][row][ch] = c

    def add_instrument(self, name, samples):
        """samples: list of dicts with keys: data (float32 array), vol, pan, finetune,
        relnote, loop (tuple or None), name, and optionally smap_ranges.
        smap_ranges: list of (low_note, high_note, sample_index) for custom mapping.
        If not given, notes are distributed evenly across samples."""
        idx = len(self.instruments) + 1
        self.instruments.append({'name': name, 'samples': samples})
        return idx

    def _pack_pattern(self, p):
        out = bytearray()
        for r in range(p['rows']):
            for ch in range(self.channels):
                c = p['cells'][r][ch]
                if not c:
                    out.append(0x80)  # FT2 clone: empty cell flag with bit 7 set
                    continue
                flag = 0x80  # FT2 clone always sets bit 7
                if 'note' in c: flag |= 1
                if 'ins' in c: flag |= 2
                if 'vol' in c: flag |= 4
                if 'eff' in c: flag |= 8
                if 'effp' in c: flag |= 16
                out.append(flag)
                if flag & 1: out.append(c['note'] & 0xFF)
                if flag & 2: out.append(c['ins'] & 0xFF)
                if flag & 4: out.append(c['vol'] & 0xFF)
                if flag & 8:
                    out.append(c['eff'] & 0xFF)
                    out.append(c['effp'] & 0xFF)
        return bytes(out)

    def write(self, path):
        npat = len(self.patterns)
        nins = len(self.instruments)
        songlen = len(self.orders)

        # ---- Pattern data ----
        pat_blobs = []
        for p in self.patterns:
            data = self._pack_pattern(p)
            hdr = struct.pack('<IBHH', 9, 0, p['rows'], len(data))
            pat_blobs.append(hdr + data)

        # ---- Instruments ----
        ins_blobs = []
        for ins in self.instruments:
            samples = ins['samples']
            ns = len(samples)
            # Build sample map (96 bytes)
            smap = bytearray(96)
            # Check if custom ranges are provided
            has_custom = any('smap_ranges' in s for s in samples)
            if has_custom:
                for note in range(96):
                    smap[note] = 0  # default to sample 0
                for s in samples:
                    for (lo, hi, idx) in s.get('smap_ranges', []):
                        for note in range(lo, hi+1):
                            if 0 <= note < 96:
                                smap[note] = idx
            else:
                # Distribute notes evenly across samples
                for note in range(96):
                    smap[note] = min(ns - 1, note * ns // 96)
            # FT2 clone instrument header (263 bytes):
            # isize(4) name(22) type(1) nsmps(2) smap(96) env(138)
            nm = ins['name'].encode('latin1')[:22].ljust(22, b'\x00')
            env = bytes.fromhex('00000000000030000400400008002c000e00080018001600200008003c00000046000000500000005a000000640000006e000000000020000a0028001e001800320020003c00200046002000500020005a002000640020006e00200078002000820020000606020305020305000000000000800000000000000000000000000000000000000000000000')  # FT2 clone default envelope data
            ihdr = struct.pack('<I', 263) + nm + struct.pack('<BH', 0, ns) + bytes(smap) + env
            assert len(ihdr) == 263, len(ihdr)
            body = bytearray(ihdr)
            # Sample headers (ALL headers first, then ALL data)
            hdrs = []
            datas = []
            for s in samples:
                arr = s['data']
                encoded = delta_encode_16bit(arr)
                nbytes = len(encoded)
                nsamp = nbytes // 2  # 16-bit samples
                lstart, llen, stype = 0, 0, 16  # 16-bit flag
                if s.get('loop'):
                    lstart = max(0, min(s['loop'][0], nsamp - 1))
                    llen = max(2, min(s['loop'][1], nsamp - lstart))
                    stype = 16 | 1  # 16-bit + forward loop
                hdr = struct.pack('<IIIBBBBBB', nbytes, lstart, llen,
                                  s.get('vol', 64),
                                  s.get('finetune', 0) & 0xFF,
                                  stype,
                                  s.get('pan', 128),
                                  s.get('relnote', 0) & 0xFF,
                                  0)
                hdr += s.get('name', 'sample').encode('latin1')[:22].ljust(22, b' ')
                hdrs.append(hdr)
                datas.append(encoded)
            for h in hdrs:
                body += h
            for dta in datas:
                body += dta
            ins_blobs.append(bytes(body))

        # ---- Song header ----
        # FT2 clone format: 16 bytes of fields + 256 bytes of orders = 272 bytes
        # hlen field = 276 (= 272 + 4, includes the hlen field itself)
        orders = bytes(list(self.orders[:256]) + [0]*(256 - min(256, len(self.orders))))
        sh = struct.pack('<HHHHHHHH', songlen, self.loop_start, self.channels,
                         npat, nins, 1, self.speed, self.bpm)
        song_header = sh + orders
        assert len(song_header) == 16 + 256, len(song_header)

        # ---- Assemble ----
        out = bytearray()
        out += b'Extended Module: '
        out += self.name.encode('latin1')[:20].ljust(20, b' ')
        out += b'\x1a'
        out += b'Fasttracker II clone'.ljust(20, b' ')
        out += struct.pack('<H', 0x0104)
        out += struct.pack('<I', len(song_header) + 4)  # hlen includes itself
        out += song_header
        for pb in pat_blobs:
            out += pb
        for ib in ins_blobs:
            out += ib
        with open(path, 'wb') as f:
            f.write(bytes(out))
        return len(out)
