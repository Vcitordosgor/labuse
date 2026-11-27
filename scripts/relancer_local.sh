#!/usr/bin/env bash
# OUTIL-COMMUNES-FIX-9 LOT B — relance SÛRE de l'app locale (API :8000 + front :5173).
#
# Corrige la cause du recontrôle ASTRA-6 (LOT A) : un `labuse api` long-running (reload=False) qui
# survit à une mise à jour du code → sert du code périmé, et des caches de réponses qui lui survivent.
# Ce script :
#   1. ARRÊTE l'API et le front, puis ATTEND que les ports soient réellement libres (SIGTERM → SIGKILL) ;
#   2. PURGE les caches de RÉPONSES de la base `labuse` (autorisé par Vic — CES caches et eux seuls,
#      listés ci-dessous) pour qu'aucune réponse calculée par l'ancien code ne survive ;
#   3. JOUE LE HEAL DE SCHÉMA EN PRÉ-SERVICE (modèle prod : `labuse schema-heal`, EN SÉRIE, avant le port)
#      avec un lock_timeout LONG (LABUSE_HEAL_LOCK_TIMEOUT, défaut 120 s LOCAL) : sur une base chargée par
#      un flux de lectures sans trou (bilan_params / v_parcel_dvf_last / pige_faits lus par un autre
#      worktree), attendre une fenêtre libre ne marche pas — l'ALTER/CREATE VIEW se MET EN FILE et l'obtient
#      dès que la lecture en cours finit. On ne redémarre JAMAIS un heal en vol (orphelin) ; on retente le
#      heal ENTIER si besoin, puis on démarre l'API avec LABUSE_SKIP_BOOT_HEAL=1 (heal non re-joué). On NE
#      touche NI au défaut de l'app (5 s) NI à la prod. Affiche les sessions qui chargent la base. Puis
#      VÉRIFIE, en échouant BRUYAMMENT sinon (jamais « RELANCE OK » avant) :
#        · /readyz == 200 (schéma sain, run servi présent) ;
#        · la révision du code RÉELLEMENT CHARGÉE par l'API (/readyz.code_rev, figée à l'import)
#          == le commit courant du dépôt (git HEAD) — plus de process survivant à une MAJ ;
#        · le run servi (/readyz.served_run.run) est annoncé (warn si ce n'est pas celui attendu).
#   4. (best-effort) REDÉMARRE le front.
#
# Caches de réponses VIDÉS (base `labuse`, uniquement ceux-là) :
#   · fiche_cache             — fiche parcelle (payload JSON servi)
#   · comparateur_raw_cache   — indicateurs bruts des 24 communes (Comparer + fiche commune)
#   · commune_contexte_cache  — contexte commune (bandeau/fiche commune)
#   · ia_cache                — réponses de l'assistant (dérivées de la fiche)
# N'est PAS touché : aucune table de DONNÉES (dvf_secteur_medianes, bilan_params, scores, zonage…).
#
# Usage :  scripts/relancer_local.sh
# Surcharge éventuelle :  LABUSE_REPO=/chemin  LABUSE_VENV=/chemin/.venv/bin  scripts/relancer_local.sh
set -u

REPO="${LABUSE_REPO:-$HOME/Desktop/labuse-main}"
VENV_BIN="${LABUSE_VENV:-$HOME/Desktop/labuse/.venv/bin}"
API_HOST="127.0.0.1"; API_PORT="8000"; FRONT_PORT="5173"
PY="$VENV_BIN/python"
LOG_DIR="${TMPDIR:-/tmp}"; API_LOG="$LOG_DIR/labuse-api.log"; FRONT_LOG="$LOG_DIR/labuse-front.log"

rouge() { printf '\033[31m✗ %s\033[0m\n' "$*" >&2; }
vert()  { printf '\033[32m✓ %s\033[0m\n' "$*"; }
info()  { printf '→ %s\n' "$*"; }
mourir() { rouge "$*"; echo "   (l'app N'EST PAS dans un état sûr — ne pas la montrer)"; exit 1; }

[ -d "$REPO/src/labuse" ] || mourir "dépôt introuvable : $REPO/src/labuse (définir LABUSE_REPO)"
[ -x "$PY" ] || mourir "python du venv introuvable : $PY (définir LABUSE_VENV)"

