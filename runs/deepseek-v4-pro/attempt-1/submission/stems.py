import json, subprocess, os
batch=json.load(open('work/pattern_batch.json'))
def build_stem(channels, out):
    cells=[b for b in batch if b['arguments']['channel'] in channels]
    json.dump(cells, open('work/stem_cells.json','w'))
    subprocess.run(['ft2','call','module_new','{"channels":10,"name":"stem"}'],check=True,capture_output=True)
    subprocess.run(['ft2','batch','work/sample_batch.json'],check=True,capture_output=True)
    subprocess.run(['ft2','batch','work/sample_meta.json'],check=True,capture_output=True)
    subprocess.run(['ft2','batch','work/stem_cells.json'],check=True,capture_output=True)
    sb=json.load(open('work/song_batch.json'))
    json.dump(sb, open('work/stem_song.json','w'))
    subprocess.run(['ft2','batch','work/stem_song.json'],check=True,capture_output=True)
    subprocess.run(['ft2','call','module_render',json.dumps({"path":out,"rate":44100})],check=True,capture_output=True)
    print('rendered', out, len(cells))
build_stem([8,9], 'work/stem_lead.wav')
build_stem([4], 'work/stem_bass.wav')
build_stem([5,6], 'work/stem_arp.wav')
build_stem([7], 'work/stem_pad.wav')
build_stem([0,1,2,3], 'work/stem_drums.wav')
