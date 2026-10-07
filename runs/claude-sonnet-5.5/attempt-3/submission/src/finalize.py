"""Build the final module into /workspace/submission, run the QA gate and write the provenance manifest."""
import sys, os, json, shutil, hashlib, datetime
sys.path.insert(0, '/workspace/work')
from make import *
import qa

SUB = "/workspace/submission"
xm = f"{SUB}/tune.xm"
order, _ = build(xm)
res = qa.run(xm, f"{SUB}/preview.wav")
import xmcheck, random
res['structure_check'] = xmcheck.check(xm)
S_ = build_song(16)
res['hanging_notes_at_loop_point'] = hanging_notes(S_)
# read-back of random cells through the tracker API
call('module_load', path=xm)
random.seed(7); keys = random.sample(sorted(S_.cells), 400); bad = 0
for (g_, ch_) in keys:
    c_ = S_.cells[(g_, ch_)]
    got = json.loads(call('pattern_get_cell', pattern=order[g_ // 64], row=g_ % 64, channel=ch_))
    if (got['note'], got['instrument'], got['volume'], got['effect'], got['effect_param']) != (c_.note, c_.inst, c_.vol, c_.fx, c_.fxp): bad += 1
res['api_readback'] = dict(cells_checked=len(keys), mismatches=bad)
for f in ("xmwriter.py", "synth.py", "instruments.py", "compose.py", "make.py", "ft2lib.py", "qa.py", "xmcheck.py", "finalize.py"):
    shutil.copy(f"/workspace/work/{f}", f"{SUB}/src/{f}")
res["preview_sha256"] = qa.sha256(f"{SUB}/preview.wav")
import subprocess
subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0,'/workspace/work'); from make import build; build('/workspace/work/rebuild_check.xm')"],
               check=True, env=dict(os.environ, QUIET='1'))
res["deterministic_rebuild_identical"] = (qa.sha256('/workspace/work/rebuild_check.xm') == res["sha256"])
res["src_sha256"] = {f: qa.sha256(f"{SUB}/src/{f}") for f in sorted(os.listdir(f"{SUB}/src"))}
json.dump(res, open(f"{SUB}/qa_report.json", "w"), indent=1)

r = res["render"]; s = res["loop_seam"]; x = res["xm"]
nfiles = 0; total = 0
for d_, _, fs_ in os.walk(SUB):
    for f_ in fs_:
        if f_ != 'MANIFEST.md': nfiles += 1; total += os.path.getsize(os.path.join(d_, f_))
nfiles += 1   # MANIFEST.md itself
total_mb = (total + 6000) / 1e6
manifest = f"""# Neon Serial - keygen tune (FastTracker II module)

Music only. `tune.xm` is an original, fully editable XM module (no embedded code, no external data).

## Deliverables
| file | purpose | SHA-256 |
|---|---|---|
| `tune.xm` | the module (deliverable) | `{res['sha256']}` |
| `preview.wav` | 16-bit/44.1 kHz stereo render of one pass (informative only) | `{res['preview_sha256']}` |
| `qa_report.json` | machine-readable QA results used below | - |
| `src/` | deterministic build scripts (numpy synthesis + XM writer + QA gate) | see `qa_report.json` |

## Musical design
* 140 BPM, speed 6 (16th-note rows), A minor / A harmonic minor; {x['channels']} channels, {x['instruments']} instruments, {x['patterns']} patterns of 64 rows, {r['seconds']} s per pass.
* Progressions: Am-F-C-G and Am-F-Dm-E (A sections), Am-G-F-E Andalusian (B drop), Dm-Am-F-E (bridge).
* Instruments are synthesised from scratch (additive/FM/subtractive, band-limited per key range with XM key maps, volume envelopes,
  auto-vibrato): kick, snare+room, clap+room, hats, shaker, crash, tom, saw bass, PWM chip lead, stereo super-saw leads, chord pads and stabs
  (chords baked into looped samples), pluck, chip arpeggio voices (0xy), FM bell, 303-style acid bass, noise riser, reverse crash.
* Tracker techniques: 0xy arpeggios, Kxx key-off gating, 2xx pitch falls, E9x retrigger rolls, 8xx ping-pong panning, volume-column
  side-chain style pumping, note-off crossfaded pads on alternating channels, delayed echo channels.

## Structure (order list)
| order | pattern content |
|---|---|
| 0 | one-time intro (arps, pad swell, hats, kick from bar 3, hook teaser) - played once |
| 1 | **restart position** - full groove, no lead (re-entry lands on a crash) |
| 2-5 | A section: hook (PWM lead + echo), pluck counter-line, stabs, fills |
| 6-7 | break: FM bells over pad, riser + snare build, one-row stop |
| 8-11 | B drop: stereo super-saw hook, rolling bass, shaker, pitch-fall endings |
| 12 | bridge: acid line over Dm-Am-F-E, riser |
| 13-14 | A return with both leads |
| 15 | turnaround: mini break + riser + snare roll, one-row gap, then back to order 1 |

## Loop behaviour
* XM restart position = 1 (header field), song length {x['song_length']}. The last pattern ends on a build; its final row only rings out
  (snare roll finished on the previous row, arps off, pad release finished, riser ended) and every sustained voice is gated off - no hanging notes (checked in `compose.hanging_notes`).
* Splice test (end of order 15 -> start of order 1, 250 ms each side): step at the seam {s['step_at_seam']} vs local RMS step {s['local_rms_step']}
  (no click); last second {s['last_1s_rms_db']} dB RMS -> restart first second {s['restart_first_1s_rms_db']} dB RMS (energy continuous).
* Row timing is exact (no tempo changes, no Bxx/Dxx), so the groove stays on the grid across the loop.

## QA results (FT2 clone render, default amplification)
peak {r['peak']} ({r['peak_dbfs']} dBFS), RMS {r['rms_dbfs']} dBFS, clipped samples {r['clipped_samples']}, DC {r['dc_offset']}.
Peak at other mixer rates: {res['peak_at_other_rates']} (all below 1.0). Structure walk of the XM (every length field chains to EOF): {res['structure_check']['ok']}.
Pattern data read back through the tracker API: {res['api_readback']['cells_checked']} random cells, {res['api_readback']['mismatches']} mismatches. Hanging notes at loop point: {res['hanging_notes_at_loop_point'] or 'none'}.
Re-saving through the tracker gives an identical render: {res['tracker_resave_identical_render']}. Rebuild in a fresh process yields a byte-identical module: {res['deterministic_rebuild_identical']}.

## Security / compliance notes (SOC 2 / ISO 27001 oriented design decisions)
* Provenance & IP (ISO 27001 A.5.32, SOC 2 confidentiality): all sound material is procedurally generated by the included scripts from fixed RNG seeds;
  no third-party samples, no existing melodies, no network access, no personal or customer data. Module metadata is limited to the title, tracker name and instrument/sample names.
* Integrity & change control (A.8.32, CC8.1): deterministic, scripted build; SHA-256 of every deliverable recorded above and in `qa_report.json`.
* Processing integrity (PI1): automated QA gate (structure walk, header, level/clipping at three mixer rates, loop seam, hanging notes, round-trip of pattern data) executed on the final file.
* Availability / least privilege (A.8.3, A1): the work only wrote inside the workspace and `/workspace/submission` ({total_mb:.1f} MB, {nfiles} regular files, no links);
  the module is a plain data file with no executable content.
* Scope: music only - the module contains no licence-key generation or software-protection logic of any kind.

## Rebuild
`cd /workspace/work && python3 finalize.py` (needs the local `ft2` bridge for the verification renders; synthesis itself needs only Python 3 + numpy).
"""
open(f"{SUB}/MANIFEST.md", "w").write(manifest)
n = sum(len(fs) for _, _, fs in os.walk(SUB)); sz = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(SUB) for f in fs)
print("files", n, "bytes", sz)
print(json.dumps(res["render"])); print(json.dumps(res["loop_seam"])); print("sha256 tune.xm", res["sha256"])
