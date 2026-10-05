#!/usr/bin/env bash
# DASHBOARD-AUDIT-1 — recompute rejouable (LECTURE SEULE).
# Compare chaque chiffre affiché par le dashboard admin à sa valeur recalculée en base.
# Usage : bash scripts/dashboard-audit/recompute.sh
# Pré-requis : API du worktree lancée sur :5965 (voir lancer_api.sh), psql local.
# CHASSE-2 tourne en parallèle : on ne touche QUE des tables de métadonnées (pas l'île 431k).
set -uo pipefail
PGURL="${LABUSE_PG:-postgresql://openclaw@localhost:5432/labuse}"
Q(){ psql "$PGURL" -At -c "$1"; }

echo "### garde CHASSE-2 : backends actifs"
Q "select count(*) filter (where state='active' and query not ilike '%pg_stat%') from pg_stat_activity;"

echo; echo "### A. licences_actives / masqués / visibles (comptes.py _MASQUE_SQL)"
MASQUE="(c.plan='interne' OR c.nom ILIKE '[CT-TEST]%' OR EXISTS(SELECT 1 FROM utilisateurs u WHERE u.compte_id=c.id AND (split_part(lower(u.email),'@',2) IN ('labuse.test','labuse.local','exemple.test','ex.test','example.com','example.org','example.net','test.com') OR lower(u.email) LIKE '%+test@%')) OR ((c.nom ILIKE '%test%' OR c.nom ILIKE '%recette%') AND NOT EXISTS(SELECT 1 FROM utilisateurs u WHERE u.compte_id=c.id AND u.email IS NOT NULL AND split_part(lower(u.email),'@',2) NOT IN ('labuse.test','labuse.local','exemple.test','ex.test','example.com','example.org','example.net','test.com') AND lower(u.email) NOT LIKE '%+test@%')))"
echo "licences_actives (attendu écran 1) = $(Q "SELECT COUNT(*) FROM comptes c WHERE c.statut='actif' AND c.essai_expire_at IS NULL AND NOT $MASQUE;")"
echo "masqués (attendu 33)            = $(Q "SELECT COUNT(*) FROM comptes c WHERE c.statut<>'resilie' AND $MASQUE;")"
echo "visibles (attendu 3)            = $(Q "SELECT COUNT(*) FROM comptes c WHERE c.statut<>'resilie' AND NOT $MASQUE;")"
echo "licences total non-résilié (36) = $(Q "SELECT COUNT(*) FROM comptes WHERE statut<>'resilie';")"

echo; echo "### B. IA mois (attendu écran 0.25653 € / 60 appels)"
Q "SELECT ROUND(COALESCE(SUM(cout_eur),0)::numeric,5)||' € / '||COUNT(*)||' appels' FROM ia_log WHERE ts >= date_trunc('month', now());"

echo; echo "### C. sources affichées (vitrine 99) + interne (reservoirs 100)"
AFF="lower(d.status) IN ('connecte','manuel','live') AND COALESCE(d.technical_notes,'') NOT LIKE 'DOUBLON%' AND COALESCE(d.technical_notes,'') NOT LIKE 'RETIRÉ%' AND COALESCE(d.technical_notes,'') NOT LIKE 'DORMANT%' AND COALESCE(d.affichage_desactive,false)=false"
echo "vitrine (99)        = $(Q "SELECT count(*) FROM data_sources d WHERE $AFF;")"
echo "vitrine + interne (100) = $(Q "SELECT count(*) FROM data_sources d WHERE ($AFF) OR lower(d.status)='interne';")"

echo; echo "### D. courrier déposables (26) + plus ancien (29 ouvrés ≈ 41 cal.)"
Q "SELECT 'déposables='||count(*) FROM courrier_demandes WHERE corps IS NOT NULL AND statut='demande';"
Q "SELECT 'plus_vieux='||min(ts)::date||' soit '||(now()::date-min(ts)::date)||' j calendaires' FROM courrier_demandes WHERE corps IS NOT NULL AND statut='demande';"

echo; echo "### E. fuites / eau ancienne (compteurs live)"
Q "SELECT 'ecarts_ouverts='||count(*) filter (where statut='ouvert')||' soldés='||count(*) filter (where statut='solde') FROM circuit_ecarts;"
Q "SELECT 'coherence_runs='||count(*) FROM coherence_runs;"   -- Cohérence onglet : passages=[]

echo; echo "### F. verrous — dernier contrôle journalisé (le dashboard LIT ce passage, ne le rejoue pas)"
Q "SELECT 'dernier verrous: '||ts||' casses='||COALESCE(details->>'casses','?')||' joues='||COALESCE(details->>'joues','?') FROM circuit_journal WHERE geste='controle' AND cible='verrous' ORDER BY id DESC LIMIT 1;"

echo; echo "### G. bascule — run_bascule_journal (alimente /admin/flux 'dernière bascule')"
Q "SELECT 'dernière bascule journalisée: '||ts||' '||ancien||'→'||nouveau||' ('||sens||')' FROM run_bascule_journal ORDER BY ts DESC LIMIT 1;"
echo "   manifeste servi (fichier) : $(Q "SELECT 'run_label='||value||' maj='||updated_at FROM mvt_meta WHERE key='run_label';")"
echo "   >>> si la dernière bascule journalisée ≠ run servi du manifeste : indicateur 'dernière bascule' PÉRIMÉ."

echo; echo "### H. registres statiques (code, pas la base) : chiffres/moteurs/robinets/verrous"
PYTHONPATH="${PYTHONPATH:-src}" "${PYBIN:-$HOME/Desktop/labuse/.venv/bin/python}" - <<'PY' 2>/dev/null
from labuse.registre import CHIFFRES, ROBINETS
from labuse import circuit_verrous, jobs
m=sorted({c.moteur for c in CHIFFRES.values() if c.moteur})
print(f"CHIFFRES={len(CHIFFRES)} (écran 286) | moteurs={len(m)} (écran 29) | ROBINETS={len(ROBINETS)} (écran 169) | VERROUS={len(circuit_verrous.VERROUS)} (écran 24) | JOBS={len(jobs.JOBS)} (horloge attendus 25)")
PY

echo; echo "### I. déploiement — git rev-list depuis le marqueur config/deploiement.json"
SHA=$(python3 -c "import json;print(json.load(open('config/deploiement.json'))['sha'])" 2>/dev/null)
echo "marqueur sha=$SHA (baseline 21/09) ; avance=$(git rev-list --count ${SHA}..HEAD 2>/dev/null) commits (écran 857)"
