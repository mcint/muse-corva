#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# ///
"""pages-wait: wait for a GitHub Pages deploy, probing gently and densely near the expected time.

  scripts/pages-wait                  # wait for the Pages branch head (or any new build)
  scripts/pages-wait --commit abc123  # a specific commit
  scripts/pages-wait --change         # just: until the latest build changes
  scripts/pages-wait --live           # ...and until the site itself serves it
  scripts/pages-wait --dry-run        # show the estimate and probe schedule

Exit 0 built (and live, if asked), 1 build errored, 2 timeout.
Spec: docs/specs/2026-11-19-pages-wait.md. Learns from
$MUSE_CORVA_CACHE/pages-wait.jsonl (default ~/.cache/muse-corva).
"""
import argparse, datetime as dt, email.utils, json, os, pathlib, statistics, subprocess, sys, time
import urllib.request

DEFAULT_OFFSETS = [-10, -5, -2, 0, 2, 5, 10, 20, 40]
LIVE_OFFSETS = [0, 2, 5, 10, 20, 40]
FINISHED = ("built", "errored")


# ---- time helpers -----------------------------------------------------------
def iso(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def http_date(t):
    return email.utils.formatdate(t, usegmt=True)


def parse_http_date(s):
    return email.utils.parsedate_to_datetime(s).timestamp()


# ---- model ------------------------------------------------------------------
def probe_times(start, expected, offsets, sparse=20.0, tail=60.0, timeout=900.0):
    """Absolute probe times: now; every `sparse` s until the dense window; expected+offsets
    (future only); then every `tail` s until start+timeout."""
    times = [start]
    first_dense = expected + min(offsets)
    x = start + sparse
    while x < first_dense - 1:
        times.append(x)
        x += sparse
    for o in sorted(offsets):
        if expected + o > times[-1]:
            times.append(expected + o)
    x = times[-1] + tail
    while x <= start + timeout:
        times.append(x)
        x += tail
    return [t for t in times if t <= start + timeout]


def estimate(anchor, builds, log_rows):
    durs = [b["duration"] / 1000 for b in builds if b and b.get("status") == "built" and b.get("duration")][:20]
    queue = [r["queue_s"] for r in log_rows[-20:] if r.get("queue_s") is not None]
    return anchor + (statistics.median(queue) if queue else 0) + (statistics.median(durs) if durs else 40)


def key(b):
    return (b.get("commit"), b.get("updated_at")) if b else None


def decide(latest, target, baseline, any_change):
    """-> (stop, reason). Stops on the target finishing, or any other build finishing if any_change."""
    if not latest:
        return False, "no builds yet"
    st, c = latest.get("status"), latest.get("commit") or "?"
    if st not in FINISHED:
        return False, f"{st} {c[:7]}"
    if target and c == target:
        return True, f"{st} {c[:7]}"
    if any_change and key(latest) != baseline:
        return True, f"changed: {st} {c[:7]}"
    return False, f"{st} {c[:7]} (waiting for {target[:7] if target else 'a change'})"


# ---- io ---------------------------------------------------------------------
def gh_api(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip() or f"gh api {path} failed")
    return json.loads(r.stdout) if r.stdout.strip() else None


def http_head(url):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "pages-wait"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return {k.lower(): v for k, v in r.headers.items()}


def detect_repo():
    r = subprocess.run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
                       capture_output=True, text=True)
    if r.returncode or not r.stdout.strip():
        sys.exit("pages-wait: can't tell the repo; pass --repo owner/name")
    return r.stdout.strip()


def log_path():
    return pathlib.Path(os.environ.get("MUSE_CORVA_CACHE", pathlib.Path.home() / ".cache" / "muse-corva")) / "pages-wait.jsonl"


def read_log(repo):
    p = log_path()
    if not p.exists():
        return []
    rows = []
    for line in p.read_text().splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("repo") == repo:
            rows.append(row)
    return rows


def append_log(row):
    p = log_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(row) + "\n")


# ---- main -------------------------------------------------------------------
def parse(argv):
    ap = argparse.ArgumentParser(prog="pages-wait", description=__doc__.split("\n")[0])
    ap.add_argument("--repo", help="owner/name (default: current repo)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--commit", help="wait for this commit's build (default: Pages branch head)")
    g.add_argument("--change", action="store_true", help="only wait until the latest build changes")
    ap.add_argument("--no-change", action="store_true", help="don't stop on other builds; only the target")
    ap.add_argument("--offsets", default=",".join(map(str, DEFAULT_OFFSETS)),
                    help="dense probe offsets (s) around the expected time")
    ap.add_argument("--sparse", type=float, default=20, help="spacing (s) before the dense window")
    ap.add_argument("--tail", type=float, default=60, help="spacing (s) after the dense window")
    ap.add_argument("--timeout", type=float, default=900, help="give up after this many seconds")
    ap.add_argument("--live", action="store_true", help="also wait until the site serves the new build")
    ap.add_argument("--dry-run", action="store_true", help="print estimate and schedule; don't poll")
    return ap.parse_args(argv)


