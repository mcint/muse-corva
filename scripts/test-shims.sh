#!/usr/bin/env bash
# test-shims: bin/gh, bin/git, bin/session-start routing, with fakes (no network).
set -uo pipefail
cd "$(dirname "$0")/.."
root=$PWD
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
fail=0; ok(){ echo "ok   $1"; }; no(){ echo "FAIL $1"; fail=1; }

# fakes: real gh/git print what they saw; token minter knows one installed repo
cat > "$t/gh" <<'F'
#!/bin/sh
echo "gh GH_TOKEN=${GH_TOKEN:-none} args=$*"
F
cat > "$t/git" <<'F'
#!/bin/sh
case "$1" in remote) echo "https://github.com/${FAKE_ORIGIN:-mcint/muse-corva}.git"; exit 0;; esac
echo "git author=${GIT_AUTHOR_NAME:-me} cfg=${GIT_CONFIG_COUNT:-0} args=$*"
F
cat > "$t/token" <<'F'
#!/bin/sh
echo call >> "$MUSE_CORVA_CACHE/calls"
[ "$1" = mcint/muse-corva ] && { echo "tok-$1"; exit 0; }
echo "not installed on $1" >&2; exit 1
F
chmod +x "$t/gh" "$t/git" "$t/token"
export MUSE_CORVA_REAL_GH=$t/gh MUSE_CORVA_REAL_GIT=$t/git MUSE_CORVA_TOKEN_CMD=$t/token
export MUSE_CORVA_CACHE=$t/cache
calls(){ if [ -f "$MUSE_CORVA_CACHE/calls" ]; then wc -l < "$MUSE_CORVA_CACHE/calls" | tr -d ' '; else echo 0; fi; }

out=$(bin/gh issue list -R mcint/muse-corva 2>&1)
[[ $out == *"GH_TOKEN=tok-mcint/muse-corva"* ]] && ok "gh -R installed -> bot token" || no "gh -R installed -> bot token ($out)"
out=$(bin/gh api repos/mcint/muse-corva/issues 2>&1)
[[ $out == *"GH_TOKEN=tok-mcint/muse-corva"* ]] && ok "gh api repos/o/r -> bot token" || no "gh api path ($out)"
out=$(bin/gh pr view --repo other/thing 2>&1)
[[ $out == *"GH_TOKEN=none"* && $out == *"acting as you"* ]] && ok "not installed -> MC, with note" || no "not installed fallback ($out)"
n=$(calls); bin/gh pr view --repo other/thing >/dev/null 2>&1
[ "$(calls)" = "$n" ] && ok "not-installed cached" || no "not-installed cached"
n=$(calls); bin/gh issue list -R mcint/muse-corva >/dev/null 2>&1
[ "$(calls)" = "$n" ] && ok "token cached" || no "token cached"
out=$(bin/gh auth status 2>&1)
[[ $out == *"GH_TOKEN=none"* ]] && ok "gh auth passes through" || no "gh auth passthrough ($out)"
out=$(bin/gh issue list 2>&1)
[[ $out == *"GH_TOKEN=tok-mcint/muse-corva"* ]] && ok "gh repo from origin" || no "gh from origin ($out)"
out=$(MUSE_CORVA_OFF=1 bin/gh issue list -R mcint/muse-corva 2>&1)
[[ $out == *"GH_TOKEN=none"* ]] && ok "MUSE_CORVA_OFF=1 -> MC" || no "off switch ($out)"

rm -rf "$MUSE_CORVA_CACHE"
out=$(bin/git status 2>&1)
[[ $out == *"author=me"* ]] && [ "$(calls)" = 0 ] && ok "git status fast path (no mint)" || no "git fast path ($out, calls=$(calls))"
out=$(bin/git commit -m x 2>&1)
[[ $out == *"author=muse-corva[bot]"* && $out == *"cfg=3"* ]] && ok "git commit -> bot author + creds" || no "git commit bot ($out)"
out=$(FAKE_ORIGIN=other/thing bin/git push 2>&1)
[[ $out == *"author=me"* && $out == *"cfg=0"* ]] && ok "git push not installed -> plain" || no "git push fallback ($out)"

env_file=$t/envfile; : > "$env_file"
CLAUDE_ENV_FILE=$env_file bin/session-start < /dev/null > "$t/ss.out"
grep -q "export PATH=\"$root/bin:" "$env_file" && ok "session-start prepends PATH" || no "session-start PATH ($(cat "$env_file"))"
grep -q muse-corva "$t/ss.out" && ok "session-start tells the session" || no "session-start context"
exit $fail
