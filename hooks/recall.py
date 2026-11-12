"""Recall by meaning for the crew kit: a local embedding model as a second channel beside word matching (ck-3jk.2).

Nothing here calls a service: the model runs on this machine's CPU. All of it lives in one directory, $CREW_HOME
(default ~/.local/share/crewkit): recall.json (the switches), site/ (ONNX Runtime, tokenizers, numpy), model/
(EmbeddingGemma 300M, about 1.3 GB, under Google's Gemma terms) and vectors/ (one cache per project).

    recall.py setup               install the runtime and the model here, switch recall by meaning on, index this project
    recall.py status              what is installed and switched on, and where
    recall.py set <key> <value>   semantic on|off, commands every|failed|off, floor 0-1, command_floor 0-1
    recall.py test [--command] <text>   what that prompt (or command) would match by meaning, with scores
    recall.py index               embed this project's memories now (a lookup embeds only a few new ones at a time)
    recall.py worker              for memories.py: stdin {"query", "memories", "project", "budget"} -> [[key, score], ...]

A lookup starts a process, loads the model (about 1.5 s, 0.7 GB) and answers; at most two run at once on a machine,
and one that cannot get a turn within three seconds answers nothing, so word matching carries that call alone.
ponytail: a process per lookup; a resident one would answer in 30 ms, when the 1.5 s starts to hurt.
"""
import hashlib
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python3 -I leaves the script's directory out

REV = "5090578d9565bb06545b4552f76e6bc2c93e4a66"  # the revision measured on a real store (see the bead)
BASE = f"https://huggingface.co/onnx-community/embeddinggemma-300m-ONNX/resolve/{REV}/"
FILES = [  # remote path, local name, sha256, bytes
    ("tokenizer.json", "tokenizer.json", "4dda02faaf32bc91031dc8c88457ac272b00c1016cc679757d1c441b248b9c47", 20323312),
    ("onnx/model.onnx", "model.onnx", "ea91fd315a7c152d427d231746f0f811a1ac93beaba656abfdf2b24e091265e4", 479932),
    ("onnx/model.onnx_data", "model.onnx_data", "ef835ae565d8695236652475903078e8ed794c7c35faf1164d78ec3238e8a88d", 1234521088),
]
PACKAGES = ["onnxruntime==1.31.1", "tokenizers==0.23.3", "numpy==2.5.4"]
MODEL_ID = "embeddinggemma-300m@" + REV[:8]
QUERY, DOC = "task: search result | query: ", "title: none | text: "  # the prefixes this model was trained with
# The floors are cosine similarities measured on one real store of 91 memories: no unrelated prompt scored over 0.35,
# and plain commands (git status, make build) score up to 0.5 against the memories about their tool.
DEFAULTS = {"semantic": True, "commands": "every", "floor": 0.40, "command_floor": 0.45}
CHOICES = {"semantic": ("on", "off"), "commands": ("every", "failed", "off")}


def home():
    return os.environ.get("CREW_HOME") or os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "crewkit")


def config():
    c = dict(DEFAULTS)
    try:
        c.update({k: v for k, v in json.load(open(os.path.join(home(), "recall.json"))).items() if k in DEFAULTS})
    except Exception:
        pass
    return c


def ready():
    h = home()
    return os.path.isdir(os.path.join(h, "site", "onnxruntime")) and all(
        os.path.exists(os.path.join(h, "model", name)) for _, name, _, _ in FILES)


def on():
    return bool(config()["semantic"]) and ready()


def ask(mems, query, timeout=8, budget=3):
    """[(key, score)] by meaning, best first. None when recall by meaning is off, not installed, or did not answer."""
    if not (on() and mems and query.strip()):
        return None
    req = json.dumps({"query": query, "memories": mems, "project": os.getcwd(), "budget": budget})
    try:
        out = subprocess.run([sys.executable, "-I", os.path.abspath(__file__), "worker"], input=req,
                             capture_output=True, text=True, timeout=timeout).stdout
        return [(k, s) for k, s in json.loads(out)]
    except Exception:
        return None


