#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# ///
"""activity: view or follow a repo's push/merge activity.

  scripts/activity                         # last 10 events, oldest first
  scripts/activity --ref gh-pages          # one branch
  scripts/activity --follow                # tail new events (idle backoff 10s -> 120s)
  scripts/activity --follow --count 1      # wait for the next push/merge, then exit
  scripts/activity --json | jq ...         # JSONL

Exit 0 ok, 2 timeout, 130 interrupted. Spec: docs/specs/2026-11-19-activity.md.
"""
import argparse, datetime as dt, json, subprocess, sys, time


def iso(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def gh_api(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip() or f"gh api {path} failed")
    return json.loads(r.stdout) if r.stdout.strip() else []


def detect_repo():
    r = subprocess.run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
                       capture_output=True, text=True)
    if r.returncode or not r.stdout.strip():
        sys.exit("activity: can't tell the repo; pass --repo owner/name")
    return r.stdout.strip()


def line(e):
    when = e.get("timestamp", "")[:19].replace("T", " ")
    ref = (e.get("ref") or "").replace("refs/heads/", "").replace("refs/tags/", "tag:")
    sha = lambda s: (s or "")[:7] or "-------"
    who = (e.get("actor") or {}).get("login", "?")
    return f"{when}  {e.get('activity_type', '?'):<15} {ref:<14} {sha(e.get('before'))}→{sha(e.get('after'))}  {who}"


def parse(argv):
    ap = argparse.ArgumentParser(prog="activity", description=__doc__.split("\n")[0])
    ap.add_argument("--repo", help="owner/name (default: current repo)")
    ap.add_argument("--ref", help="only this branch (name or refs/heads/...)")
    ap.add_argument("--limit", type=int, default=10, help="recent events to show first (0 = none)")
    ap.add_argument("--json", action="store_true", help="JSON lines, API fields as-is")
    ap.add_argument("--follow", action="store_true", help="keep polling and print new events")
    ap.add_argument("--count", type=int, help="with --follow: exit after N new events")
    ap.add_argument("--interval", type=float, default=10, help="base poll interval (s)")
    ap.add_argument("--max-interval", type=float, default=120, help="idle backoff cap (s)")
    ap.add_argument("--timeout", type=float, help="with --follow: give up after S seconds (exit 2)")
    return ap.parse_args(argv)


def main(argv=None, api=gh_api, now=time.time, sleep=time.sleep, out=print):
    a = parse(argv)
    repo = a.repo or detect_repo()
    path = f"repos/{repo}/activity?per_page={max(a.limit, 30)}" + (f"&ref={a.ref}" if a.ref else "")
    show = (lambda e: out(json.dumps(e))) if a.json else (lambda e: out(line(e)))

    events = api(path) or []
    for e in list(reversed(events))[-a.limit:] if a.limit > 0 else []:
        show(e)
    if not a.follow:
        return 0

    seen = {e.get("id") for e in events}
    start, interval, got = now(), a.interval, 0
    deadline = start + a.timeout if a.timeout else None
    try:
        while True:
            wait = interval
            if deadline is not None:
                if now() >= deadline:
                    return 2
                wait = min(wait, deadline - now())
            sleep(wait)
            try:
                events = api(path) or []
            except RuntimeError as e:
                print(f"activity: {e}", file=sys.stderr)
                interval = min(interval * 2, a.max_interval)
                continue
            new = [e for e in reversed(events) if e.get("id") not in seen]
            for e in new:
                seen.add(e.get("id"))
                show(e)
                got += 1
                if a.count and got >= a.count:
                    return 0
            interval = a.interval if new else min(interval * 2, a.max_interval)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
