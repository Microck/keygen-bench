import base64, json, subprocess, numpy as np, wave, os

WORK='/workspace/work'

def run(calls, verbose=False):
    p='/workspace/work/_batch.json'
    with open(p,'w') as f: json.dump(calls,f)
    r=subprocess.run(['ft2','batch',p],capture_output=True,text=True)
    txt=r.stdout
    # count errors
    nerr=txt.count('"isError": true')
    if nerr or verbose:
        # print the error lines
        for line in txt.split('{"type": "text"')[1:]:
            if 'true' in line.split('"isError"')[0] or nerr:
                pass
        if nerr: print('ERRORS:',nerr); print(txt[-3000:])
    return txt

def b64(x):
    return base64.b64encode(np.asarray(x,dtype='<i2').tobytes()).decode()

def wavfile(path, data, rate=44100):
    with wave.open(path,'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(np.asarray(data,dtype='<i2').tobytes())

def render(path, rate=44100, bits=16, amp=8, loops=0, start=0, stop=None):
    a={'path':path,'rate':rate,'bits':bits,'amp':amp,'loops':loops,'start':start}
    if stop is not None: a['stop']=stop
    r=subprocess.run(['ft2','call','module_render',json.dumps(a)],capture_output=True,text=True)
    return json.loads(r.stdout[r.stdout.index('{'):]) if '{' in r.stdout else r.stdout

def loadwav(path):
    with wave.open(path,'rb') as w:
        n=w.getnframes(); ch=w.getnchannels()
        d=np.frombuffer(w.readframes(n),dtype='<i2').astype(np.float64)/32768.0
    return d.reshape(-1,ch)
