#!/usr/bin/env python3
"""Copy finished showcase campaigns into the private data root, verified by SHA-256.

Layout (user 2026-10-04): ~/keygen-data/ on this laptop, not a git checkout:
  campaigns/<YYYY-MM-DD>-<name>/   run root (campaign.lock.json, attempts, queue state) as `results/`,
                                   campaign.json (the frozen manifest from the lock) and the campaign's
                                   control inputs (selection, plan, tier spec, collected proofs) as `control/`
  inputs/  snapshots/  publications/  legacy/
Only campaigns of the showcased condition (max tier, prompt v2) are listed in CAMPAIGNS; everything
else goes to legacy/ separately. Originals on the controllers are never modified or removed.

  organize.py --dry-run      list every copy with its size; copies nothing
  organize.py                copy, then verify every file's SHA-256 against the source listing
Refuses to copy a campaign whose run root still has a RUNNING attempt (never-started RESERVED slots of
stopped campaigns are final and are copied as they are).
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

DATA = Path.home() / "keygen-data"
ASHBURN = ("ubuntu@100.92.22.120", "/home/ubuntu/keygen-full.OGHjBAkO")
PARIS = ("oracle-paris", "/home/ubuntu/keygen-full.eALj54bh")
# (target name, host, run root relative to the host base, control files relative to the host base)
CAMPAIGNS = [
    ("2026-10-01-ashburn-main", ASHBURN, "next-launch-20261001/results/next-max-tier-prompt-v2-ashburn-20261001",
     ["next-launch-20261001/launch-20261001"]),
    ("2026-10-01-oauth-repeats", PARIS, "oauth-repeats-20261001/results/next-max-tier-prompt-v2-oauth-repeats-20261001",
     ["oauth-repeats-20261001/control"]),
    ("2026-10-02-oauth-queue-1", ASHBURN, "oauth-queue-20261002/results/next-max-tier-prompt-v2-oauth-queue-20261002",
     ["oauth-queue-20261002/control"]),
    ("2026-10-02-oauth-queue-2", ASHBURN, "oauth-queue-2-20261002/results/next-max-tier-prompt-v2-oauth-queue-2-20261002",
     ["oauth-queue-2-20261002/control"]),
    ("2026-10-02-oauth-queue-3", ASHBURN, "oauth-queue-3-20261002/results/next-max-tier-prompt-v2-oauth-queue-3-20261002",
     ["oauth-queue-3-20261002/control"]),
    ("2026-10-01-paris-addon", PARIS, "go-three-20261002/results/next-max-tier-prompt-v2-paris-addon-20261001", []),
    ("2026-10-02-go-three", PARIS, "go-three-20261002/results/next-max-tier-prompt-v2-go-three-20261002",
     ["go-three-20261002/control"]),
    ("2026-10-02-go-exclusive", PARIS, "go-exclusive-20261002/results/next-max-tier-prompt-v2-go-exclusive-20261002",
     ["go-exclusive-20261002/control"]),
    ("2026-10-02-paris-addon-go-exclusive", PARIS,
     "go-exclusive-20261002/results/next-max-tier-prompt-v2-paris-addon-go-exclusive-20261002", []),
    ("2026-10-02-go-parallel", PARIS, "go-parallel-20261002/results/next-max-tier-prompt-v2-go-parallel-20261002",
     ["go-parallel-20261002/control"]),
    ("2026-10-02-paris-addon-go-parallel", PARIS,
     "go-parallel-20261002/results/next-max-tier-prompt-v2-paris-addon-go-parallel-20261002", []),
    ("2026-10-03-google", ASHBURN, "google-20261003/results/next-max-tier-prompt-v2-google-20261003",
     ["google-20261003/control", "google-20261003/rescore-3-flash-rep-1/rescore-record.json"]),
    ("2026-10-04-devin", ASHBURN, "devin-20261004/results/next-max-tier-prompt-v2-devin-20261004",
     ["devin-20261004/control"]),
    ("2026-10-04-devin-only", ASHBURN, "devin-20261004/results/next-max-tier-prompt-v2-devin-only-20261004", []),
    ("2026-10-04-devin-only-wide", ASHBURN,
     "devin-20261004/results/next-max-tier-prompt-v2-devin-only-wide-20261004", []),
    ("2026-10-04-devin-dense", ASHBURN, "devin-20261004/results/next-max-tier-prompt-v2-devin-dense-20261004", []),
    ("2026-10-04-devin-arm64", ASHBURN, "devin-20261004/results/next-max-tier-prompt-v2-devin-arm64-20261004", []),
    ("2026-10-05-go-arm64", PARIS, "go-arm64-20261005/results/next-max-tier-prompt-v2-go-arm64-20261005",
     ["go-arm64-20261005/control"]),
    ("2026-10-05-paris-addon-go-arm64", PARIS,
     "go-arm64-20261005/results/next-max-tier-prompt-v2-paris-addon-go-arm64-20261005", []),
    ("2026-10-05-go-hy4-cap32k", PARIS, "go-arm64-20261005/results/next-max-tier-prompt-v2-go-hy4-cap32k-20261005", []),
]
# Private material never copied: credentials, SSH keys, private logs stay on the controllers.
EXCLUDE = ["*.private.log", ".private/", "*.env.json", "isolated-host-home/", "__pycache__/", "*.lock"]
LISTING = r"""import hashlib,json,os,sys
root=sys.argv[1];skip=json.loads(sys.argv[2]);out={}
import fnmatch
for d,ds,fs in os.walk(root):
    rel=os.path.relpath(d,root)
    ds[:]=[x for x in ds if not any(fnmatch.fnmatch(x+'/',p) for p in skip)]
    for f in fs:
        if any(fnmatch.fnmatch(f,p) for p in skip): continue
        p=os.path.join(d,f)
        if os.path.islink(p): continue
        h=hashlib.sha256()
        with open(p,'rb') as s:
            for b in iter(lambda:s.read(1<<20),b''): h.update(b)
        out[os.path.normpath(os.path.join(rel,f))]=h.hexdigest()
