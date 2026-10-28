#!/bin/bash
# MENAGE-1 (geste 11) — L'ALARME DISQUE DU MAC. Tourne SUR LE MAC via launchd (toutes les 30 min) et
# alerte quand le disque de travail passe SOUS un seuil (défaut 5 Go). C'est le poste qui coince le
# travail quotidien : le 28/10, le Mac était à 649 Mo libres (un VACUUM FULL devenait impossible — cf.
# rapport MENAGE-1, encadré « Urgence Mac »). Mieux vaut être prévenu à 5 Go qu'à 0.
#
# Canaux (comme readyz_watch) :
#   · notification macOS (osascript) — visible même sans mail ;
#   · toujours : une ligne dans ~/.labuse/alerte_disque.log.
# Anti-déluge : UNE notification par jour tant qu'on est sous le seuil ; une ligne « rétabli » au retour.
#
# Config (dans le plist, EnvironmentVariables) :
#   LABUSE_DISK_MIN_GO   seuil d'alerte en Go (défaut 5)
#   LABUSE_DISK_VOLUME   point de montage sondé (défaut /System/Volumes/Data — le conteneur APFS data)
#
# N'écrit QUE dans ~/.labuse : aucun accès disque particulier requis (contrairement à backup-offsite).
set -u

SEUIL_GO="${LABUSE_DISK_MIN_GO:-5}"
VOL="${LABUSE_DISK_VOLUME:-/System/Volumes/Data}"
DIR="$HOME/.labuse"
STATE="$DIR/alerte_disque.state"
LOG="$DIR/alerte_disque.log"
mkdir -p "$DIR"

now="$(date +%FT%T)"
jour="$(date +%F)"

# espace libre en octets (df -k → blocs de 1024). $4 = Avail.
avail_kb="$(df -k "$VOL" 2>/dev/null | awk 'NR==2{print $4}')"
if [ -z "${avail_kb:-}" ]; then
  echo "$now  ERREUR  df sans réponse pour $VOL" >> "$LOG"
  exit 0           # une sonde ne doit jamais faire échouer launchd
fi
avail_octets=$((avail_kb * 1024))
seuil_octets=$((SEUIL_GO * 1000 * 1000 * 1000))   # Go « disque » (base 1000), cohérent avec l'affichage macOS
avail_go="$(awk -v b="$avail_kb" 'BEGIN{printf "%.1f", b*1024/1000000000}')"

# état précédent : statut (ok|bas|inconnu), jour de la dernière notification
statut="inconnu"; derniere_notif=""
if [ -f "$STATE" ]; then
  # shellcheck disable=SC1090
  . "$STATE"
fi

notifier() {
  titre="$1"; corps="$2"
  echo "$now  ALERTE  $titre — $corps" >> "$LOG"
  osascript -e "display notification \"${corps}\" with title \"${titre}\"" >/dev/null 2>&1 || true
}

if [ "$avail_octets" -lt "$seuil_octets" ]; then
  # sous le seuil : une notification par jour (anti-déluge)
  if [ "$derniere_notif" != "$jour" ]; then
    notifier "[LABUSE] Disque Mac bas" "Il reste ${avail_go} Go libres (seuil ${SEUIL_GO} Go) sur ${VOL}. Fais le ménage : worktrees mergés, vieux dumps, runs Postgres (cf. rapport MENAGE-1)."
    derniere_notif="$jour"
  else
    echo "$now  BAS ${avail_go} Go (< ${SEUIL_GO}) — déjà notifié aujourd'hui" >> "$LOG"
  fi
  statut="bas"
else
  if [ "$statut" = "bas" ]; then
    echo "$now  RÉTABLI ${avail_go} Go libres (>= ${SEUIL_GO})" >> "$LOG"
  else
    echo "$now  OK ${avail_go} Go libres" >> "$LOG"
  fi
  statut="ok"; derniere_notif=""
fi

# persiste l'état (écriture atomique)
tmp="$STATE.tmp"
{ echo "statut=$statut"; echo "derniere_notif=$derniere_notif"; } > "$tmp" && mv "$tmp" "$STATE"
exit 0
