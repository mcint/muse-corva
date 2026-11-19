---
title: Muse Corva — the app (manifest + persona)
date: 2026-11-18
kind: app
tldr: >
  MC's first GitHub App; acts as muse-corva[bot]. Catch-all repo permissions (no administration),
  private, no webhooks yet. Register via the manifest flow (spec in
  docs/specs/2026-11-18-muse-corva-app.md); key into the keychain, never git.
---
# Muse Corva

`manifest.json` is the registration source of truth (GitHub App manifest
format). No webhook: agents call the API; nothing listens yet.

## Persona
A magpie: active, inquisitive, collecting. It goes and looks, brings back
what it found, and says what it did, in its own name. Corvids are the
family; later apps can be other corvids with narrower jobs.

## Name
Display name **Muse Corva**, slug `muse-corva` (free as an account on
2026-11-18; the slug is only confirmed at registration). Considered: Mega
Cyb (`megacyb` is a taken account), mcfamiliar, mcmagpie, mcherald.
