#!/bin/bash
# =============================================================================
# DISQUE-EXTERNE-1 (14/10) — COPIE DES SAUVEGARDES HORS DU VPS, SUR LE DISQUE EXTERNE DU MAC.
# -----------------------------------------------------------------------------
# Remplace l'ancienne copie vers un stockage objet chiffré (deploy/scripts/backup_offsite.sh, retiré).
# Un VPS perdu (feu, rançongiciel) ne doit pas emporter les sauvegardes : ce script tourne SUR LE MAC
# (lancé par launchd quand le disque est branché, et chaque dimanche s'il l'est), tire le DERNIER dump
# du VPS par ssh (sens TIRÉ — le VPS ne détient aucun accès vers chez nous), VÉRIFIE l'empreinte
# (sha256 calculée sur le VPS) et la lisibilité (`pg_restore --list`), puis range le dump sur le disque.
#
#   · Un dossier DÉDIÉ `LABUSE-SAUVEGARDES` à la racine du disque. On ne touche RIEN d'autre sur le disque.
#   · On ne touche JAMAIS le volume Time Machine « SAUVEGARDE HD » (garde explicite en tête de script).
#   · JAMAIS d'écrasement sans vérification réussie : on copie dans un `.part`, on vérifie, puis on
#     renomme atomiquement. Un fichier déjà en place et bon n'est jamais remplacé par de l'invérifié.
#   · Rétention : les 8 dernières hebdomadaires + 1 par mois sur 12 mois (sur le seul dossier dédié).
#   · Après chaque copie vérifiée, le Mac INSCRIT la date sur le VPS (marqueur .copie-externe.json) :
#     le récap du matin l'affiche, et une alerte « branche le disque » part si elle a plus de 10 j.
#
# Config (plist EnvironmentVariables) :
#   LABUSE_VPS_SSH            alias ssh du VPS (défaut labuse-vps)
#   LABUSE_REMOTE_BACKUP      dossier des dumps sur le VPS (défaut /var/backups/labuse)
#   LABUSE_OFFSITE_DISK       point de montage du disque (défaut /Volumes/MUSIQUE-VIDEO)
#   LABUSE_OFFSITE_DIRNAME    dossier dédié à la racine (défaut LABUSE-SAUVEGARDES)
#   PG_RESTORE_BIN            pg_restore >= la majeure PostgreSQL du VPS (défaut pg_restore du PATH)
#   LABUSE_OFFSITE_KEEP_WEEKLY   nb d'hebdomadaires gardées (défaut 8)
#   LABUSE_OFFSITE_KEEP_MONTHLY  nb de mensuelles gardées (défaut 12)
#   LABUSE_BREVO_API_KEY, LABUSE_ALERT_TO, LABUSE_ALERT_FROM   (mail d'alerte — sinon notif macOS + log)
# =============================================================================
set -u

SSHV="${LABUSE_VPS_SSH:-labuse-vps}"
REMOTE_DIR="${LABUSE_REMOTE_BACKUP:-/var/backups/labuse}"
DISK="${LABUSE_OFFSITE_DISK:-/Volumes/MUSIQUE-VIDEO}"
DIRNAME="${LABUSE_OFFSITE_DIRNAME:-LABUSE-SAUVEGARDES}"
PG_RESTORE="${PG_RESTORE_BIN:-pg_restore}"
KEEP_WEEKLY="${LABUSE_OFFSITE_KEEP_WEEKLY:-8}"
KEEP_MONTHLY="${LABUSE_OFFSITE_KEEP_MONTHLY:-12}"
# Volume à NE JAMAIS toucher (Time Machine du Mac). Garde dure, non surchargeable par erreur.
INTERDIT="/Volumes/SAUVEGARDE HD"

DEST="$DISK/$DIRNAME"
STATEDIR="$HOME/.labuse"; LOG="$STATEDIR/backup_offsite_disque.log"
mkdir -p "$STATEDIR"
now="$(date -u +%FT%TZ)"
disk_label="$(basename "$DISK")"

