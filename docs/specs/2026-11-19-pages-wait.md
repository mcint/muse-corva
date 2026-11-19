---
title: Spec — pages-wait, poll a Pages deploy gently and densely near the expected time
date: 2026-11-19
kind: spec
tldr: >
  scripts/pages-wait waits until GitHub Pages has built the expected commit
  (default: head of the Pages branch), or any new build as a backup. Probes
  once now, sparsely early, densely around the expected finish, then backs
  off. Expected time = build start (or now) + median recent duration +
  median logged queue delay; every run logs one line so estimates improve.
---
# Spec: pages-wait

## Want
"Is the site updated yet?" without hammering the API or guessing. MC
merges, runs `scripts/pages-wait`, gets a line per probe and an exit code.

## Observed (2026-11-19, mcint/muse-corva)
- Build `created_at` ≈ merge + 2 s; `duration` 34–40 s.
- Site `last-modified` = build `updated_at` (±1 s); `cache-control:
  max-age=600`, so the plain URL can be ~10 min stale at an edge.

## CLI
```
scripts/pages-wait [--repo o/r] [--commit SHA | --change] [--no-change]
                   [--offsets -10,-5,-2,0,2,5,10,20,40] [--sparse 20] [--tail 60]
                   [--timeout 900] [--live] [--dry-run]
```
- Target: `--commit` (short or full), else head of the Pages source branch.
- Stops on: target build finished, **or** (unless `--no-change`) any build
  that differs from the one seen at start and finished. `--change` = only
  the latter.
- `--live`: after building, also poll the site (cache-busted query) until
  `last-modified` ≥ build time − 2 s; report the plain URL's `age`.
- `--dry-run`: print the estimate and the probe schedule, don't poll.
- Exit: 0 built (and live, if asked); 1 build errored; 2 timeout.

## Estimate
- anchor = when the target landed on the branch (`GET /repos/{o}/{r}/activity?ref=<branch>`,
  PR merge or push; observed build start = landing + 1–2 s), else `created_at`
  of the target's build, else now.
- expected = anchor + median(queue delay from log, default 0)
  + median(last 20 built durations, default 40 s).
- Probe times: now; every `sparse` s until the first dense point; then
  expected + each offset (future ones only); then every `tail` s to timeout.

## Learning log
`$MUSE_CORVA_CACHE` (default `~/.cache/muse-corva`)`/pages-wait.jsonl`, one
JSON line per finished run: repo, commit, anchor, pushed, build created/updated,
queue_s (landing → build start), total_s (landing → built), duration_s, error_s (actual − expected), probes, outcome.

## Tests
`tests/test_pages_wait.py` (stdlib unittest, fake API + clock): schedule
shape, past points dropped, immediate stop when already built, stop on
target, stop on change, errored → 1, timeout → 2, log line written, live wait.