# ── 1. ARRÊT + ATTENTE que le port soit LIBRE (le cœur du correctif vs « lsof | xargs kill ») ────────
arreter_port() {
  local port="$1" label="$2" pids
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    info "arrêt $label (:$port) — PID(s) $pids (SIGTERM)…"
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
  fi
  # ATTENDRE la libération effective du port (jusqu'à 20 s), puis SIGKILL en dernier recours.
  for _ in $(seq 1 40); do
    lsof -tiTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1 || { [ -n "$pids" ] && vert "$label arrêté, :$port libre"; return 0; }
    sleep 0.5
  done
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    rouge "$label (:$port) ne s'arrête pas — SIGKILL $pids"
    # shellcheck disable=SC2086
    kill -9 $pids 2>/dev/null || true
    for _ in $(seq 1 20); do
      lsof -tiTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1 || { vert ":$port libre après SIGKILL"; return 0; }
      sleep 0.5
    done
    mourir "$label : :$port TOUJOURS occupé — refus de démarrer par-dessus (risque Errno 48)"
  fi
  return 0
}
arreter_port "$FRONT_PORT" "front"
arreter_port "$API_PORT" "API"

# ── 2. PURGE des caches de RÉPONSES (base `labuse`, autorisée) ───────────────────────────────────────
info "purge des caches de réponses (fiche_cache, comparateur_raw_cache, commune_contexte_cache, ia_cache)…"
( cd "$REPO" && PYTHONPATH=src "$PY" - <<'PYEOF'
from sqlalchemy import text
from labuse.db import engine
CACHES = ["fiche_cache", "comparateur_raw_cache", "commune_contexte_cache", "ia_cache"]
with engine().begin() as c:
    for t in CACHES:
        if c.execute(text("SELECT to_regclass(:t)"), {"t": t}).scalar():
            n = c.execute(text(f"DELETE FROM {t}")).rowcount
            print(f"   · {t}: {n} ligne(s) supprimée(s)")
        else:
            print(f"   · {t}: absente (rien à purger)")
PYEOF
) || mourir "purge des caches impossible (base injoignable ?) — corriger avant de servir"

# ── 3. HEAL DE SCHÉMA EN PRÉ-SERVICE (mise en FILE), puis API avec heal SAUTÉ ──────────────────────────
# Le heal ne tourne qu'AU DÉMARRAGE du processus (lifespan), jamais re-joué par /readyz. Sur une base
# chargée par un flux de lectures (dont des requêtes spatiales de 10-20 s d'un autre worktree), « attendre
# un trou » ne marche pas. On reproduit le modèle PROD (ExecStartPre `labuse schema-heal` + worker
# LABUSE_SKIP_BOOT_HEAL=1) : on joue le heal EN SÉRIE, UNE fois, AVANT d'ouvrir le port, avec un
# lock_timeout LONG (LABUSE_HEAL_LOCK_TIMEOUT) — l'ALTER/CREATE VIEW se MET EN FILE et obtient l'ACCESS
# EXCLUSIVE dès que la lecture EN COURS finit (les nouvelles patientent derrière, borné par le délai).
# On NE redémarre JAMAIS un heal en cours (ça orphelinerait un backend tenant le verrou, qui bloquerait
# le heal suivant) : on ATTEND sa fin ; on peut relancer le heal ENTIER (process neuf, sans orphelin) si
# un step a échoué. Le heal fini, l'API démarre avec LABUSE_SKIP_BOOT_HEAL=1 (ne re-joue pas le heal) →
# /readyz 200. On ne touche NI au défaut de l'app (5 s, variable absente) NI à la prod.
HEAD="$(git -C "$REPO" rev-parse HEAD)"
WATCH_TABLES="bilan_params v_parcel_dvf_last pige_faits event_log"   # tables sensibles au heal (ALTER/UPDATE/refresh)
HEAL_LT="${LABUSE_HEAL_LOCK_TIMEOUT:-120s}"   # délai de MISE EN FILE du heal (local) ; borne l'attente + le blocage des lectures derrière
export LABUSE_HEAL_LOCK_TIMEOUT="$HEAL_LT"

demarrer_api() {
  info "démarrage de l'API depuis $REPO (git HEAD ${HEAD:0:12}, heal déjà joué → LABUSE_SKIP_BOOT_HEAL=1) — journal : $API_LOG"
  # </dev/null : serveur détaché, aucun fd partagé (sinon « relancer | tail » resterait ouvert).
  # LABUSE_SKIP_BOOT_HEAL=1 : le heal a été joué en pré-service juste avant → l'API ne le re-joue PAS
  # (modèle prod worker) : démarrage rapide, pas de 503 heal.
  ( cd "$REPO" && PYTHONPATH=src LABUSE_SKIP_BOOT_HEAL=1 nohup "$VENV_BIN/labuse" api --host "$API_HOST" --port "$API_PORT" </dev/null >"$API_LOG" 2>&1 & )
}

