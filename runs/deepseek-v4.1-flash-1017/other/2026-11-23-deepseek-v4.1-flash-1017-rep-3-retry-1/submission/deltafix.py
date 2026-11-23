import numpy as np

def fit_delta(data, vol, limit=31800):
    """Scale 16-bit sample data so consecutive-sample deltas fit int16 (XM delta encoding).
    Returns (newdata, newvol, scale). Compensates loudness with instrument volume (0..64)."""
    q=np.clip(np.round(np.asarray(data,dtype=np.float64)*32767),-32768,32767)
    if len(q)<2:
        return data, vol, 1.0
    md=float(np.abs(np.diff(q)).max())
    if md<=limit:
        return data, vol, 1.0
    s=limit/md
    newdata=np.asarray(data,dtype=np.float64)*s
    newvol=int(round(min(64.0, vol/max(s,1e-9))))
    return newdata, newvol, s

def check(data):
    q=np.clip(np.round(np.asarray(data,dtype=np.float64)*32767),-32768,32767)
    return int(np.abs(np.diff(q)).max()) if len(q)>1 else 0
