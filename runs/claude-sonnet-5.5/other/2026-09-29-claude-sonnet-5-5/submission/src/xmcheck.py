import struct, sys, collections
d = open(sys.argv[1], 'rb').read()
hsize = struct.unpack_from('<I', d, 60)[0]
songlen, restart, nch, npat, ninst = struct.unpack_from('<HHHHH', d, 64)
order = list(d[80:80 + songlen])
pos = 60 + hsize
problems = []
stats = collections.Counter()
used_inst = set()
last_note_state = {}
for p in range(npat):
    hl, ptype, rows, psize = struct.unpack_from('<IBHH', d, pos)
    data = d[pos + hl:pos + hl + psize]
    pos += hl + psize
    i = 0
    row = ch = 0
    for row in range(rows):
        for ch in range(nch):
            b = data[i]; i += 1
            note = inst = vol = fx = fxp = 0
            if b & 0x80:
                if b & 1: note = data[i]; i += 1
                if b & 2: inst = data[i]; i += 1
                if b & 4: vol = data[i]; i += 1
                if b & 8: fx = data[i]; i += 1
                if b & 16: fxp = data[i]; i += 1
            else:
                note = b; inst = data[i]; vol = data[i + 1]; fx = data[i + 2]; fxp = data[i + 3]; i += 4
            if note:
                stats['notes'] += 1
                if not (1 <= note <= 97): problems.append(('bad note', p, row, ch, note))
            if note and note != 97 and inst == 0: problems.append(('note without instrument', p, row, ch))
            if inst:
                used_inst.add(inst)
                if inst > ninst: problems.append(('bad inst', p, row, ch, inst))
            if vol and not (0x10 <= vol <= 0x50): problems.append(('vol column out of range', p, row, ch, vol))
            if fx: stats['fx_%X' % fx] += 1
            if fx not in (0, 4, 0xE): problems.append(('unexpected effect', p, row, ch, fx))
    if i != len(data): problems.append(('pattern data length mismatch', p, i, len(data)))
print('order', order, 'restart', restart, 'channels', nch)
print('note events', stats['notes'], '| effects:', {k: v for k, v in stats.items() if k.startswith('fx_')})
print('instruments used', sorted(used_inst))
print('problems:', problems[:10] if problems else 'none')