# Attend que /readyz RÉPONDE (quel que soit le code), ~60 s (heal déjà joué → démarrage rapide).
poll_readyz() {
  CODE=""; READY_JSON=""
  for _ in $(seq 1 120); do
    CODE="$(curl -s -o "$LOG_DIR/readyz.json" -w '%{http_code}' "http://$API_HOST:$API_PORT/readyz" 2>/dev/null || true)"
    [ -n "$CODE" ] && [ "$CODE" != "000" ] && { READY_JSON="$(cat "$LOG_DIR/readyz.json")"; return 0; }
    sleep 0.5
  done
  return 1
}

# Affiche les verrous tenus par d'AUTRES sessions sur des tables utilisateur (requête + ancienneté) ;
# 1re ligne « WATCH=N » = nb de sessions tenant un verrou sur une table SENSIBLE (watchlist + tables
# nommées dans l'erreur du heal). Lecture seule, statement_timeout court (ne se bloque pas lui-même).
_blockers() {
  ( cd "$REPO" && WATCH="$WATCH_TABLES $1" PYTHONPATH=src "$PY" - <<'PYEOF'
import os
from sqlalchemy import text
from labuse.db import engine
watch = {w.strip(' ,.";').lower() for w in os.environ.get("WATCH", "").split() if len(w.strip(' ,.";')) >= 4}
try:
    with engine().connect() as c:
        c.exec_driver_sql("SET statement_timeout='5s'")
        rows = c.execute(text("""
            SELECT cl.relname AS tbl, l.mode AS mode, a.pid AS pid,
                   coalesce(round(extract(epoch from (now()-a.query_start)))::int, -1) AS dur_s,
                   coalesce(a.state, '?') AS state,
                   left(regexp_replace(coalesce(a.query, ''), '\\s+', ' ', 'g'), 110) AS q
            FROM pg_locks l JOIN pg_class cl ON cl.oid = l.relation
            JOIN pg_stat_activity a ON a.pid = l.pid
            WHERE l.relation IS NOT NULL AND cl.relkind IN ('r', 'm', 'v', 'p')
              AND a.pid <> pg_backend_pid() AND a.datname = current_database()
              AND cl.relnamespace::regnamespace::text NOT IN ('pg_catalog', 'information_schema')
            ORDER BY dur_s DESC
        """)).mappings().all()
    seen = set(); uniq = []
    for r in rows:
        k = (r["tbl"], r["pid"])
        if k not in seen:
            seen.add(k); uniq.append(r)
    sens = [r for r in uniq if r["tbl"].lower() in watch]
    print(f"WATCH={len({r['pid'] for r in sens})}")
    for r in (sens or uniq)[:12]:
        flag = " ⚠SENSIBLE" if r["tbl"].lower() in watch else ""
        print(f"  · {r['tbl']}{flag} [{r['mode']}] pid {r['pid']} depuis {r['dur_s']}s ({r['state']}) : {r['q']}")
    if not uniq:
        print("  (aucun verrou tenu par une autre session sur une table utilisateur)")
except Exception as ex:  # noqa: BLE001
    print("WATCH=-1"); print(f"  (lecture des verrous impossible : {type(ex).__name__}: {ex})")
PYEOF
  )
}

# Qui charge la base (transparence, lecture seule) — le heal va se mettre EN FILE derrière ces lectures.
info "sessions qui chargent la base (le heal se met EN FILE derrière leurs lectures en cours) :"
printf '%s\n' "$(_blockers "")" | grep -v '^WATCH='

# Heal pré-service, borné, SANS redémarrage en plein vol (pas d'orphelin). On RETENTE le heal ENTIER
# (process neuf → aucun backend orphelin) si un step échoue sur un verrou, jusqu'à 3 min. `labuse
# schema-heal` SORT EN CODE 1 si un step échoue → on le DIT + on montre les verrous, puis on retente.
DEADLINE=$(( $(date +%s) + 180 )); ESSAI=0; HEAL_OK=0
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  ESSAI=$((ESSAI + 1))
  info "heal de schéma (essai $ESSAI) — EN FILE, lock_timeout=$HEAL_LT (attend la fin des lectures en cours)…"
  if ( cd "$REPO" && PYTHONPATH=src "$VENV_BIN/labuse" schema-heal >"$LOG_DIR/heal.log" 2>&1 ); then
    HEAL_OK=1; grep -E '✓|OK|steps' "$LOG_DIR/heal.log" | tail -1; break
  fi
  rouge "heal en échec (essai $ESSAI) :"; grep -iE '✗|error|lock|timeout' "$LOG_DIR/heal.log" | head -4
  _HTBL="$(grep -oiE '[a-z_][a-z0-9_]{3,}' "$LOG_DIR/heal.log" | sort -u | tr '\n' ' ')"
  info "verrous au moment de l'échec :"; printf '%s\n' "$(_blockers "$_HTBL")" | grep -v '^WATCH='
  sleep 4
