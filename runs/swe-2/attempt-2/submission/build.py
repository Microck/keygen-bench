import numpy as np, base64, json, os, subprocess
import samples as S

R = 8363.0
# ---------------- instruments ----------------
# (instr_no, name, pcm, loop_start_samples or None, loop_len_samples, vol, pan)
def mk(pcm, ls, ll, vol, pan):
    return dict(pcm=pcm, ls=ls, ll=ll, vol=vol, pan=pan)

INS = {
 1:  ("bass.fat",   S.bass(),   None, None, 64, 128),
 2:  ("lead.saw",   S.lead(),   "lead", None, 56, 128),
 3:  ("arp.pluck",  S.pluck(),  None, None, 58, 152),
 4:  ("pad.soft",   S.pad(),    "pad",  None, 44, 118),
 5:  ("dr.kick",    S.kick(),   None, None, 64, 128),
 6:  ("dr.snare",   S.snare(),  None, None, 62, 140),
 7:  ("dr.hat",     S.hat(),    None, None, 48, 172),
 8:  ("dr.ohat",    S.openhat(),None, None, 40, 96),
 9:  ("dr.clap",    S.clap(),   None, None, 46, 140),
 10: ("dr.tom",     S.tom(),    None, None, 56, 108),
 11: ("fx.sweep",   S.sweep(),  None, None, 44, 128),
 12: ("lead.square",S.lead_sq(),"sq",   None, 52, 128),
}

calls = []
for ins,(nm,dat,*_ ,vol,pan) in []:
    pass
for ins,(nm,val,a,b,vol,pan) in INS.items():
    if a in ("lead","sq","pad"):
        pcm, ls, ll = val
        flags = 17
    else:
        pcm = val; ls=None; ll=None; flags=16
    calls.append({"name":"sample_create_from_pcm","arguments":
        {"instrument":ins,"sample":0,"pcm":S.b64(pcm),"encoding":"int16","name":nm}})
    args = {"instrument":ins,"sample":0,"volume":vol,"panning":pan,"flags":flags,"name":nm}
    if ls is not None:
        args["loop_start"]=ls; args["loop_length"]=ll
    calls.append({"name":"sample_set","arguments":args})
    calls.append({"name":"instrument_set","arguments":{"instrument":ins,"name":nm}})

json.dump(calls, open("batch_instr.json","w"))
print("instrument calls:", len(calls))
