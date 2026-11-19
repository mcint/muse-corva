#!/usr/bin/env bash
# test-check: check.sh catches planted secrets in a scratch copy of the repo.
set -uo pipefail
cd "$(dirname "$0")/.."
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
fail=0; ok(){ echo "ok   $1"; }; no(){ echo "FAIL $1"; fail=1; }
fresh(){ rm -rf "$t/r"; mkdir "$t/r"; git ls-files -z | xargs -0 tar -cf - | tar -xf - -C "$t/r"
  ( cd "$t/r" && git init -q && git add -A ) ; }
run(){ ( cd "$t/r" && scripts/check.sh >/dev/null 2>&1 ); }

fresh; run && ok "clean copy passes" || no "clean copy passes"
fresh; printf 'token: ghs_%s\n' "$(printf 'a%.0s' {1..36})" > "$t/r/notes.md"; (cd "$t/r" && git add notes.md)
run && no "github token in tracked file" || ok "github token in tracked file"
fresh; hdr="-----BEGIN RSA PRIV""ATE KEY-----"; printf -- '%s\nMIIE\n' "$hdr" > "$t/r/apps/k.txt"; (cd "$t/r" && git add apps/k.txt)
run && no "private key block" || ok "private key block"
fresh; echo x > "$t/r/secrets/app.pem"; (cd "$t/r" && git add -f secrets/app.pem)
run && no "file tracked under secrets/" || ok "file tracked under secrets/"
fresh; echo x > "$t/r/deploy.key"; (cd "$t/r" && git add -f deploy.key)
run && no "tracked .key file" || ok "tracked .key file"
fresh; echo x > "$t/r/secrets/app.pem"
run && ok "untracked file in secrets/ is fine" || no "untracked file in secrets/ is fine"
exit $fail