log()  { echo "$now  $*" >> "$LOG"; }
_json() { printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }
alerter() {    # alerte DURE (copie invérifiable) : mail Brevo si configuré + notif macOS + log
  sujet="$1"; corps="$2"
  log "ALERTE  $sujet — $corps"
  if [ -n "${LABUSE_BREVO_API_KEY:-}" ] && [ -n "${LABUSE_ALERT_TO:-}" ]; then
    from="${LABUSE_ALERT_FROM:-labuse@app.labuse.immo}"
    curl -sS -m 20 -X POST 'https://api.brevo.com/v3/smtp/email' \
      -H "api-key: ${LABUSE_BREVO_API_KEY}" -H 'content-type: application/json' \
      -d "{\"sender\":{\"email\":\"${from}\"},\"to\":[{\"email\":\"${LABUSE_ALERT_TO}\"}],\"subject\":$(_json "$sujet"),\"textContent\":$(_json "$corps")}" >> "$LOG" 2>&1
  fi
  osascript -e "display notification \"${corps}\" with title \"${sujet}\"" >/dev/null 2>&1 || true
}

# ── GARDE DURE : ne jamais écrire ailleurs que dans le dossier dédié du bon disque ───────────────────
case "$DEST" in
  "$INTERDIT"/*|"$INTERDIT") echo "REFUS : la destination tombe sur le volume Time Machine « $INTERDIT »." >&2; log "REFUS destination = volume interdit"; exit 2 ;;
esac
case "$DIRNAME" in */*|*..*|"") echo "REFUS : nom de dossier dédié invalide ($DIRNAME)." >&2; exit 2 ;; esac
case "$DEST" in "$DISK"/*) : ;; *) echo "REFUS : la destination n'est pas sous le disque ($DISK)." >&2; exit 2 ;; esac

# ── le disque est-il branché ? sinon, rien à faire (lancé à chaque montage de volume) ───────────────
if [ ! -d "$DISK" ]; then
  log "disque « $disk_label » non branché — rien à faire (la vigie VPS rappellera « branche le disque » après 10 j)."
  exit 0
fi
mkdir -p "$DEST" || { alerter "[LABUSE] copie externe : dossier KO" "Impossible de créer $DEST"; exit 1; }
log "▶ copie externe vers $DEST (disque « $disk_label »)"

# ── 1) dernier dump du VPS : chemin, empreinte, taille (calculés SUR LE VPS) ─────────────────────────
REMOTE_PATH="$(ssh -o ConnectTimeout=15 "$SSHV" "ls -1t ${REMOTE_DIR}/labuse-labuse-*.dump 2>/dev/null | head -1")"
if [ -z "$REMOTE_PATH" ]; then
  log "VPS injoignable ou aucun dump — on réessaiera au prochain montage/dimanche (pas d'alerte dure)."
  exit 1
fi
NAME="$(basename "$REMOTE_PATH")"
REMOTE_SHA="$(ssh -o ConnectTimeout=15 "$SSHV" "sha256sum '$REMOTE_PATH'" | awk '{print $1}')"
REMOTE_SIZE="$(ssh -o ConnectTimeout=15 "$SSHV" "stat -c %s '$REMOTE_PATH'" 2>/dev/null)"
if [ -z "$REMOTE_SHA" ]; then log "empreinte VPS illisible — on réessaiera."; exit 1; fi
taille_mo="$(python3 -c "print(round(${REMOTE_SIZE:-0}/1e6,1))" 2>/dev/null || echo 0)"
log "dernier dump VPS : $NAME ($taille_mo Mo) sha256=${REMOTE_SHA:0:12}…"

DESTFILE="$DEST/$NAME"
PART="$DEST/.$NAME.part"

verifier() {   # $1 = fichier local → 0 si sha256 == VPS ET pg_restore --list sain
  f="$1"
  loc_sha="$(shasum -a 256 "$f" 2>/dev/null | awk '{print $1}')"
  if [ "$loc_sha" != "$REMOTE_SHA" ]; then log "✗ sha256 divergent sur $(basename "$f") (local=${loc_sha:0:12}… vps=${REMOTE_SHA:0:12}…)"; return 1; fi
  n="$("$PG_RESTORE" --list "$f" 2>/dev/null | grep -c -v '^;')"
  if [ -z "$n" ] || [ "$n" -lt 50 ]; then log "✗ pg_restore --list maigre/illisible sur $(basename "$f") (objets=${n:-0})"; return 1; fi
  log "✓ vérifié $(basename "$f") : sha256 OK + pg_restore --list ($n objets)"
  return 0
}

# ── 2) déjà présent et bon ? sinon copie dans .part, vérification, puis renommage atomique ──────────
if [ -f "$DESTFILE" ] && verifier "$DESTFILE"; then
  log "déjà en place et vérifié : $NAME (aucune re-copie)"
else
  log "copie rsync depuis le VPS…"
  rm -f "$PART"
  if ! rsync -az --partial --timeout=600 "$SSHV:$REMOTE_PATH" "$PART" >>"$LOG" 2>&1; then
    alerter "[LABUSE] copie externe : rsync KO" "Échec du rsync de $NAME depuis $SSHV."
    rm -f "$PART"; exit 1
  fi
  if ! verifier "$PART"; then
    # JAMAIS d'écrasement sans vérification réussie : on jette le .part, on ne touche pas au bon fichier.
    alerter "[LABUSE] copie externe : VÉRIFICATION ÉCHOUÉE" \
            "Le dump $NAME rapatrié ne passe pas la vérification (sha256 ou pg_restore). Copie NON validée, rien écrasé."
    rm -f "$PART"; exit 1
  fi
  mv -f "$PART" "$DESTFILE" || { alerter "[LABUSE] copie externe : rangement KO" "mv $PART → $DESTFILE a échoué."; rm -f "$PART"; exit 1; }
  log "✓ rangé : $DESTFILE"
fi

# ── 3) inscrire la date sur le VPS (marqueur lu par le récap / la vigie « branche le disque ») ──────
MARQUEUR="{\"copie_at\":\"$now\",\"dump\":\"$NAME\",\"sha256\":\"$REMOTE_SHA\",\"taille_mo\":$taille_mo,\"disque\":\"$disk_label\"}"
if printf '%s' "$MARQUEUR" | ssh -o ConnectTimeout=15 "$SSHV" "sudo -n -u labuse tee ${REMOTE_DIR}/.copie-externe.json >/dev/null" 2>>"$LOG"; then
  log "✓ date inscrite sur le VPS (${REMOTE_DIR}/.copie-externe.json)"
else
  log "⚠ marqueur non inscrit sur le VPS (copie locale faite quand même) — le récap le signalera après 10 j."
fi

# ── 4) rétention : 8 hebdomadaires + 1 par mois sur 12 mois (dossier dédié UNIQUEMENT) ──────────────
# Fichiers du dossier dédié, du plus récent au plus ancien (ne sort JAMAIS de $DEST).
FICHIERS="$(ls -1t "$DEST"/labuse-labuse-*.dump 2>/dev/null)"
[ -z "$FICHIERS" ] && { log "rétention : aucun dump à élaguer."; exit 0; }

GARDES=""                         # ensemble à conserver (chemins, un par ligne)
i=0
for f in $FICHIERS; do            # 8 hebdomadaires = les 8 plus récents
  i=$((i+1)); [ "$i" -le "$KEEP_WEEKLY" ] && GARDES="$GARDES$f
"
done
MOIS_VUS=" "; nm=0                 # 1 mensuelle par mois (le plus récent du mois), 12 mois
for f in $FICHIERS; do
  ym="$(basename "$f" | sed -n 's/^labuse-labuse-\([0-9]\{6\}\)[0-9]\{2\}-.*$/\1/p')"
  [ -z "$ym" ] && continue
  case "$MOIS_VUS" in *" $ym "*) continue ;; esac
  [ "$nm" -ge "$KEEP_MONTHLY" ] && continue
  MOIS_VUS="$MOIS_VUS$ym "; nm=$((nm+1))
  GARDES="$GARDES$f
"
done

for f in $FICHIERS; do
  case "
$GARDES" in *"
$f
"*) : ;; *) rm -f "$f" && log "rétention : retiré $(basename "$f")" ;; esac
done
# un fichier peut figurer DEUX fois dans GARDES (il est à la fois une hebdomadaire ET une mensuelle) :
# on compte les dumps RÉELLEMENT présents dans le dossier, pas les lignes de l'ensemble à garder.
ngardes="$(ls -1 "$DEST"/labuse-labuse-*.dump 2>/dev/null | grep -c .)"
log "✓ copie externe OK — $ngardes dump(s) conservé(s) dans $DEST ($disk_label)."
echo "$now  ✓ copie externe vérifiée et rangée : $NAME" >> "$LOG"
