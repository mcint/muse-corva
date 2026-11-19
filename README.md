---
title: gh-pages — Muse Corva site
date: 2026-11-18
kind: readme
tldr: >
  Published site only (Jekyll, branch root). Source of truth for app docs
  is main; this branch carries what the world sees. Worktree:
  .claude/worktrees/gh-pages in the main checkout.
---
# gh-pages

Served by GitHub Pages from `gh-pages:/`. Edit here, commit, push.
`index.html` is hand-written (no Jekyll layout); `assets/dissolve-NN.png` are
32px frames of the logo transition (exact 1/16 of main's `art/transition/`).
The hero logo is a scrubber: live notch by default (`LIVE` in the script),
left→right hover/drag walks notches 0..10. Bump `LIVE` and `favicon.png`
when the app logo moves a notch.
README.md is excluded from the build.
