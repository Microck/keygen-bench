import song
S = song.build()
names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
chs = {'bass': song.BS, 'arp': song.AR, 'lead': song.LD, 'cnt': song.CT, 'pad': song.PD, 'rs': song.RS}
state = {k: None for k in chs}
arpiv = {}
issues = []
for r in range(S.n):
    for k, c in chs.items():
        cell = S.g[r][c]
        if cell[0] == 97: state[k] = None
        elif cell[0]:
            if k == 'rs' and cell[1] == song.I_RISE: state[k] = None
            else: state[k] = cell[0] + 11
        if k == 'arp' and cell[3] == 0 and cell[4]: arpiv[r] = cell[4]
    # build set of sounding pitch classes w/ sources
    snd = []
    for k, n in state.items():
        if n is None: continue
        if k == 'arp':
            p = arpiv.get(r, 0x37)
            for iv in (0, p >> 4, p & 15): snd.append(('arp', (n + iv) % 12))
        else: snd.append((k, n % 12))
    if state['lead'] is not None:
        lp = state['lead'] % 12
        bad = [(k, names[pc]) for k, pc in snd if k != 'lead' and (pc - lp) % 12 in (1, 11, 6)]
        if bad and r % 2 == 0:
            issues.append((r // 64, r % 64, names[lp], bad))
for i in issues: print(i)
print(len(issues), 'clash rows (even rows only)')
