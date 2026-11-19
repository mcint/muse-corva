---
title: Responsibilities — what each app may do, and who answers for it
date: 2026-11-18
kind: policy
tldr: >
  MC owns every app and answers for its actions. Mega Cyb starts with
  catch-all repo permissions (minus administration) on selected repos;
  branch protection on main/dev, not the app's scope, is what keeps
  merges human. Narrowing happens per app later, visibly, in the manifest.
---
# Responsibilities

## Owner
MC (`mcint`) registers, installs and is accountable for every app here.
Apps act *for* MC, visibly *as themselves* (`<slug>[bot]`).

## Shared duties (all apps)
- **Act, attributed.** Push topic branches, open PRs, comment, label —
  under the app's name, never MC's.
- **Never merge to protected branches or approve PRs.** Approval is MC's
  act. Enforced by branch protection on `main`/`dev`, not by trust.
- **Short-lived credentials only.** Installation tokens (1h), minted from
  the keychain-held key on demand.
- **Install on selected repos**, never "all repositories" by default.

## Apps
| app | slug | scope (to start) | job | status |
|---|---|---|---|---|
| Mega Cyb | `mega-cyb` | catch-all: contents, PRs, issues, actions, workflows, checks, statuses, pages, discussions (write); no administration | general agent hands on MC's repos | spec'd, not registered |

## Narrowing later
Catch-all is a deliberate *start*, not the end state (see
`~/.claude/CLAUDE.md` → most-or-appropriate attenuation). When a job gets
its own app, it gets only that job's permissions, and Mega Cyb drops
them. Each change is a manifest diff + a row edit here.
