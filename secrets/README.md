---
title: secrets/ — the only place secret files may live
date: 2026-11-18
kind: policy
tldr: >
  Gitignored except this README. Put local secret files here (e.g.
  muse-corva.pem) when the keychain won't do; scripts look here before the
  keychain. check.sh fails if anything here is tracked or if a secret
  pattern appears in any tracked file.
---
# secrets/

Everything in this directory except this README is ignored by git.

| file | used by | fallback |
|---|---|---|
| `muse-corva.pem` | `scripts/token.sh` (app private key) | keychain `muse-corva` / `private-key` |

Preferred home for long-lived secrets is still the macOS keychain;
use this directory for files tools need on disk, shared across this
checkout's worktrees by absolute path. Mode 0700 on the directory, 0600
on files.
