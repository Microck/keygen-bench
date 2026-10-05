import sys, json, subprocess, os
path = sys.argv[1] if len(sys.argv)>1 else '/workspace/work/tune_draft.xm'
out = sys.argv[2] if len(sys.argv)>2 else '/workspace/work/tune_draft.wav'
cmds=[{"name":"module_load","arguments":{"path":path}},
      {"name":"module_info","arguments":{}},
      {"name":"module_render","arguments":{"path":out,"rate":44100,"bits":16,"loops":1}}]
json.dump(cmds,open('/workspace/work/cm_render.json','w'))
r=subprocess.run(['ft2','batch','/workspace/work/cm_render.json'],capture_output=True,text=True)
print(r.stdout[-400:])
