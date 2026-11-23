import sys, numpy as np
sys.path.insert(0,'/workspace/work')
from xmlib import Song, Pattern, write_xm

def stem_song(song, keep_ch, path, name_suffix=''):
    s=Song(song.name[:16]+name_suffix, song.channels, bpm=song.bpm, speed=song.speed)
    s.instruments=song.instruments
    s.orders=song.orders; s.restart=song.restart
    for p in song.patterns:
        q=Pattern(p.rows, p.channels)
        for (r,c),cell in p.cells.items():
            if c in keep_ch: q.cells[(r,c)]=cell
        s.patterns.append(q)
    return write_xm(s,path)