done
[ "$HEAL_OK" = 1 ] || mourir "heal de schéma échoué après 3 min malgré la mise en file (lock_timeout=$HEAL_LT). Requêtes tenant le verrou ci-dessus."
vert "heal de schéma OK (mis en file, essai $ESSAI)"

# L'API démarre heal SAUTÉ (déjà joué) → vite, et /readyz ne 503 pas sur le heal.
demarrer_api
poll_readyz || mourir "l'API ne répond pas sur /readyz (voir $API_LOG)"
if [ "${CODE:-}" != "200" ]; then
  printf '%s\n' "${READY_JSON:-}" | "$PY" -m json.tool 2>/dev/null | head -40 || printf '%s\n' "${READY_JSON:-}"
  mourir "/readyz = ${CODE:-000} (≠ 200) — l'API est démarrée mais PAS saine (voir le JSON ci-dessus)"
fi
vert "/readyz = 200"

# ── 3b. révision CHARGÉE == git HEAD du dépôt ─────────────────────────────────────────────────────────
SERVED_REV="$(echo "$READY_JSON" | "$PY" -c 'import sys,json; print((json.load(sys.stdin).get("code_rev") or "").split(":")[-1])')"
RUN="$(echo "$READY_JSON" | "$PY" -c 'import sys,json; d=json.load(sys.stdin).get("served_run") or {}; print(d.get("run") or "")')"
[ -n "$SERVED_REV" ] || mourir "/readyz ne renvoie pas code_rev — l'API ne sait pas dire sa révision"
case "$HEAD" in
  "$SERVED_REV"*) vert "révision servie = $SERVED_REV == git HEAD ${HEAD:0:12} (le code de main EST servi)" ;;
  *) mourir "révision servie ($SERVED_REV) ≠ git HEAD (${HEAD:0:12}) — l'API sert un AUTRE code que le dépôt" ;;
esac

# ── 3c. run servi (warn, pas un échec : c'est une donnée, pas du code) ────────────────────────────────
EXPECTED_RUN="${LABUSE_EXPECTED_RUN:-}"
if [ -n "$RUN" ]; then
  if [ -n "$EXPECTED_RUN" ] && [ "$RUN" != "$EXPECTED_RUN" ]; then
    rouge "run servi = $RUN (attendu $EXPECTED_RUN) — vérifier la bascule de run"
  else
    vert "run servi = $RUN"
  fi
else
  rouge "run servi non annoncé par /readyz (served_run absent)"
fi

# ── 3d. WARMUP (ASTRA-9 LOT 5) — amorce les caches lourds AVANT la première ouverture utilisateur ──────
# Cause des 500 « à froid » vus après la relance : des agrégats lourds (_q_v2_stats du /filtre, /communes,
# carnet de secteur, contexte commune) dépassent statement_timeout sur un cache PostgreSQL FROID — aggravé
# en LOCAL par la contention des worktrees sœurs — → QueryCanceled → la transaction de la session est
# abandonnée → cascade InFailedSqlTransaction → 500. Le 2e appel passe (cache chaud + _mem_cached 30 s).
# On pré-chauffe donc ces routes CÔTÉ SERVEUR (GET lecture seule, ne touche NI l'app NI la prod) pour que
# la 1re ouverture utilisateur tombe sur un cache chaud. Échec persistant (contention) = signalé, pas bloquant.
FILTRE_TIERS="brulante,chaude,reserve_fonciere,a_creuser,declasse_bati_sature,declasse_non_constructible,declasse_bati_revele,declasse_zone_fermee,declasse_au_statut_inconnu,declasse_au_fermee,priorite,a_suivre,sans_signal,ecartee"
warmup_route() {  # $1 = chemin+query, $2 = libellé
  CODE_W=000
  for ESSAI in 1 2 3; do
    CODE_W="$(curl -s -o /dev/null -w '%{http_code}' --max-time 120 "http://$API_HOST:$API_PORT$1" 2>/dev/null || echo 000)"
    [ "$CODE_W" = "200" ] && { vert "warmup $2 : 200 (essai $ESSAI)"; return 0; }
    info "warmup $2 : $CODE_W (essai $ESSAI) — cache froid/contention, nouvel essai…"
  done
  rouge "warmup $2 : $CODE_W après 3 essais — 1re ouverture possiblement à froid (contention DB locale ?)"
  return 1
}
info "pré-chauffage des caches lourds (évite les 500 « à froid » à la 1re ouverture)…"
warmup_route "/filtre?source=${RUN:-q_v20}&limit=0&offset=0&sort=rang&tiers=$FILTRE_TIERS" "/filtre (bandes)" || true
warmup_route "/communes" "/communes" || true

