import sys
sys.path.insert(0, '.')
from ft2lib import run_batch, sample_calls, call
import synth

REL = synth.REL
N_CHANNELS = 12

# instrument slot -> (builder, display name, panning, base volume)
INSTR = {
    1:  (synth.build_lead,       "Lead Pulse",   128, 64),
    2:  (synth.build_lead2,      "Lead Soft",    96,  60),
    3:  (synth.build_arp,        "Arp Pluck",    160, 56),
    4:  (synth.build_bass,       "Sub Bass",     128, 64),
    5:  (synth.build_pad,        "Warm Pad",     128, 48),
    6:  (synth.build_kick,       "Kick",         128, 64),
    7:  (synth.build_snare,      "Snare",        128, 60),
    8:  (synth.build_clap,       "Clap",         150, 52),
    9:  (synth.build_hat_closed, "Hat Closed",   176, 44),
    10: (synth.build_hat_open,   "Hat Open",     84,  44),
    11: (synth.build_ride,       "Ride Perc",    160, 40),
    12: (synth.build_crash,      "Crash",        128, 48),
}

CHANNEL_OF = {
    'lead': 0, 'lead2': 1, 'arp': 2, 'bass': 3, 'pad': 4,
    'kick': 5, 'snare': 6, 'clap': 7, 'hat_closed': 8, 'hat_open': 9,
    'ride': 10, 'crash': 11,
}
INSTRUMENT_OF = {
    'lead': 1, 'lead2': 2, 'arp': 3, 'bass': 4, 'pad': 5,
    'kick': 6, 'snare': 7, 'clap': 8, 'hat_closed': 9, 'hat_open': 10,
    'ride': 11, 'crash': 12,
}

def build_instrument_batch():
    calls = []
    for slot, (builder, name, pan, vol) in INSTR.items():
        pcm = builder()
        calls += sample_calls(slot, pcm, name, relative_note=REL, finetune=0,
                               loop=False, volume=vol, panning=pan)
    return calls

if __name__ == "__main__":
    call("module_new", {"channels": N_CHANNELS, "name": "ASCII DREAMS"})
    calls = build_instrument_batch()
    print(f"{len(calls)} calls")
    run_batch(calls)
    print(call("module_info", {}))
