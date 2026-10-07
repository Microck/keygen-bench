import json, subprocess, sys
samples = json.load(open('/workspace/build/samples.json'))
song = json.load(open('/workspace/build/song.json'))
calls = [{'name': 'module_new', 'arguments': {'channels': 12, 'name': 'crackdown'}}] + samples + song
calls.append({'name': 'module_save', 'arguments': {'path': '/workspace/build/tune.xm', 'format': 'xm'}})
calls.append({'name': 'module_render', 'arguments': {'path': '/workspace/build/tune.wav', 'rate': 44100, 'bits': 16}})
json.dump(calls, open('/workspace/build/all.json', 'w'))
r = subprocess.run(['ft2', 'batch', '/workspace/build/all.json'], capture_output=True, text=True)
out = r.stdout.strip().split('\n')
bad = [l for l in out if '"isError": true' in l or 'error' in l.lower()]
print('calls:', len(calls), 'results:', len(out), 'errors:', len(bad))
for l in bad[:10]:
    print(l)
print(out[-1])
