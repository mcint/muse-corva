---
title: Muse Corva — MC's magpie GitHub App
date: 2026-11-18
kind: readme
tldr: >
  Repo and GitHub Pages site for Muse Corva, the GitHub App that lets MC's
  agents act on GitHub as themselves (muse-corva[bot]), not as mcint.
  Persona: a magpie, active, inquisitive, collecting. Catch-all
  permissions to start; later corvid apps get narrower scopes, and the
  repo may become Maestro Corvidae once there are a few.
---
# Muse Corva

*The corvid muse: the whisper at the start.* Muse Corva is the GitHub App
that lets MC's agents push, comment and open PRs as `muse-corva[bot]`
instead of as `mcint`: a magpie that is active, inquisitive, and collects.
The Pages site ([mcint.github.io/muse-corva](https://mcint.github.io/muse-corva/))
lives on the **`gh-pages`** branch (worktree `.claude/worktrees/gh-pages`)
and is the app's homepage.

| path | what |
|---|---|
| [`RESPONSIBILITIES.md`](RESPONSIBILITIES.md) | what each app may do, who answers for it |
| [`apps/<slug>/`](apps/muse-corva/README.md) | per-app manifest + notes |
| `gh-pages` branch | Pages site (Jekyll, served from branch root) |
| [`docs/specs/`](docs/specs/) | specs (not published) |
| [`scripts/`](scripts/) | `register.py`, `token.sh`, `as-bot`; `check.sh`, `test.sh` |

## Use it (local-first)
```sh
uv run scripts/register.py          # once: click Create on GitHub; key -> keychain
# install on selected repos (URL printed), commit apps/muse-corva/app.json
scripts/as-bot gh issue comment 1 -R mcint/muse-corva -b "caw"
scripts/as-bot git push             # pushes and commits as muse-corva[bot]
scripts/token.sh owner/repo         # raw 1h installation token
scripts/test.sh && scripts/check.sh # tests + checks
```
Spec: [`docs/specs/2026-11-18-muse-corva-app.md`](docs/specs/2026-11-18-muse-corva-app.md).

Conventions: Conventional Commits, scope = top-level dir or app slug
(`feat(apps,muse-corva): …`). Frontmatter on every doc. Private keys never
in git (`*.pem` ignored); they live in the macOS keychain. Local intent:
`draft/intent` worktree at `.intent/` (never pushed). Agents: [CLAUDE.md](CLAUDE.md).

Lineage: `~/dev-llm/ClaudeCollab/agent-identity/seed.md` (bot account first,
App later; this repo starts at the "later").
