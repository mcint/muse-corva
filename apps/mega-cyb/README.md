---
title: Mega Cyb — catch-all agent app
date: 2026-11-18
kind: app
tldr: >
  First Muse Corva app. Catch-all repo permissions (no administration),
  private, no webhooks yet. Register via the manifest flow (spec in
  docs/specs/2026-11-18-mega-cyb.md); key into the keychain, never git.
---
# Mega Cyb

`manifest.json` is the registration source of truth (GitHub App manifest
format). No webhook: agents call the API; nothing listens yet.

Slug: `mega-cyb` (`megacyb` is an existing GitHub account, so "MegaCyb"
would collide).
