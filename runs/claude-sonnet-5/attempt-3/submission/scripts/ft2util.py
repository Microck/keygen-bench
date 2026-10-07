import subprocess, json, shlex

def call(tool, args):
    cmd = ["ft2", "call", tool, json.dumps(args)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ft2 call {tool} failed: {r.stdout}\n{r.stderr}")
    out = r.stdout.strip()
    try:
        obj = json.loads(out)
    except Exception:
        print("RAW:", out)
        raise
    if obj.get("isError"):
        raise RuntimeError(f"ft2 tool error: {obj}")
    text = obj["content"][0]["text"]
    try:
        return json.loads(text)
    except Exception:
        return text

def batch(calls):
    path = "/tmp/_batch.json"
    with open(path, "w") as f:
        json.dump(calls, f)
    cmd = ["ft2", "batch", path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ft2 batch failed: {r.stdout}\n{r.stderr}")
    return r.stdout
