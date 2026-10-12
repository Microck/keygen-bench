import json
INST=[
 # (idx, name, wav, pan, vol, relnote, looped, looplen)
 (1,'kick',   'kick',  128, 60, 29, False, 0),
 (2,'snare',  'snare', 128, 54, 29, False, 0),
 (3,'hatc',   'hatc',  170, 34, 29, False, 0),
 (4,'hato',   'hato',  182, 34, 29, False, 0),
 (5,'crash',  'crash', 150, 40, 29, False, 0),
 (6,'tom',    'tom',   100, 48, 29, False, 0),
 (7,'riser',  'riser', 128, 46, 29, False, 0),
 (8,'bass',   'bass',  128, 62, 24, True, 1023),
 (9,'organL', 'organ', 96,  40, 24, True, 1023),
 (10,'organR','organ', 168, 40, 24, True, 1023),
 (11,'arp',   'arp',   112, 36, 24, True, 1023),
 (12,'lead',  'lead',  128, 54, 24, True, 44100),
 (13,'lead2', 'lead2', 144, 44, 24, True, 1023),
 (14,'padL',  'pad',   56,  42, 24, True, 44100),
 (15,'padR',  'pad',   200, 42, 24, True, 44100),
]
def setup_calls(channels=10, name='Keygen Tune', bpm=150, speed=6):
    calls=[{"name":"module_new","arguments":{"channels":channels,"name":name}},
           {"name":"song_set","arguments":{"bpm":bpm,"speed":speed}}]
    for idx,nm,wav,pan,vol,rn,looped,ll in INST:
        calls.append({"name":"sample_load","arguments":{"path":f"work/samples/{wav}.wav","instrument":idx,"sample":0}})
        calls.append({"name":"sample_set","arguments":{"instrument":idx,"sample":0,"name":wav[:22],
            "volume":vol,"panning":pan,"finetune":0,"relative_note":rn,
            "loop_start":0,"loop_length":ll,"flags":1 if looped else 0}})
        calls.append({"name":"instrument_set","arguments":{"instrument":idx,"name":nm}})
    return calls
