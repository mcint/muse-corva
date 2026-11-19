# CLAUDE.md — Muse Corva

Read README.md and RESPONSIBILITIES.md first.

## Rules for agents
- **Secrets:** never write, print or commit an app private key, client
  secret or installation token. Keys live in the keychain; tokens are
  minted on demand and expire (1h). `*.pem` and `.env*` are gitignored.
- **Permissions are scope; scope is MC's.** Changing an app's permissions,
  events, or installation targets is a trust-boundary change: propose it
  (diff the manifest + RESPONSIBILITIES.md), don't apply it on GitHub.
- **Pages source is `gh-pages:/` only**, never `main:/docs`: main's docs/
  holds unpublished specs and research. Enabling or changing Pages is MC's call.
- **Spec first** for any new app or new surface: `docs/specs/`, same commit
  at latest.
- **`check` before commit:** `scripts/check.sh` (needs `jq`); the
  pre-commit hook runs it, CI (`check`) runs it plus all `scripts/test*.sh`.
- **Secrets only in `secrets/`** (ignored) or the keychain. Never elsewhere.
- **Linear history:** rebase-merge only on `main`; `pull.rebase`/`merge.ff=only`
  locally. MC (admin) can bypass.
- **Intent:** `.intent/INTENT.md` (orphan `draft/intent`, worktree at
  `.claude/worktrees/intent`). `draft/*` branches are hook-enforced
  local-only (`core.hooksPath` → `.claude/worktrees/intent/hooks`).
  Refresh INTENT.md at session end.
- Commits: Conventional, scope = top-level dir or app slug, small; explain
  why. Co-Authored-By trailer on agent commits.
- Until an app is installed, agent comments via MC's `gh` end with
  `— Claude, working notes (agent) <!-- claude -->`.
