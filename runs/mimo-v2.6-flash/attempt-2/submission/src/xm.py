import struct, numpy as np
def parse(path, with_patterns=True):
    b=open(path,'rb').read()
    assert b[:17]==b"Extended Module: "
    o=17
    name=b[o:o+20].decode('latin1').strip(); o+=20+1
    tracker=b[o:o+20].decode('latin1').strip(); o+=20
    ver=struct.unpack_from('<H',b,o)[0]; o+=2
    hsize_off=o
    hsize=struct.unpack_from('<I',b,o)[0]; o+=4
    songlen,restart,chn,pats,instrs,flags,speed,bpm=struct.unpack_from('<8H',b,o)
    orders=list(b[o+16:o+16+songlen])
    o=hsize_off+hsize
    out={"name":name,"tracker":tracker,"ver":hex(ver),"songlen":songlen,"restart":restart,
         "channels":chn,"npats":pats,"ninstrs":instrs,"flags":flags,"speed":speed,"bpm":bpm,"orders":orders}
    pinfo=[]
    for p in range(pats):
        psz=struct.unpack_from('<I',b,o)[0]
        rows=struct.unpack_from('<H',b,o+5)[0]
        packed=struct.unpack_from('<H',b,o+7)[0]
        o+=psz
        data=b[o:o+packed]; o+=packed
        grid=[[None]*chn for _ in range(rows)]
        if packed>0:
            r=c=0; i=0
            while i<len(data) and r<rows:
                fb=data[i]; i+=1
                if fb&0x80:
                    note=ins=vol=eff=px=0
                    if fb&1: note=data[i]; i+=1
                    if fb&2: ins=data[i]; i+=1
                    if fb&4: vol=data[i]; i+=1
                    if fb&8: eff=data[i]; i+=1
                    if fb&16: px=data[i]; i+=1
                else:
                    note,ins,vol,eff,px=fb,data[i],data[i+1],data[i+2],data[i+3]; i+=4
                grid[r][c]=(note,ins,vol,eff,px)
                c+=1
                if c>=chn: c=0; r+=1
        pinfo.append({"rows":rows,"packed":packed,"grid":grid})
    out["patterns"]=pinfo
    instr=[]
    for i in range(instrs):
        ih=o
        isz=struct.unpack_from('<I',b,o)[0]
        iname=b[o+4:o+26].decode('latin1').strip()
        itype=b[o+26]
        nsmp=struct.unpack_from('<H',b,o+27)[0]
        o=ih+isz
        smps=[]
        for s in range(nsmp):
            ln,ls,ll=struct.unpack_from('<III',b,o)
            vol1,finet,typ,pan,reln=b[o+12],b[o+13],b[o+14],b[o+15],b[o+16]
            sname=b[o+20:o+42].decode('latin1').strip()
            smps.append({"len":ln,"loop_start":ls,"loop_len":ll,"vol":vol1,"finetune":finet,
                         "type":typ,"pan":pan,"relnote":reln,"name":sname})
            o+=40
        for s in range(nsmp):
            o+=smps[s]["len"]
        instr.append({"name":iname,"type":itype,"nsmp":nsmp,"smp":smps})
    out["instruments"]=instr
    out["size"]=len(b)
    return out
def summarize(path):
    d=parse(path)
    print("song:",d["name"],"| tracker",d["tracker"],"ver",d["ver"],"| len",d["songlen"],"restart",d["restart"],
          "| chn",d["channels"],"pats",d["npats"],"instr",d["ninstrs"],"| speed",d["speed"],"bpm",d["bpm"],"| orders",d["orders"])
    for i,ins in enumerate(d["instruments"]):
        for j,s in enumerate(ins["smp"]):
            print(f"  I{i+1} '{ins['name']}' smp{j} '{s['name']}' len={s['len']} loop={s['loop_start']}+{s['loop_len']} vol={s['vol']} ft={s['finetune']} type={s['type']} pan={s['pan']} rel={s['relnote']}")
    return d
if __name__=="__main__":
    import sys
    d=summarize(sys.argv[1])
    for p in d["patterns"]:
        print("pat rows",p["rows"],"packed",p["packed"])
