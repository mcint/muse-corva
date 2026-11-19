---
title: Muse Corva — home of MC's GitHub Apps
date: 2026-11-18
kind: readme
tldr: >
  Home repo and GitHub Pages site for the GitHub Apps that let MC's agents
  act on GitHub as themselves, not as mcint. First app: Mega Cyb
  (catch-all permissions, to start). Muse Corva is the name of the start
  and of the family; later apps get narrower scopes and their own names.
---
# Muse Corva

*The corvid muse: the whisper at the start.* Home for the GitHub Apps that
let MC's agents push, comment and open PRs as `<app>[bot]` instead of as
`mcint`. Private to start; the Pages site in [`docs/`](docs/index.md) is
each app's homepage.

| path | what |
|---|---|
| [`RESPONSIBILITIES.md`](RESPONSIBILITIES.md) | what each app may do, who answers for it |
| [`apps/<slug>/`](apps/mega-cyb/README.md) | per-app manifest + notes |
| [`docs/`](docs/index.md) | Pages site (Jekyll, served from `/docs`) |
| [`docs/specs/`](docs/specs/) | specs (excluded from the site) |
| [`scripts/check.sh`](scripts/check.sh) | `check`: manifests parse, docs carry frontmatter |

Conventions: Conventional Commits, scope = top-level dir or app slug
(`feat(apps,mega-cyb): …`). Frontmatter on every doc. Private keys never
in git (`*.pem` ignored); they live in the macOS keychain. Local intent:
`draft/intent` worktree at `.intent/` (never pushed). Agents: [CLAUDE.md](CLAUDE.md).

Lineage: `~/dev-llm/ClaudeCollab/agent-identity/seed.md` (bot account first,
App later; this repo starts at the "later").
