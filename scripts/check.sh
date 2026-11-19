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
  for k in checks statuses; do
    jq -e --arg k "$k" '.default_permissions | has($k) | not' "$m" >/dev/null \
      || { echo "FAIL $m: grants $k (could forge required checks on its own PRs)"; fail=1; }
  done
done
for d in README.md RESPONSIBILITIES.md apps/*/README.md docs/*.md docs/specs/*.md; do
  [ "$(head -1 "$d")" = "---" ] || { echo "FAIL $d: no frontmatter"; fail=1; }
done
[ $fail -eq 0 ] && echo "check: ok"
exit $fail