def slot(wait):
    """One of two locks: at most two models in memory at once on this machine, however many sessions ask. None: busy."""
    import fcntl
    end = time.monotonic() + wait
    while True:
        for i in (0, 1):
            f = open(os.path.join(home(), f"slot{i}.lock"), "w")
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return f
            except OSError:
                f.close()
        if time.monotonic() > end:
            return None
        time.sleep(0.1)


def load():
    """numpy, and embed(text) -> unit vector. The only place the runtime and the model are touched."""
    sys.path.insert(0, os.path.join(home(), "site"))
    import numpy as np
    import onnxruntime as ort
    from tokenizers import Tokenizer
    m = os.path.join(home(), "model")
    tok = Tokenizer.from_file(os.path.join(m, "tokenizer.json"))
    tok.no_padding()
    tok.enable_truncation(max_length=1024)
    so = ort.SessionOptions()
    so.log_severity_level = 3
    so.intra_op_num_threads = min(4, os.cpu_count() or 1)
    sess = ort.InferenceSession(os.path.join(m, "model.onnx"), so, providers=["CPUExecutionProvider"])

    def embed(text):
        ids = np.array([tok.encode(text).ids], dtype=np.int64)
        v = sess.run(["sentence_embedding"], {"input_ids": ids, "attention_mask": np.ones_like(ids)})[0][0]
        return (v / np.linalg.norm(v)).astype(np.float32)
    return np, embed


def vectors(np, embed, mems, project, budget):
    """({key: vector}, how many were new). Memories the project's cache lacks are embedded until the budget (seconds,
    None for no limit) runs out; the rest are left for the next call and are not candidates in this one."""
    path = os.path.join(home(), "vectors", hashlib.sha256(project.encode()).hexdigest()[:16] + ".npz")
    ident = lambda k, v: hashlib.sha256((MODEL_ID + "\0" + k + "\0" + v).encode()).hexdigest()[:24]
    have = {}
    try:
        z = np.load(path)
        have = dict(zip(z["ids"].tolist(), z["vecs"]))
    except Exception:
        pass
    out, new, t0 = {}, 0, time.monotonic()
    for k, v in mems.items():
        i = ident(k, v)
        if i not in have:
            if budget is not None and time.monotonic() - t0 > budget:
                continue
            have[i] = embed(DOC + k.replace("-", " ") + ". " + v)
            new += 1
        out[k] = have[i]
    if new:  # the cache holds this store's current memories only; written whole and renamed into place
        ids = [i for i in {ident(k, v) for k, v in mems.items()} if i in have]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.{os.getpid()}.npz"
        np.savez(tmp, ids=np.array(ids), vecs=np.stack([have[i] for i in ids]))
        os.replace(tmp, path)
    return out, new


def worker():
    req = json.load(sys.stdin)
    if slot(3) is None:
        print("[]")
        return
    np, embed = load()
    vec, _ = vectors(np, embed, req["memories"], req.get("project", ""), req.get("budget", 3))
    if not vec:
        print("[]")
        return
    q = embed(QUERY + req["query"][:4000])
    best = sorted(((float(v @ q), k) for k, v in vec.items()), reverse=True)[:8]
    print(json.dumps([[k, round(s, 4)] for s, k in best]))


def fetch(url, dst, sha):
    """Download to dst through a temporary file, checking the sha256 before it takes the name."""
    import urllib.request
    tmp, h, got = dst + ".part", hashlib.sha256(), 0
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "crewkit"}), timeout=60) as r, open(tmp, "wb") as f:
        total, step = int(r.headers.get("Content-Length") or 0), 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            h.update(chunk)
            got += len(chunk)
            if total and got * 10 // total > step:
                step = got * 10 // total
                print(f"    {step * 10}%", flush=True)
    if h.hexdigest() != sha:
        os.remove(tmp)
        sys.exit(f"crew-recall: {os.path.basename(dst)} did not match its checksum; nothing was installed from it. Run setup again.")
    os.replace(tmp, dst)


def store():
    from memories import memories
    return memories()


