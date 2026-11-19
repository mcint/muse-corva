---
title: Spec — register and use Muse Corva
date: 2026-11-18
kind: spec
tldr: >
  Muse Corva is MC's main assistant app, the mask agents wear on GitHub.
  Register it locally via the manifest flow (scripts/register.py), keep the
  key in the macOS keychain, mint 1h installation tokens (scripts/token.sh),
  and run gh/git as muse-corva[bot] with scripts/as-bot. Broad permissions
  to start; no admin, checks or statuses.
---
# Spec: Muse Corva

## Want
MC's main assistant app: the mask agents wear so their comments, pushes,
PRs and other actions on GitHub show as `muse-corva[bot]`, separate from
MC. Local-first: no server, no webhooks; everything runs from MC's machine.
Tokens expire (1h); the only long-lived secret is the private key, in the
keychain.

## Surfaces
| command | does |
|---|---|
| `uv run scripts/register.py` | serves `http://localhost:8765/`, a form that POSTs `apps/muse-corva/manifest.json` (+ `redirect_url`) to `github.com/settings/apps/new?state=…`. MC clicks **Create**. The callback checks `state`, exchanges the code (`POST /app-manifests/{code}/conversions`), stores secrets in keychain service `muse-corva` (accounts `private-key` (PEM, base64), `client-secret`, `webhook-secret`) via `security -i` on stdin (never argv), writes non-secret `apps/muse-corva/app.json` (id, slug, client_id, html_url, owner, bot_user_id), prints the install URL, exits. `MUSE_CORVA_OWNER=<org>` registers under an org. |
| `scripts/token.sh --jwt` | prints an app JWT (RS256; `iat` = now−60, `exp` = now+540, `iss` = app id). |
| `scripts/token.sh [owner/repo]` | prints an installation token for that repo (default: `origin` of the current dir). |
| `scripts/as-bot <cmd…>` | runs `<cmd>` with `GH_TOKEN` set, git credentials for github.com answering with the token, and git author/committer `muse-corva[bot] <bot_user_id+muse-corva[bot]@users.noreply.github.com>`. |

Overrides (for tests and other machines): `MUSE_CORVA_APP_ID`,
`MUSE_CORVA_KEY_FILE` (PEM path instead of keychain).

## Default in Claude Code (decided 2026-11-18: MC wants the bot by default)
A user-level SessionStart hook runs `bin/session-start`, which appends
`export PATH="<repo>/bin:$PATH"` to `$CLAUDE_ENV_FILE` (Claude Code's Bash
tool only; MC's own terminal is untouched) and tells the session it acts as
`muse-corva[bot]`. No-op if `app.json` or `bin/` is missing.

| shim | behaviour |
|---|---|
| `bin/gh` | repo from `-R/--repo`, else `repos/<o>/<r>` in a `gh api` path, else `origin` of cwd. Installed → `GH_TOKEN` = repo-scoped token, exec real gh. Not installed / no repo → real gh as MC, one stderr line when a repo was named. `gh auth …` always passes through. |
| `bin/git` | only `commit merge rebase cherry-pick revert am tag push fetch pull`; others exec real git at once. Installed origin → bot author/committer + credential helper answering with the token. Else plain git. |

Tokens cached in `~/.cache/muse-corva/` (0600; 1h tokens reused until
5 min before expiry; "not installed" cached 1h). `MUSE_CORVA_OFF=1`
disables both shims. Test overrides: `MUSE_CORVA_REAL_GH`,
`MUSE_CORVA_REAL_GIT`, `MUSE_CORVA_TOKEN_CMD`, `MUSE_CORVA_CACHE`.

## Steps for MC
1. `uv run scripts/register.py`, click **Create GitHub App**.
2. Install on selected repos (URL printed). Protect `main` (PR required).
3. Commit `apps/muse-corva/app.json`.
4. Try: `scripts/as-bot gh issue comment <n> -R mcint/muse-corva -b "caw"`.

## Decided
- Bot is author *and* committer on as-bot commits (it contributes
  separately from MC); MC stays reviewer/merger.
- `"public": false`: installable only on MC's account.
- Webhook inactive (`hook_attributes.active: false`): nothing listens yet.

## Tests
- `scripts/check.sh`: manifest parses; required keys; no `administration`,
  `checks` or `statuses`; webhook inactive.
- `scripts/test-shims.sh`: shim routing with fake gh/git/token (installed,
  not installed, fast path, off switch, session-start).
- `scripts/test.sh`: JWT from a throwaway key has the right header and
  claims, a 600s window, and a signature that verifies with the public key.

## Open
- Commits outside Claude Code still author as MC (by design for now).
