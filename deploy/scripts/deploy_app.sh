#!/usr/bin/env bash
# =============================================================================
# LA BUSE — M7 · déploiement applicatif — À LANCER DEPUIS LE MAC (idempotent)
# -----------------------------------------------------------------------------
# Le VPS ne détient AUCUN credential git : le code part du poste local en rsync
# (l'état de la branche déployée), sans .git ni artefacts. Relançable à volonté.
# Usage : deploy/scripts/deploy_app.sh [hôte-ssh=labuse-vps]
# =============================================================================
set -euo pipefail
HOST="${1:-labuse-vps}"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
HEALTH_PORT="${LABUSE_HEALTH_PORT:-8000}"

# ── SOLIDITE-1 (Lot 4.2) — GARDE MANIFESTE AVANT ENVOI ──────────────────────────────────────
# Le manifeste servi n'est PAS expédié (il est exclu du rsync ci-dessous) : il appartient à la prod.
# Mais si le manifeste LOCAL pointe un run dont la prod n'a PAS les données, c'est le signe d'un
# décalage dangereux (incident 13/10 : front/code attendent un run que la prod ne sert pas → /readyz
# faux). On REFUSE de déployer tant que ce run n'a pas ses lignes en prod.
LOCAL_RUN="$(python3 -c "import json;print(json.load(open('$REPO/config/served_manifest.json'))['scoring_run'])" 2>/dev/null || echo '')"
if [ -n "$LOCAL_RUN" ]; then
  N=$(ssh -o BatchMode=yes "$HOST" "sudo -u postgres psql -At -d labuse -c \"SELECT count(*) FROM score_labuse WHERE run_label='$LOCAL_RUN'\"" 2>/dev/null || echo 0)
  if [ "${N:-0}" -lt 1 ]; then
    echo "✗ REFUS : le manifeste local sert '$LOCAL_RUN' mais la prod n'a AUCUNE ligne score_labuse pour ce run." >&2
    echo "  Poser d'abord les données (deploy/scripts/deploy_donnees.sh --run-label $LOCAL_RUN), puis redéployer le code." >&2
    exit 1
  fi
  echo "── garde manifeste : run local '$LOCAL_RUN' présent en prod ($N lignes score_labuse) ✓"
fi

echo "── 1. Code → ${HOST}:/opt/labuse/app (rsync DIRECT via sudo distant, sans transit /tmp) ──"
# DISQUE-VPS-1 — on n'envoie QUE l'utile (cf. docs/audit-2026-10/DISQUE-VPS-1.md) :
#   · rsync écrit DIRECTEMENT dans /opt/labuse/app via --rsync-path="sudo rsync" (plus de
#     /tmp/labuse-app-sync : économise ~11 Go temporaires sous /tmp à chaque déploiement) ;
#   · exclusions ANCRÉES (préfixe / = racine du transfert) des SOURCES d'ingestion brutes (jamais
#     lues au runtime ni par un cron — ingérées une fois en base), de docs/ (barrière jouée côté Mac),
#     et des artefacts de dev (qa/captures/audit_shots/tests/reports) ;
#   · les exclusions PROTÈGENT AUSSI du --delete les caches/sorties écrits SUR le VPS
#     (data/plu_reglements, data/ortho_tiles, data/ban régénéré par cron, outputs/) — à ne pas écraser.
#   · ⛔ ÉTAT SERVI (config/served_manifest.json + served_run.txt) JAMAIS expédié : c'est le POINTEUR
#     de bascule, propre à la prod (écrit par la bascule seule). Incident 13/10 : le manifeste local
#     (q_v18) rsync'd ici a basculé prod sur un run sans données → /readyz=false. Exclu définitivement.
rsync -a --delete --rsync-path="sudo rsync" \
  --exclude .git --exclude .venv --exclude node_modules --exclude frontend/dist \
  --exclude /.env \
  `# /.env = config LOCALE de dev (chemins Mac, ex. LABUSE_PIGE_CAPTURES_DIR=/Users/...) : JAMAIS` \
  `# expédiée en prod — elle y fuyait des valeurs Mac. La config prod vit dans /etc/labuse/labuse.env.` \
  --exclude "__pycache__" --exclude "*.pyc" --exclude .pytest_cache --exclude /exports \
  --exclude /reports --exclude /qa --exclude /captures --exclude /audit_shots \
  --exclude /tests --exclude /docs --exclude /outputs \
  --exclude /data/cosia --exclude /data/ortho_irc --exclude /data/ortho_tiles \
  --exclude /data/rgealti --exclude /data/dvf_histo --exclude /data/ml \
  --exclude /data/insee_rp --exclude /data/ban --exclude /data/edf_hta \
  --exclude /data/tcsp --exclude /data/dvf --exclude /data/plu_reglements \
  --exclude /config/served_manifest.json --exclude /config/served_run.txt \
  "$REPO/" "$HOST":/opt/labuse/app/