# ── 4. FRONT (best-effort) ────────────────────────────────────────────────────────────────────────────
if [ -d "$REPO/frontend" ]; then
  info "démarrage du front (vite :$FRONT_PORT) — journal : $FRONT_LOG"
  ( cd "$REPO/frontend" && nohup npm run dev </dev/null >"$FRONT_LOG" 2>&1 & )
  for _ in $(seq 1 60); do
    lsof -tiTCP:"$FRONT_PORT" -sTCP:LISTEN >/dev/null 2>&1 && { vert "front en écoute sur :$FRONT_PORT"; break; }
    sleep 0.5
  done
  lsof -tiTCP:"$FRONT_PORT" -sTCP:LISTEN >/dev/null 2>&1 || rouge "front pas encore en écoute (voir $FRONT_LOG) — l'API, elle, est saine"
fi

# ── 5. GARDE-FOU DES TABLES DÉRIVÉES (OUTIL-PERMIS-FIX-15) ─────────────────────────────────────────────
# `pc_caducs` a été vidée deux fois par une reconstruction sur source transitoirement vide (rebuild_swap
# publiait un résultat vide). Le garde-fou de code (RebuildWouldEmptyError) empêche désormais l'écrasement ;
# ici on VÉRIFIE l'état servi : pc_caducs NON VIDE et /accueil/chiffres == la table. Sinon ÉCHEC CLAIR
# (jamais « RELANCE OK »). Autres dérivées au MÊME risque (mêmes rebuild_swap) : defisc_fenetres, score_e.
info "garde-fou des tables dérivées (pc_caducs — cause des disparitions FIX-15)…"
DERIV_COUNTS="$( cd "$REPO" && PYTHONPATH=src "$PY" - <<'PYEOF'
from sqlalchemy import text
from labuse.db import engine
with engine().connect() as c:
    for t in ("pc_caducs", "defisc_fenetres", "score_e"):
        reg = c.execute(text("SELECT to_regclass(:t)"), {"t": t}).scalar()
        n = c.execute(text(f'SELECT count(*) FROM "{t}"')).scalar() if reg is not None else -1
        print(f"{t} {n}")
PYEOF
)"
TBL_CADUCS="$(printf '%s\n' "$DERIV_COUNTS" | awk '$1=="pc_caducs"{print $2}')"
ROUTE_CADUCS="$(curl -s "http://$API_HOST:$API_PORT/accueil/chiffres" | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("permis_caducs"))' 2>/dev/null || echo "")"
[ -n "$TBL_CADUCS" ] || mourir "garde-fou : impossible de lire le compte de pc_caducs (base injoignable ?)"
if [ "$TBL_CADUCS" = "-1" ]; then
  mourir "garde-fou : table pc_caducs ABSENTE — la reconstruire (fraicheur-derives / pc-caducs) avant de servir"
elif [ "$TBL_CADUCS" = "0" ]; then
  mourir "garde-fou : pc_caducs est VIDE (0 ligne) — reconstruire avant de servir (cf. FIX-15 ; ne jamais montrer un signal 'caduc' muet)"
elif [ "$ROUTE_CADUCS" != "$TBL_CADUCS" ]; then
  mourir "garde-fou : /accueil/chiffres sert permis_caducs=$ROUTE_CADUCS ≠ table pc_caducs=$TBL_CADUCS — incohérence route/table"
fi
vert "garde-fou pc_caducs : $TBL_CADUCS ligne(s), /accueil/chiffres == table"
# Autres dérivées à risque : avertir si vides (non bloquant — elles peuvent l'être légitimement en dev).
printf '%s\n' "$DERIV_COUNTS" | awk '$1!="pc_caducs"{print}' | while read -r t n; do
  if [ "$n" = "0" ] || [ "$n" = "-1" ]; then
    rouge "dérivée $t : ${n/-1/ABSENTE} — même risque que pc_caducs (rebuild_swap), à surveiller/reconstruire"
  else
    vert "dérivée $t : $n ligne(s)"
  fi
done

vert "RELANCE OK — API saine, code de ${HEAD:0:12} servi, caches de réponses purgés, dérivées non vides (pc_caducs == route)."
