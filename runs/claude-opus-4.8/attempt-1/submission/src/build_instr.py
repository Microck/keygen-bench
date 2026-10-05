import json
WORK="/workspace/work"
osc=[(1,"lead_256.wav","lead",50,128,4),(2,"bass_256.wav","bass",62,128,4),
 (3,"arp_256.wav","arpL",40,72,4),(4,"pad_256.wav","pad",34,128,4),
 (9,"lead2_256.wav","lead2",40,150,4),(10,"sub_256.wav","sub",50,128,4),
 (13,"arp_256.wav","arpR",34,184,4),(14,"pad_256.wav","padL",30,60,-3),(15,"pad_256.wav","padR",30,196,11)]
perc=[(5,"kick.wav","kick",64,128,-26),(6,"snare3.wav","snare",54,128,-26),
 (7,"hatc4.wav","hat",34,168,-26),(8,"hato4.wav","ohat",32,96,-26),
 (11,"clap.wav","clap",46,100,-26),(12,"crash.wav","crash",40,128,-26)]
calls=[]
for slot,f,name,vol,pan,ft in osc:
    calls+=[{"name":"sample_load","arguments":{"path":f"{WORK}/{f}","instrument":slot,"sample":0}},
            {"name":"instrument_set","arguments":{"instrument":slot,"name":name}},
            {"name":"sample_set","arguments":{"instrument":slot,"sample":0,"name":name,"volume":vol,
             "panning":pan,"relative_note":36,"finetune":ft,"loop_start":0,"loop_length":256,"flags":1}}]
for slot,f,name,vol,pan,ft in perc:
    calls+=[{"name":"sample_load","arguments":{"path":f"{WORK}/{f}","instrument":slot,"sample":0}},
            {"name":"instrument_set","arguments":{"instrument":slot,"name":name}},
            {"name":"sample_set","arguments":{"instrument":slot,"sample":0,"name":name,"volume":vol,
             "panning":pan,"relative_note":29,"finetune":ft,"flags":0}}]
json.dump(calls,open(f"{WORK}/batch_instr.json","w"));print("calls",len(calls))
