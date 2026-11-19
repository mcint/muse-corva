#!/usr/bin/env bash
# token.sh --jwt            print an app JWT (10 min)
# token.sh [owner/repo]     print a 1h installation token for that repo only
# token.sh --scope o/r      print the token request body (repo-scoped)
#                           (default: origin of the current directory)
# Key: macOS keychain (service muse-corva, account private-key, base64 PEM),
# or MUSE_CORVA_KEY_FILE. App id: MUSE_CORVA_APP_ID or apps/muse-corva/app.json.
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
API=https://api.github.com

app_id=${MUSE_CORVA_APP_ID:-}
[ -n "$app_id" ] || app_id=$(jq -r .id "$here/apps/muse-corva/app.json" 2>/dev/null) \
  || { echo "token.sh: no app id (register first: uv run scripts/register.py)" >&2; exit 1; }

b64url(){ openssl base64 -A | tr '+/' '-_' | tr -d '='; }
key(){
  if [ -n "${MUSE_CORVA_KEY_FILE:-}" ]; then cat "$MUSE_CORVA_KEY_FILE"
  else security find-generic-password -s muse-corva -a private-key -w | openssl base64 -d -A; fi
}
jwt(){
  local now h p s
  now=$(date +%s)
  h=$(printf '{"alg":"RS256","typ":"JWT"}' | b64url)
  p=$(printf '{"iat":%d,"exp":%d,"iss":"%s"}' $((now-60)) $((now+540)) "$app_id" | b64url)
  s=$(printf '%s.%s' "$h" "$p" | openssl dgst -sha256 -sign <(key) | b64url)
  printf '%s.%s.%s\n' "$h" "$p" "$s"
}
api(){ curl -fsS -H "Authorization: Bearer $1" -H 'Accept: application/vnd.github+json' \
  -H 'X-GitHub-Api-Version: 2022-11-28' "${@:2}"; }

scope(){ jq -nc --arg r "${1#*/}" '{repositories:[$r]}'; }
if [ "${1:-}" = --jwt ]; then jwt; exit; fi
if [ "${1:-}" = --scope ]; then scope "$2"; exit; fi

repo=${1:-}
if [ -z "$repo" ]; then
  url=$(git remote get-url origin)
  repo=$(printf '%s' "$url" | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')
fi
j=$(jwt)
inst=$(api "$j" "$API/repos/$repo/installation" | jq -r .id) \
  || { echo "token.sh: muse-corva is not installed on $repo" >&2; exit 1; }
api "$j" -X POST -d "$(scope "$repo")" "$API/app/installations/$inst/access_tokens" | jq -r .token
