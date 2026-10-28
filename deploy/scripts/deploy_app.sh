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

# ── VITESSE-2 (Lot 4) — RÉCHAUFFAGE DES CACHES APRÈS DÉPLOIEMENT ──────────────────────────────
# Le code déployé change la version (deploiement.json) → la CLÉ DE FRAÎCHEUR change → les caches
# partagés (comparateur_raw_cache des 24 communes, commune_contexte_cache) deviennent périmés :
# sans réchauffage, chaque worker froid recalcule au 1ᵉʳ clic (DEPLOY-1028 §Phase 4 : ~5 s, plusieurs
# fois/jour). On relance le job `fiche-commune-cache` (il réchauffe D'ABORD comparateur_raw_cache
# puis les 24 fiches communes), DÉTACHÉ (setsid) et JOURNALISÉ — il ne bloque pas le déploiement.
# Le réchauffage PAR WORKER (indicateurs + 3 fiches témoins en mémoire) est fait par CHAQUE worker
# à son démarrage (événement startup FastAPI, LABUSE_WARM_ON_BOOT) — rien à faire ici côté HTTP.
echo "── 6. réchauffage des caches (job fiche-commune-cache, détaché + journalisé) ──"
# VITESSE-2 (Lot 7) — INVALIDATION AU DÉPLOIEMENT du cache de fiche PARTAGÉ : le nouveau code change
# code_sha → la clé de fraîcheur change → les fiches de l'ancien code ne seraient de toute façon plus
# servies ; on VIDE la table pour libérer l'espace (best-effort, ne bloque jamais le déploiement).
ssh -o BatchMode=yes "$HOST" "sudo -u postgres psql -d labuse -c 'DELETE FROM fiche_cache' 2>/dev/null || true; echo '   fiche_cache vidé (invalidation déploiement)'"
ssh -o BatchMode=yes "$HOST" 'sudo -u labuse bash -lc "
  set -a; [ -f /etc/labuse/labuse.env ] && . /etc/labuse/labuse.env; set +a
  mkdir -p /var/log/labuse
  setsid nohup /opt/labuse/venv/bin/labuse jobs run fiche-commune-cache \
    >> /var/log/labuse/rechauffage-deploy.log 2>&1 < /dev/null &
  echo \"   job fiche-commune-cache relancé (détaché) — journal : /var/log/labuse/rechauffage-deploy.log + le journal du job\"
"' || echo "   ⚠ relance du job non bloquante (échec ssh/labuse) — à relancer à la main : labuse jobs run fiche-commune-cache"

echo "✓ déployé — reste : /etc/labuse/labuse.env (secrets), systemctl enable --now labuse"
echo "  (au restart, chaque worker se réchauffe seul : indicateurs 24 communes + 3 fiches témoins ;"
echo "   le job fiche-commune-cache (étape 6) a (re)peuplé les caches partagés en base.)"
