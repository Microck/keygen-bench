"""Writes MANIFEST.sha256 for the submission directory and checks the size limits."""
import hashlib, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows, total, count = [], 0, 0
for dp, dn, fn in os.walk(ROOT):
    dn[:] = sorted(d for d in dn if d != '__pycache__')
    for f in sorted(fn):
        p = os.path.join(dp, f)
        rel = os.path.relpath(p, ROOT)
        if rel == 'MANIFEST.sha256':
            continue
        assert os.path.isfile(p) and not os.path.islink(p), rel
        h = hashlib.sha256(open(p, 'rb').read()).hexdigest()
        rows.append('%s  %s' % (h, rel))
        total += os.path.getsize(p)
        count += 1
open(os.path.join(ROOT, 'MANIFEST.sha256'), 'w').write('\n'.join(rows) + '\n')
print('\n'.join(rows))
print('files: %d (+ manifest)   bytes: %d' % (count, total))
assert count + 1 <= 4096 and total < 128 * 1024 * 1024
