#!/usr/bin/env bash
# MENAGE-1 (geste 12) — RETRAIT DES WORKTREES MERGÉS, prudent.
# Chaque worktree lié pèse ~3 Go de fichiers suivis dupliqués au checkout (cf. rapport MENAGE-1, A1.3).
# Ce script retire ceux dont la branche est MERGÉE dans `main` ET dont l'arbre est PROPRE.
# Il REFUSE (laisse en place + alerte) tout worktree qui porte des fichiers NON SUIVIS : ce sont
# souvent des LIVRABLES non commités (ex. labuse-radaretat et ses docs/audit-2026-10/radar-etat-1/)
# — on ne détruit jamais un livrable par mégarde.
#
# PAR DÉFAUT : DRY-RUN (montre ce qui serait retiré, ne touche à rien). `--apply` exécute.
# Ne touche JAMAIS : la worktree principale (main), ni la worktree COURANTE, ni une branche non mergée.
#
# Usage :  bash scripts/ops/retrait_worktrees_merges.sh [--apply] [--base main]
set -uo pipefail

APPLY=0
BASE="main"
while [ $# -gt 0 ]; do
  case "$1" in
    --apply) APPLY=1 ;;
    --base)  shift; BASE="${1:-main}" ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "argument inconnu : $1" >&2; exit 2 ;;
  esac
  shift
done

GITDIR="$(git rev-parse --git-common-dir 2>/dev/null)" || { echo "✗ pas dans un dépôt git." >&2; exit 1; }
MAIN_WT="$(git -C "$(dirname "$GITDIR")" rev-parse --show-toplevel 2>/dev/null)"
CUR_WT="$(git rev-parse --show-toplevel 2>/dev/null)"

# la branche `main` doit exister comme référence pour tester « mergé ».
if ! git show-ref --verify --quiet "refs/heads/$BASE"; then
  echo "✗ branche de base introuvable : $BASE (passer --base <branche>)." >&2; exit 1
fi

echo "▶ Base de merge : $BASE · mode : $([ "$APPLY" = 1 ] && echo APPLY || echo DRY-RUN)"
echo

retires=0; gardes=0; refus=0

# `git worktree list --porcelain` : blocs séparés par une ligne vide ; clés worktree/branch/bare/detached.
wt=""; br=""; detached=0; bare=0
traiter() {
  [ -z "$wt" ] && return
  # jamais la principale ni la courante
  if [ "$wt" = "$MAIN_WT" ] || [ "$wt" = "$CUR_WT" ]; then
    echo "• $wt  →  gardé (worktree principale ou courante)"; gardes=$((gardes+1)); return
  fi
  if [ "$bare" = 1 ]; then return; fi
  if [ "$detached" = 1 ] || [ -z "$br" ]; then
    echo "• $wt  →  gardé (HEAD détachée, pas de branche à tester)"; gardes=$((gardes+1)); return
  fi
  local branche="${br#refs/heads/}"
  # un worktree sur la base elle-même (main) n'est pas une branche de travail « mergée » à retirer.
  if [ "$branche" = "$BASE" ]; then
    echo "• $wt  [$branche]  →  gardé (sur la branche de base $BASE)"; gardes=$((gardes+1)); return
  fi
  # mergée dans BASE ?
  if ! git merge-base --is-ancestor "$branche" "$BASE" 2>/dev/null; then
    echo "• $wt  [$branche]  →  gardé (branche NON mergée dans $BASE — travail actif)"
    gardes=$((gardes+1)); return
  fi
  # arbre propre ? on distingue modifs suivies et fichiers NON SUIVIS.
  local porcelain untracked modified
  porcelain="$(git -C "$wt" status --porcelain 2>/dev/null)"
  untracked="$(printf '%s\n' "$porcelain" | grep -c '^??' || true)"
  modified="$(printf '%s\n' "$porcelain" | grep -vc '^??' || true)"
  # (grep -c sur chaîne vide renvoie 0 ; mais une ligne vide compte comme 0 match → ok)
  [ -z "$porcelain" ] && { untracked=0; modified=0; }
  if [ "$untracked" -gt 0 ]; then
    echo "⚠ $wt  [$branche]  →  REFUSÉ : mergée mais $untracked fichier(s) NON SUIVI(S) (livrables ?) :"
    printf '%s\n' "$porcelain" | grep '^??' | sed 's/^?? /      /'
    echo "      → archive-les ou commit-les, puis relance. (jamais retiré automatiquement.)"
    refus=$((refus+1)); return
  fi
  if [ "$modified" -gt 0 ]; then
    echo "⚠ $wt  [$branche]  →  REFUSÉ : mergée mais modifications suivies non commitées."
    refus=$((refus+1)); return
  fi
  # mergée + propre → candidat au retrait
  if [ "$APPLY" = 1 ]; then
    if git worktree remove "$wt" 2>/dev/null; then
      echo "✓ $wt  [$branche]  →  RETIRÉ (mergée + propre)"
      retires=$((retires+1))
    else
      echo "✗ $wt  [$branche]  →  échec du retrait (git worktree remove)"; refus=$((refus+1))
    fi
  else
    echo "✓ $wt  [$branche]  →  serait RETIRÉ (mergée + propre) — (dry-run)"
    retires=$((retires+1))
  fi
}

while IFS= read -r line; do
  case "$line" in
    worktree\ *) traiter; wt="${line#worktree }"; br=""; detached=0; bare=0 ;;
    branch\ *)   br="${line#branch }" ;;
    detached)    detached=1 ;;
    bare)        bare=1 ;;
    "")          : ;;  # fin de bloc traitée au bloc suivant / en fin
  esac
done < <(git worktree list --porcelain)
traiter   # dernier bloc

echo
echo "▶ Bilan : $retires $([ "$APPLY" = 1 ] && echo 'retiré(s)' || echo 'retirable(s)') · $gardes gardé(s) · $refus refusé(s)."
[ "$APPLY" = 1 ] || echo "  (dry-run — relancer avec --apply pour exécuter.)"
exit 0