print(json.dumps(out))"""


def remote(host, command, **kwargs):
    return subprocess.run(["ssh", "-o", "BatchMode=yes", host, command], capture_output=True, text=True,
                          check=True, timeout=1800, **kwargs).stdout


def listing(host, path):
    if host is None:
        return json.loads(subprocess.run([sys.executable, "-c", LISTING, str(path), json.dumps(EXCLUDE)],
                                         capture_output=True, text=True, check=True).stdout)
    return json.loads(remote(host, f"python3 -c {json.dumps(LISTING)} {path} '{json.dumps(EXCLUDE)}'"))


def pending(host, run_root):
    script = ("import glob,json,sys;print(sum(json.load(open(p)).get('status')=='RUNNING' "
              "for p in glob.glob(sys.argv[1]+'/*/status.json')))")
    return int(remote(host, f"python3 -c \"{script}\" {run_root}").strip() or 0)


def copy(host, source, target, dry):
    command = ["rsync", "-a", "--delete-excluded"] + [f"--exclude={p}" for p in EXCLUDE] + [
        f"{host}:{source}" + ("/" if not source.endswith(".json") else ""), str(target)]
    if dry:
        size = remote(host, f"du -sh {source} | cut -f1").strip()
        print(f"  {size:>6}  {host}:{source} -> {target}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(command, check=True, timeout=7200)
    if source.endswith(".json"):
        return
    expected, actual = listing(host, source), listing(None, target)
    if expected != actual:
        missing = sorted(set(expected) - set(actual))[:5]
        changed = sorted(k for k in set(expected) & set(actual) if expected[k] != actual[k])[:5]
        raise SystemExit(f"checksum mismatch for {source}: missing {missing} changed {changed}")
    print(f"  verified {len(actual)} files  {target}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    for name, (host, base), run_root, controls in CAMPAIGNS:
        source = f"{base}/{run_root}"
        exists = remote(host, f"test -f {source}/campaign.lock.json && echo yes || echo no").strip() == "yes"
        if not exists:
            print(f"{name}: no run root yet (skipped)")
            continue
        busy = pending(host, source)
        print(f"{name}:{' IN FLIGHT ' + str(busy) if busy else ''}")
        if busy and not args.dry_run:
            raise SystemExit(f"{name}: {busy} attempts still RUNNING; let them finish or recover the campaign first")
        target = DATA / "campaigns" / name
        copy(host, source, target / "results", args.dry_run)
        for control in controls:
            name_ = Path(control).name
            copy(host, f"{base}/{control}", target / "control" / ("" if name_ == "control" else name_), args.dry_run)
        if not args.dry_run:
            lock = json.loads((target / "results/campaign.lock.json").read_text())
            (target / "campaign.json").write_text(json.dumps(lock["snapshot"]["campaign"], indent=2) + "\n")
            (target / "SOURCE.json").write_text(json.dumps(
                {"host": host, "run_root": source, "controls": [f"{base}/{c}" for c in controls],
                 "campaign_id": lock["snapshot"]["campaign"]["campaign_id"],
                 "copied_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                indent=2) + "\n")


if __name__ == "__main__":
    main()
