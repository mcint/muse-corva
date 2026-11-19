# shared by bin/gh, bin/git: find real binaries, resolve repos, cache tokens.
here=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
app="$here/apps/muse-corva/app.json"
cache=${MUSE_CORVA_CACHE:-$HOME/.cache/muse-corva}

off(){ [ "${MUSE_CORVA_OFF:-0}" = 1 ] || [ ! -f "$app" ]; }

real(){  # real <name> [override] -> first <name> on PATH that isn't ours
  [ -n "${2:-}" ] && { echo "$2"; return; }
  local d IFS=:
  for d in $PATH; do
    [ "$d" = "$here/bin" ] && continue
    [ -x "$d/$1" ] && { echo "$d/$1"; return; }
  done
  return 1
}

origin_repo(){  # origin_repo [git -C args...] -> owner/repo for github.com origins
  "$REAL_GIT" "$@" remote get-url origin 2>/dev/null \
    | sed -nE 's#^(git@github\.com:|https://github\.com/|ssh://git@github\.com/)([^/]+/[^/]+)$#\2#p' \
    | sed 's/\.git$//'
}

token_for(){  # token_for owner/repo -> token on stdout, or exit 1 if not installed
  local f exp tok now
  f="$cache/$(printf '%s' "$1" | tr / _)"; now=$(date +%s)
  if [ -f "$f" ] && read -r exp tok < "$f" && [ "$exp" -gt $((now + 300)) ]; then
    [ "$tok" = - ] && return 1
    echo "$tok"; return 0
  fi
  mkdir -p "$cache" && chmod 700 "$cache"
  if tok=$("${MUSE_CORVA_TOKEN_CMD:-$here/scripts/token.sh}" "$1" 2>/dev/null) && [ -n "$tok" ]; then
    (umask 077; echo "$((now + 3600)) $tok" > "$f"); echo "$tok"
  else
    (umask 077; echo "$((now + 3600)) -" > "$f"); return 1
  fi
}
