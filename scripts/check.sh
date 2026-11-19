#!/bin/sh
# check: manifests parse with required keys and no administration grant;
# every markdown doc (except under docs/research/.gitkeep) has frontmatter.
set -eu
cd "$(dirname "$0")/.."
fail=0
for m in apps/*/manifest.json; do
  jq -e '.name and .url and .default_permissions.metadata' "$m" >/dev/null \
    || { echo "FAIL $m: missing name/url/metadata"; fail=1; }
  jq -e '.default_permissions | has("administration") | not' "$m" >/dev/null \
    || { echo "FAIL $m: grants administration (scope change: propose, don't apply)"; fail=1; }
  jq -e '(.hook_attributes.active // false) == false' "$m" >/dev/null \
    || { echo "FAIL $m: webhook active (nothing listens; local-first)"; fail=1; }
  for k in checks statuses; do
    jq -e --arg k "$k" '.default_permissions | has($k) | not' "$m" >/dev/null \
      || { echo "FAIL $m: grants $k (could forge required checks on its own PRs)"; fail=1; }
  done
done
for d in README.md RESPONSIBILITIES.md apps/*/README.md docs/specs/*.md; do
  [ "$(head -1 "$d")" = "---" ] || { echo "FAIL $d: no frontmatter"; fail=1; }
done
# secrets: only in secrets/ (untracked); no secret-shaped content anywhere tracked
for f in $(git ls-files secrets/ | grep -v '^secrets/README.md$'); do
  echo "FAIL $f: tracked under secrets/ (git rm --cached it)"; fail=1
done
for f in $(git ls-files '*.pem' '*.key' '*.p12' '.env*'); do
  echo "FAIL $f: key/env file tracked"; fail=1
done
pat='-----BEGIN ([A-Z]+ )*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-ant-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|xox[abprs]-[A-Za-z0-9-]{10,}'
hits=$(git ls-files -z | xargs -0 grep -IlE -e "$pat" 2>/dev/null || true)
for f in $hits; do echo "FAIL $f: secret-shaped content (move it to secrets/ or the keychain)"; fail=1; done
[ $fail -eq 0 ] && echo "check: ok"
exit $fail
