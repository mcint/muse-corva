#!/usr/bin/env bash
# test: token.sh --jwt with a throwaway key -> header, claims, window, signature.
set -euo pipefail
cd "$(dirname "$0")/.."
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
openssl genrsa -out "$t/key.pem" 2048 2>/dev/null
openssl rsa -in "$t/key.pem" -pubout -out "$t/pub.pem" 2>/dev/null
b64d(){ local s; s=$(tr '_-' '/+'); while [ $(( ${#s} % 4 )) -ne 0 ]; do s="$s="; done; printf '%s' "$s" | openssl base64 -d -A; }
fail=0; ok(){ echo "ok   $1"; }; no(){ echo "FAIL $1"; fail=1; }

jwt=$(MUSE_CORVA_APP_ID=4242 MUSE_CORVA_KEY_FILE="$t/key.pem" scripts/token.sh --jwt) || { no "token.sh --jwt runs"; exit 1; }
IFS=. read -r h p s <<<"$jwt"
[ "$(printf '%s' "$h" | b64d | jq -c .)" = '{"alg":"RS256","typ":"JWT"}' ] && ok header || no header
claims=$(printf '%s' "$p" | b64d)
[ "$(jq -r .iss <<<"$claims")" = 4242 ] && ok "iss = app id" || no "iss = app id"
[ "$(jq '.exp - .iat' <<<"$claims")" = 600 ] && ok "600s window" || no "600s window"
now=$(date +%s); iat=$(jq .iat <<<"$claims")
[ $((now - iat)) -ge 55 ] && [ $((now - iat)) -le 65 ] && ok "iat backdated 60s" || no "iat backdated 60s"
printf '%s' "$s" | b64d > "$t/sig"
printf '%s.%s' "$h" "$p" | openssl dgst -sha256 -verify "$t/pub.pem" -signature "$t/sig" >/dev/null && ok signature || no signature
mkdir -p "$t/sec" && cp "$t/key.pem" "$t/sec/muse-corva.pem"
jwt2=$(MUSE_CORVA_APP_ID=4242 MUSE_CORVA_SECRETS="$t/sec" scripts/token.sh --jwt 2>/dev/null) || jwt2=
IFS=. read -r h2 p2 s2 <<<"$jwt2"
printf '%s' "$s2" | b64d > "$t/sig2" 2>/dev/null
printf '%s.%s' "$h2" "$p2" | openssl dgst -sha256 -verify "$t/pub.pem" -signature "$t/sig2" >/dev/null 2>&1 && ok "key read from secrets/" || no "key read from secrets/"
body=$(MUSE_CORVA_APP_ID=4242 scripts/token.sh --scope mcint/muse-corva 2>/dev/null || true)
[ "$body" = '{"repositories":["muse-corva"]}' ] && ok "token scoped to one repo" || no "token scoped to one repo"
exit $fail
