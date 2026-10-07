import json, subprocess, base64, struct, math
import numpy as np

def call(tool, args):
    j=json.dumps(args)
    r=subprocess.run(["ft2","call",tool,j], capture_output=True, text=True)
    try:
        d=json.loads(r.stdout)
        txt=d["content"][0]["text"] if d.get("content") else r.stdout
        err=d.get("isError",False)
    except Exception as e:
        raise RuntimeError(f"call {tool} failed: {r.stdout[:2000]} {r.stderr[:2000]}")
    if err:
        raise RuntimeError(f"tool {tool} error: {txt}")
    return txt

def pack8(S):
    """Pack desired signed 8-bit sample bytes S (-128..127) into int16 array for upload trick."""
    S=list(int(x) for x in S)
    N=len(S)
    if N%2==1:
        S=S+[0]; N+=1
    # clamp
    S=[max(-128,min(127,x)) for x in S]
    Su=[x & 0xFF for x in S]
    P=[]
    for j in range(N//2):
        lo=Su[2*j]; hi=Su[2*j+1]
        v=lo+256*hi
        if v>=32768: v-=65536
        P.append(v)
    P+=[0]*(N-len(P))
    return np.array(P,dtype=np.int16)

def upload_packed(S, inst, name, loop_start=0, loop_length=0, flags=0, volume=64, panning=128, rel=0, ft=0):
    P=pack8(S)
    b64=base64.b64encode(P.tobytes()).decode()
    txt=call("sample_create_from_pcm", {"instrument":inst,"sample":0,"pcm":b64,"encoding":"int16","name":name})
    #print(txt)
    call("sample_set", {"instrument":inst,"sample":0,"name":name,"volume":volume,"panning":panning,"loop_start":loop_start,"loop_length":loop_length,"flags":flags,"finetune":ft,"relative_note":rel})
    call("instrument_set", {"instrument":inst,"name":name})
    return len(S)

def xm_info(path):
    d=open(path,'rb').read()
    hlen=struct.unpack('<I', d[60:64])[0]
    songlen, restart, nchan, npat, ninstr, flags, speed, bpm = struct.unpack('<HHHHHHHH', d[64:80])
    return {"len":len(d),"hlen":hlen,"songlen":songlen,"restart":restart,"nchan":nchan,"npat":npat,"ninstr":ninstr,"speed":speed,"bpm":bpm}
