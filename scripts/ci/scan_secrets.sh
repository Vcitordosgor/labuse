#!/usr/bin/env bash
# CI-1 (Lot 3/4) — recherche de secrets commités, SANS dépendance ni licence externe.
# Partagé par le workflow GitHub (.github/workflows/ci.yml) ET le hook pre-push local.
# Compatible bash 3.2 (Mac de Vic) : aucun `mapfile`/`declare -A` ; on s'appuie sur `git grep`.
#
# Principe : scanne les fichiers SUIVIS par git (jamais .gitignore / node_modules) pour des motifs
# de secrets RÉELS à forte confiance, et interdit tout `.env` suivi (hors *.example). Conçu pour
# ZÉRO faux positif ici : clés de TEST Stripe (sk_test_/pk_test_/cs_test_), placeholders des
# .env.example, URLs vers des bases locales (labuse@localhost…) ne déclenchent pas.
#
# Sortie : 0 = rien ; 1 = secret(s) suspecté(s) (liste affichée).
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 2

fail=0

# 1) Aucun fichier d'environnement RÉEL suivi par git (seuls les *.example sont permis).
env_tracked=$(git ls-files | grep -E '(^|/)\.env($|\.)' | grep -vE '\.example$' || true)
if [ -n "$env_tracked" ]; then
  echo "Fichier(s) d'environnement suivi(s) par git (doivent être .gitignore) :"
  echo "$env_tracked" | sed 's/^/  ✗ /'
  fail=1
fi

# 2) Motifs de secrets réels. Exclusions de chemin (pathspec git) : exemples, lockfiles, CE script.
EXCL=(':(exclude)*.example' ':(exclude,glob)**/*.example'
      ':(exclude)requirements.lock' ':(exclude)frontend/package-lock.json'
      ':(exclude)scripts/ci/scan_secrets.sh')

# étiquette ⟞ regex ERE (git grep -I ignore les binaires). Clés de TEST non visées (live/pk/rk only).
scan() {
  local label="$1" re="$2"
  local hits
  hits=$(git grep -InE "$re" -- . "${EXCL[@]}" 2>/dev/null \
         | grep -vE '://[a-zA-Z0-9_.-]+:(labuse|password|changeme|secret|xxx+|placeholder|example|CHANGE_ME)@' \
         | grep -vE '@(localhost|127\.0\.0\.1|postgres|db|::1)[:/]' || true)
  if [ -n "$hits" ]; then
    echo "Secret suspecté — $label :"
    echo "$hits" | head -20 | sed 's/^/  ✗ /'
    fail=1
  fi
}

scan "Clé privée PEM"        '-----BEGIN ([A-Z ]+ )?PRIVATE KEY-----'
scan "Clé Stripe LIVE"       '(sk|rk|pk)_live_[0-9a-zA-Z]{20,}'
scan "Clé API Anthropic"     'sk-ant-[0-9A-Za-z_-]{24,}'
scan "Clé AWS"               'AKIA[0-9A-Z]{16}'
scan "Clé API Google"        'AIza[0-9A-Za-z_-]{35}'
scan "Jeton Slack"           'xox[baprs]-[0-9A-Za-z-]{10,}'
scan "Jeton GitHub"          'ghp_[0-9A-Za-z]{36}'
scan "URL avec mot de passe" '://[a-zA-Z0-9_.-]+:[^@/[:space:]:]{6,}@'

if [ "$fail" -eq 0 ]; then
  echo "scan secrets : rien trouvé."
fi
exit "$fail"