ssh -o BatchMode=yes "$HOST" 'sudo chown -R labuse:labuse /opt/labuse/app'

echo "── 2. venv + dépendances (sur le VPS, en labuse) ──"
# Import-smoke de la CHAÎNE DE DÉMARRAGE (pas juste `import labuse`) : app servie + comptes +
# tenant + events. Une dépendance cœur manquante (ex. argon2-cffi absent → comptes KO → cloison
# non matérialisée EN SILENCE) fait ÉCHOUER LE DÉPLOIEMENT ICI, avant tout restart. set -e propage.
ssh -o BatchMode=yes "$HOST" 'sudo -u labuse bash -c "
  set -e
  cd /opt/labuse
  [ -d venv ] || python3.12 -m venv venv
  ./venv/bin/pip install -q --upgrade pip
  # PROPRETE-FIX-0 — dépendances CŒUR depuis le VERROU (versions testées, CVE corrigées), puis
  # le paquet lui-même en éditable SANS re-résoudre (--no-deps : le closure vient du lock).
  ./venv/bin/pip install -q -r ./app/requirements.lock
  ./venv/bin/pip install -q -e ./app --no-deps
  ./venv/bin/python -c \"import labuse.api.app, labuse.comptes, labuse.api.tenant, labuse.api.events; print(\\\"chaîne de démarrage importable ✓\\\")\"
"'

echo "── 3. Front (dist se CONSTRUIT sur le VPS, ne se copie pas ; --base=/ : Caddy le sert à la RACINE) ──"
ssh -o BatchMode=yes "$HOST" 'sudo -u labuse bash -c "
  cd /opt/labuse/app/frontend
  npm ci --silent
  VITE_RUN_LABEL=\${VITE_RUN_LABEL:-q_v7_defisc} npx vite build --base=/ 2>&1 | tail -1
"'

echo "── 4. systemd (unit versionnée) ──"
ssh -o BatchMode=yes "$HOST" 'sudo install -o root -g root -m 644 /opt/labuse/app/deploy/systemd/labuse.service /etc/systemd/system/labuse.service
sudo systemctl daemon-reload'

# ── DONNEES-ETAT-FIX-2 (Lot 0) — CRONTAB REPOSÉ + VÉRIFIÉ À CHAQUE DÉPLOIEMENT ───────────────
# Le SEUL vrai déploiement passe ICI (la prod n'a pas de clone git → deploy_vps.sh ne tourne jamais ;
# FIX-1 avait mis la repose au mauvais endroit). On régénère le crontab depuis le registre du binaire
# qu'on vient de poser, on sauvegarde l'ancien, on pose, et on VÉRIFIE l'égalité au registre — tout
# écart ARRÊTE le déploiement (plus jamais « déployé mais crontab périmé », écart DONNEES-ETAT-2 §2/§3).
# Heures : le registre est en UTC, --tz convertit (+4 h pour Indian/Reunion).
echo "── 4b. crontab reposé + vérifié depuis le registre ──"
if ! ssh -o BatchMode=yes "$HOST" 'set -e
  SRVTZ=$(timedatectl show -p Timezone --value 2>/dev/null || cat /etc/timezone 2>/dev/null || echo inconnu)
  case "$SRVTZ" in
    UTC|Etc/UTC) GENTZ=utc ;;
    Indian/Reunion) GENTZ=reunion ;;
    *) echo "✗ fuseau serveur $SRVTZ ni UTC ni Indian/Reunion (le registre est en UTC)" >&2; exit 5 ;;
  esac
  CT=$(mktemp)
  sudo -u labuse /opt/labuse/venv/bin/labuse jobs crontab --tz "$GENTZ" > "$CT"
  [ -f /etc/cron.d/labuse ] && sudo cp -p /etc/cron.d/labuse "/etc/cron.d/labuse.bak-deploy-$(date +%Y%m%d-%H%M%S)"
  sudo install -o root -g root -m 644 "$CT" /etc/cron.d/labuse
  rm -f "$CT"
  sudo -u labuse /opt/labuse/venv/bin/labuse jobs crontab --tz "$GENTZ" --verifier /etc/cron.d/labuse
  sudo systemctl restart cron 2>/dev/null || true'; then
  echo "✗ REFUS : crontab non reposé / divergent du registre — déploiement ARRÊTÉ (DONNEES-ETAT-FIX-2 Lot 0)." >&2
  exit 5