def setup():
    h = home()
    os.makedirs(os.path.join(h, "model"), exist_ok=True)
    print(f"crew-recall: installing into {h} (the model is EmbeddingGemma 300M, under Google's Gemma terms)")
    if not os.path.isdir(os.path.join(h, "site", "onnxruntime")):
        print("  runtime: " + " ".join(PACKAGES))
        r = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
                            "--no-warn-conflicts", "--root-user-action=ignore", "--target", os.path.join(h, "site")] + PACKAGES)
        if r.returncode:
            sys.exit("crew-recall: pip could not install the runtime (is pip for python3 installed?). Recall stays by word.")
    for remote, name, sha, size in FILES:
        dst = os.path.join(h, "model", name)
        if not (os.path.exists(dst) and os.path.getsize(dst) == size):
            print(f"  {name}: {size / 1e6:.0f} MB")
            fetch(BASE + remote, dst, sha)
    if not os.path.exists(os.path.join(h, "recall.json")):
        save(dict(DEFAULTS))
    t = time.monotonic()
    got = ask({"setup-check": "The dev server always sends gzip; pass --compressed to curl."}, "curl prints binary garbage", timeout=120)
    if not got:
        sys.exit("crew-recall: installed, but a test lookup gave nothing. Run `crew-recall status`; recall stays by word.")
    print(f"  a test lookup answered in {time.monotonic() - t:.1f} s")
    index()
    status()


def save(c):
    p = os.path.join(home(), "recall.json")
    os.makedirs(home(), exist_ok=True)
    with open(p + ".tmp", "w") as f:
        json.dump(c, f, indent=2)
        f.write("\n")
    os.replace(p + ".tmp", p)


def set_(key, value):
    c = config()
    if key in CHOICES and value in CHOICES[key]:
        c[key] = (value == "on") if key == "semantic" else value
    elif key in ("floor", "command_floor") and value.replace(".", "", 1).isdigit() and 0 <= float(value) <= 1:
        c[key] = float(value)
    else:
        sys.exit("usage: crew-recall set semantic on|off | commands every|failed|off | floor 0-1 | command_floor 0-1")
    save(c)
    status()


def status():
    c, h = config(), home()
    size = lambda d: sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(os.path.join(h, d)) for f in fs if not os.path.islink(os.path.join(r, f))) / 1e9
    print(f"crew-recall: {h}")
    print(f"  installed: {'yes' if ready() else 'no (crew-recall setup; about 1.5 GB)'}" + (f", runtime {size('site'):.2f} GB, model {size('model'):.2f} GB ({MODEL_ID})" if ready() else ""))
    print(f"  semantic: {'on' if c['semantic'] else 'off'}" + ("" if ready() or not c["semantic"] else " (waiting for setup: recall is by word only)"))
    print(f"  commands: {c['commands']} (every: a lookup with each Bash command; failed: only when one fails; off: prompts only)")
    print(f"  floor: {c['floor']} for prompts and error text, {c['command_floor']} for commands")


def index():
    if not on():
        return
    mems = store()
    if not mems or slot(60) is None:
        return
    np, embed = load()
    t = time.monotonic()
    vec, new = vectors(np, embed, mems, os.getcwd(), None)
    if sys.stdout.isatty() or new:
        print(f"  {len(vec)} memories indexed for {os.getcwd()} ({new} new, {time.monotonic() - t:.1f} s)")


def test(args):
    command = args[:1] == ["--command"]
    text = " ".join(args[1:] if command else args)
    c = config()
    floor = c["command_floor"] if command else c["floor"]
    t = time.monotonic()
    got = ask(store(), text, timeout=120, budget=None)
    if got is None:
        sys.exit("crew-recall: recall by meaning is off, not installed, or gave no answer (crew-recall status)")
    print(f"by meaning, {time.monotonic() - t:.1f} s, floor {floor}:")
    for k, s in got:
        print(f"  {s:.2f} {'*' if s >= floor else ' '} {k}")


if __name__ == "__main__":
    a = sys.argv[1:]
    cmd = a[0] if a else "status"
    if cmd == "worker": worker()
    elif cmd == "setup": setup()
    elif cmd == "set" and len(a) == 3: set_(a[1], a[2])
    elif cmd == "index": index()
    elif cmd == "test" and len(a) > 1: test(a[1:])
    elif cmd == "status": status()
    else: sys.exit(__doc__.split("\n\n")[2])
