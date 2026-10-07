import sys; sys.path.insert(0,'/workspace/build')
import build_module as B
CHN=[n for n,_ in B.CHS]
def dump(pi, rows=24, sel=None):
    p=B.P[pi]
    grid=p.grid
    print("=== pattern %d ==="%pi)
    for row in range(rows):
        line=[]
        for ci,name in enumerate(CHN):
            if sel and name not in sel: continue
            c=grid.get((row,ci))
            if c is None: line.append("        ")
            elif c[2]==97: line.append("  off    ")
            else:
                nn=B.nm(c[2]) if c[2]>0 else "---"
                line.append("%-4s%02d  "%(nn,c[4]))
        print("%2d |%s"%(row,"|".join(line)))
if __name__=='__main__':
    pi=int(sys.argv[1]) if len(sys.argv)>1 else 4
    sel=sys.argv[2].split(',') if len(sys.argv)>2 else None
    dump(pi,sel=sel)