def main(argv=None, api=gh_api, now=time.time, sleep=time.sleep, out=print, head=None):
    a = parse(argv)
    head = head or http_head
    offsets = [float(x) for x in a.offsets.split(",") if x.strip()]
    repo = a.repo or detect_repo()
    pages = api(f"repos/{repo}/pages")
    branch, url = pages["source"]["branch"], pages["html_url"]
    target = None
    if a.commit:
        target = api(f"repos/{repo}/commits/{a.commit}")["sha"]
    elif not a.change:
        target = api(f"repos/{repo}/branches/{branch}")["commit"]["sha"]
    builds = api(f"repos/{repo}/pages/builds?per_page=30") or []
    latest = builds[0] if builds else None
    baseline = key(latest)
    start = now()
    deadline = start + a.timeout
    rows = read_log(repo)

    def live_phase(built_at):
        out(f"built; checking the site serves it ({url})")
        for o in LIVE_OFFSETS + [60 * i for i in range(2, 100)]:
            t = live_start + o
            if t > deadline:
                break
            sleep(max(0, t - now()))
            try:
                h = head(f"{url}?pages-wait={int(now())}")
                lm = parse_http_date(h["last-modified"])
            except Exception as e:  # network blips: keep going
                out(f"{now() - start:+7.1f}s  site check failed: {e}")
                continue
            if lm >= built_at - 2:
                try:
                    age = head(url).get("age", "?")
                except Exception:
                    age = "?"
                out(f"{now() - start:+7.1f}s  live (last-modified {iso(lm)}); plain URL cache age {age}s, max 600s")
                return now() - built_at
            out(f"{now() - start:+7.1f}s  site still serves {iso(lm)}")
        return None

    if target and latest and latest.get("commit") == target and latest.get("status") in FINISHED:
        out(f"already {latest['status']}: {target[:7]} at {latest.get('updated_at')}")
        if latest["status"] != "built":
            return 1
        if a.live:
            live_start = now()
            return 0 if live_phase(ts(latest["updated_at"])) is not None else 2
        return 0

    tb = next((b for b in builds if target and b.get("commit") == target), None)
    anchor = ts(tb["created_at"]) if tb else start
    expected = estimate(anchor, builds, rows)
    times = probe_times(start, expected, offsets, a.sparse, a.tail, a.timeout)
    what = f"{target[:7]} on {branch}" if target else f"a new build on {branch}"
    out(f"waiting for {what} ({repo}); expected in ~{expected - start:.0f}s; "
        f"{len(times) - 1} probes planned, timeout {a.timeout:.0f}s")
    if a.dry_run:
        out("probes at: " + " ".join(f"+{t - start:.0f}" for t in times[1:]))
        return 0

    any_change = (a.change or not a.no_change)
    probes = 0
    for t in times[1:]:
        sleep(max(0, t - now()))
        probes += 1
        try:
            latest = api(f"repos/{repo}/pages/builds/latest")
        except RuntimeError as e:
            out(f"{now() - start:+7.1f}s  api error: {e}")
            continue
        stop, reason = decide(latest, target, baseline, any_change)
        out(f"{now() - start:+7.1f}s  {reason}")
        if stop:
            break
    else:
        out(f"timeout after {now() - start:.0f}s ({probes} probes)")
        return 2

    created, updated = ts(latest["created_at"]), ts(latest["updated_at"])
    row = {"repo": repo, "target": target, "commit": latest["commit"], "anchor": anchor,
           "created": created, "updated": updated,
           "queue_s": (created - anchor) if latest["commit"] == target else None,
           "duration_s": (latest.get("duration") or (updated - created) * 1000) / 1000,
           "expected": expected, "error_s": updated - expected, "probes": probes,
           "outcome": latest["status"], "at": iso(now())}
    code = 0 if latest["status"] == "built" else 1
    if code == 0 and a.live:
        live_start = now()
        live_s = live_phase(updated)
        row["live_s"] = live_s
        if live_s is None:
            code = 2
    append_log(row)
    out(f"done: {latest['status']} {latest['commit'][:7]}; build {row['duration_s']:.0f}s, "
        f"estimate off by {row['error_s']:+.0f}s, {probes} probes")
    return code


if __name__ == "__main__":
    sys.exit(main())
