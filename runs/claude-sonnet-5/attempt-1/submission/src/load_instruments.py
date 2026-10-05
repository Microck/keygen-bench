import sys, base64
sys.path.insert(0, '.')
import numpy as np
from ftclient import jcall, call
import synth as S
import theory as T

INSTR = {}  # name -> index

def to_i16(sig):
    return np.clip(sig * 32767.0, -32768, 32767).astype('<i2')

def b64_of(sig):
    return base64.b64encode(to_i16(sig).tobytes()).decode()

def load_oneshot(idx, name, sig, sr, volume=64, panning=128, detune_cents=0.0):
    pcm = b64_of(sig)
    jcall("sample_create_from_pcm", instrument=idx, sample=0, pcm=pcm, encoding="int16", name=name)
    rel, fine = T.calibrate(sr, detune_cents=detune_cents)
    jcall("sample_set", instrument=idx, sample=0, volume=volume, panning=panning,
          finetune=fine, relative_note=rel, loop_start=0, loop_length=0, flags=16)
    jcall("instrument_set", instrument=idx, name=name)
    INSTR[name] = idx
    print(f"loaded {name} -> instrument {idx}  len={len(sig)} sr={sr} rel={rel} fine={fine}")

def load_looped(idx, name, sig, sr, attack_len, loop_len, volume=64, panning=128, detune_cents=0.0):
    pcm = b64_of(sig)
    jcall("sample_create_from_pcm", instrument=idx, sample=0, pcm=pcm, encoding="int16", name=name)
    rel, fine = T.calibrate(sr, detune_cents=detune_cents)
    jcall("sample_set", instrument=idx, sample=0, volume=volume, panning=panning,
          finetune=fine, relative_note=rel, loop_start=attack_len, loop_length=loop_len, flags=17)
    jcall("instrument_set", instrument=idx, name=name)
    INSTR[name] = idx
    print(f"loaded {name} -> instrument {idx}  total={len(sig)} attack={attack_len} loop={loop_len} sr={sr} rel={rel} fine={fine}")


def build(channels=14, song_name="Unlock Sequence"):
    print(jcall("module_new", channels=channels, name=song_name))

    load_oneshot(1, "Kick", S.make_kick(44100), 44100, volume=64, panning=128)
    load_oneshot(2, "Snare", S.make_snare(44100), 44100, volume=60, panning=128)
    load_oneshot(3, "Clap", S.make_clap(44100), 44100, volume=50, panning=140)
    hatc_sig = S.make_hat_closed(44100)
    load_oneshot(4, "HatClosed", hatc_sig, 44100, volume=40, panning=170)
    load_oneshot(18, "HatClosedA", hatc_sig, 44100, volume=40, panning=84)
    load_oneshot(19, "HatClosedB", hatc_sig, 44100, volume=40, panning=172)
    load_oneshot(5, "HatOpen", S.make_hat_open(44100), 44100, volume=40, panning=170)
    load_oneshot(6, "Crash", S.make_crash(22050), 22050, volume=48, panning=110)
    load_oneshot(7, "Tom", S.make_tom(44100), 44100, volume=55, panning=90)
    load_oneshot(8, "Riser", S.make_riser(11025), 11025, volume=56, panning=128)
    load_oneshot(9, "Downlifter", S.make_downlifter(11025), 11025, volume=56, panning=128)

    load_oneshot(10, "Bass", S.make_bass(44100), 44100, volume=62, panning=128)
    load_oneshot(11, "Lead", S.make_lead(44100), 44100, volume=56, panning=118)
    load_oneshot(12, "Lead2", S.make_lead(44100), 44100, volume=46, panning=168, detune_cents=7.0)
    load_oneshot(13, "Arp", S.make_arp(44100), 44100, volume=44, panning=128)

    pad_sig, al, ll = S.make_pad(44100, cycles=32)
    load_looped(14, "PadL", pad_sig, 44100, al, ll, volume=40, panning=64, detune_cents=-5.0)
    load_looped(15, "PadR", pad_sig, 44100, al, ll, volume=40, panning=196, detune_cents=5.0)
    load_looped(17, "PadMid", pad_sig, 44100, al, ll, volume=40, panning=128, detune_cents=0.0)
    load_oneshot(16, "Stab", S.make_stab(44100), 44100, volume=50, panning=128)

    return INSTR


if __name__ == "__main__":
    instr = build()
    print(instr)
    print(jcall("module_info"))