fi
echo "   crontab reposé depuis le registre + vérifié ✓"

# ── DONNEES-ETAT-FIX-2 (Lot 0) — MARQUEUR DE DÉPLOIEMENT (sha + date) ────────────────────────
# config/deploiement.json est lu par le Pilotage (« Déployer » : avance de main sur la prod). Il
# n'était jamais mis à jour par ce script (deploy_app.sh) → sha figé/périmé. On l'écrit ICI après
# la pose, avec le sha réellement déployé et la date du déploiement.
echo "── 4c. marqueur de déploiement (config/deploiement.json) ──"
DSHA=$(git -C "$REPO" rev-parse HEAD 2>/dev/null || echo '')
DISO=$(git -C "$REPO" show -s --format=%cI HEAD 2>/dev/null || echo '')
DEPLOYE_LE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
if [ -n "$DSHA" ]; then
  ssh -o BatchMode=yes "$HOST" "sudo -u labuse tee /opt/labuse/app/config/deploiement.json >/dev/null" <<EOF
{
 "sha": "$DSHA",
 "iso": "$DISO",
 "par": "deploy_app.sh",
 "deploye_le": "$DEPLOYE_LE"
}
EOF
  echo "   deploiement.json = ${DSHA:0:12} (déployé $DEPLOYE_LE)"
else
  echo "   ⚠ git indisponible — deploiement.json inchangé"
fi

# ── SOLIDITE-1 (Lot 4.2) — CONTRÔLE DU MANIFESTE PROD APRÈS ENVOI ───────────────────────────
# Le manifeste prod n'a pas dû bouger (on ne l'expédie pas) ; on VÉRIFIE qu'il sert toujours un run
# qui a ses données, et que /readyz répond. Un code déployé par-dessus un manifeste incohérent se verrait
# ici, pas chez le client.
echo "── 5. contrôle du manifeste prod (SOLIDITE-1 Lot 4.2) ──"
PROD_RUN=$(ssh -o BatchMode=yes "$HOST" "grep -vE '^[[:space:]]*#' /opt/labuse/app/config/served_run.txt 2>/dev/null | grep -vE '^[[:space:]]*\$' | head -1")
NP=$(ssh -o BatchMode=yes "$HOST" "sudo -u postgres psql -At -d labuse -c \"SELECT count(*) FROM score_labuse WHERE run_label='$PROD_RUN'\"" 2>/dev/null || echo 0)
if [ "${NP:-0}" -lt 1 ]; then
  echo "✗ ALERTE : la prod sert '$PROD_RUN' mais ce run n'a aucune donnée score_labuse — /readyz va échouer." >&2
  exit 1
fi
echo "   manifeste prod : '$PROD_RUN' ($NP lignes) ✓"

# ── VITESSE-2 (Lot 4) + REMISE-1 (Lot A) — RESTART → readyz STABLE → RÉCHAUFFAGE ─────────────
# Le code déployé change la version (deploiement.json) → la CLÉ DE FRAÎCHEUR change → les caches
# partagés (comparateur_raw_cache des 24 communes, commune_contexte_cache) deviennent périmés :
# sans réchauffage, chaque worker froid recalcule au 1ᵉʳ clic (DEPLOY-1028 §Phase 4 : ~5 s, plusieurs
# fois/jour). On relance le job `fiche-commune-cache` (il réchauffe D'ABORD comparateur_raw_cache
# puis les 24 fiches communes), DÉTACHÉ (setsid) et JOURNALISÉ.
#
# REMISE-1 (Lot A) — INCIDENT DEPLOY-1028b : le job de réchauffage (gros 6-joins + DVF, lecteurs
# concurrents) partait AVANT/PENDANT que les workers rejouaient leur heal de schéma au (re)démarrage.
# L'ALTER du heal (ex. `pige_biens ADD COLUMN`) percutait un lecteur du job → verrou → heal_failed →
# `/readyz` 503 ~40 % jusqu'à un restart manuel. CORRECTIF : on RESTART le service, on attend que
# `/readyz` soit 200 STABLE (25 succès CONSÉCUTIFS : le heal des workers a convergé, plus aucun ALTER
# en vol), et SEULEMENT APRÈS on lance le job — plus aucune contention de verrou possible.
# (Côté code, le heal est en outre résilient : lock_timeout court + 2 réessais par step.)
echo "── 6. restart + attente readyz STABLE + réchauffage des caches (REMISE-1 Lot A) ──"
# Pré-requis : secrets en place. En PREMIER déploiement (env absente), on NE restart/warm PAS ici —
# l'opérateur pose /etc/labuse/labuse.env puis `systemctl enable --now labuse` (le réchauffage par
# worker au boot suffit à l'amorçage ; relancer le job à la main si besoin).
if ! ssh -o BatchMode=yes "$HOST" "test -f /etc/labuse/labuse.env"; then
  echo "   ⚠ /etc/labuse/labuse.env absente (premier déploiement ?) — restart/réchauffage SAUTÉS."
  echo "✓ déployé — reste : /etc/labuse/labuse.env (secrets), puis systemctl enable --now labuse"
  echo "  (au boot, chaque worker se réchauffe seul ; lancer ensuite : labuse jobs run fiche-commune-cache)"
  exit 0
fi
# VITESSE-2 (Lot 7) — INVALIDATION du cache de fiche PARTAGÉ : nouveau code → code_sha change → les
# fiches de l'ancien code ne seraient plus servies ; on VIDE pour libérer l'espace (best-effort).
ssh -o BatchMode=yes "$HOST" "sudo -u postgres psql -d labuse -c 'DELETE FROM fiche_cache' 2>/dev/null || true; echo '   fiche_cache vidé (invalidation déploiement)'"
echo "   restart du service labuse (nouveau code)…"
ssh -o BatchMode=yes "$HOST" 'sudo systemctl restart labuse'
# Attente readyz 200 STABLE : 25 succès CONSÉCUTIFS (un seul 503 remet le compteur à zéro → on ne
# considère stable que lorsque TOUS les workers ont fini leur heal). Plafond ~180 essais (~3 min).
if ssh -o BatchMode=yes "$HOST" "HEALTH_PORT='$HEALTH_PORT' bash -s" <<'REMOTE'
set -u
ok=0; tours=0
while [ "$ok" -lt 25 ]; do
  tours=$((tours + 1))
  if [ "$tours" -gt 180 ]; then
    echo "   ✗ /readyz jamais stable (25/25) après $tours essais" >&2
    exit 1
  fi
  if curl -fsS -o /dev/null "http://127.0.0.1:${HEALTH_PORT}/readyz" 2>/dev/null; then
    ok=$((ok + 1))
  else
    ok=0   # un 503 (heal pas fini sur un worker) → on repart de zéro
  fi
  sleep 1
done
echo "   /readyz 200 STABLE ($ok/25 consécutifs, $tours essais) ✓"
REMOTE
then
  # readyz stable → le heal de TOUS les workers a convergé → AUCUN ALTER en vol → on peut réchauffer
  ssh -o BatchMode=yes "$HOST" 'sudo -u labuse bash -lc "
    set -a; [ -f /etc/labuse/labuse.env ] && . /etc/labuse/labuse.env; set +a
    mkdir -p /var/log/labuse
    setsid nohup /opt/labuse/venv/bin/labuse jobs run fiche-commune-cache \
      >> /var/log/labuse/rechauffage-deploy.log 2>&1 < /dev/null &
    echo \"   job fiche-commune-cache relancé (détaché, APRÈS readyz stable) — journal : /var/log/labuse/rechauffage-deploy.log\"
  "' || echo "   ⚠ relance du job non bloquante (échec ssh/labuse) — à relancer : labuse jobs run fiche-commune-cache"
else
  echo "   ✗ /readyz non stable — job de réchauffage NON lancé (on n'empile pas la contention)." >&2
  echo "     Diagnostiquer : curl /readyz (heal_failed ?), journaux du service ; puis relancer" >&2
  echo "     labuse jobs run fiche-commune-cache une fois readyz stable." >&2
  exit 6
fi

echo "✓ déployé — service redémarré, /readyz 200 stable, caches en réchauffage."
echo "  (chaque worker s'est réchauffé au boot : indicateurs 24 communes + 3 fiches témoins ;"
echo "   le job fiche-commune-cache a (re)peuplé les caches partagés en base, sans contention.)"
