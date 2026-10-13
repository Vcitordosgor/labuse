#!/bin/bash
# SOLIDITE-1 (Lot 1.5) — LA GARDE EXTERNE. Tourne SUR LE MAC (hors du VPS), toutes les 15 min via
# launchd, et sonde https://app.labuse.immo/readyz. C'est la seule alerte qui survit à la mort du
# serveur entier : si le VPS tombe, l'alerte in-app ne peut plus partir — celle-ci, oui.
#
# Anti-déluge (mêmes règles que l'alerte in-app) : alerte au PASSAGE en panne (après 2 échecs
# consécutifs, pour amortir un redémarrage), UN rappel par jour tant que c'est en panne, et un mail
# « rétabli » au retour. État dans ~/.labuse/readyz_watch.state.
#
# Canaux d'alerte, dans l'ordre :
#   · mail Brevo (si LABUSE_BREVO_API_KEY posée) — POST api.brevo.com/v3/smtp/email ;
#   · notification macOS (osascript) — visible même sans mail ;
#   · toujours : une ligne dans ~/.labuse/readyz_watch.log.
#
# Config (dans le plist, section EnvironmentVariables) :
#   LABUSE_READYZ_URL   (défaut https://app.labuse.immo/readyz)
#   LABUSE_BREVO_API_KEY, LABUSE_ALERT_TO, LABUSE_ALERT_FROM   (mail Brevo — fournis par Vic)
set -u

URL="${LABUSE_READYZ_URL:-https://app.labuse.immo/readyz}"
SEUIL_ECHECS="${LABUSE_READYZ_SEUIL:-2}"
DIR="$HOME/.labuse"
STATE="$DIR/readyz_watch.state"
LOG="$DIR/readyz_watch.log"
mkdir -p "$DIR"

now="$(date -u +%FT%TZ)"
jour="$(date -u +%F)"

# état précédent : statut (up|down|inconnu), nombre d'échecs consécutifs, jour du dernier mail
statut="inconnu"; fails=0; dernier_mail=""
if [ -f "$STATE" ]; then
  # shellcheck disable=SC1090
  . "$STATE"
fi

# sonde — code HTTP ; 200 = prêt. Timeout 20 s, suit les redirections.
code="$(curl -sS -m 20 -o /tmp/labuse_readyz.body -w '%{http_code}' -L "$URL" 2>/tmp/labuse_readyz.err || echo 000)"
if [ "$code" = "200" ]; then
  sain=1
else
  sain=0
fi

envoyer() {
  sujet="$1"; corps="$2"
  echo "$now  ALERTE  $sujet — $corps" >> "$LOG"
  # mail Brevo (transactionnel) si la clé est là
  if [ -n "${LABUSE_BREVO_API_KEY:-}" ] && [ -n "${LABUSE_ALERT_TO:-}" ]; then
    from="${LABUSE_ALERT_FROM:-labuse@app.labuse.immo}"
    curl -sS -m 20 -X POST 'https://api.brevo.com/v3/smtp/email' \
      -H "api-key: ${LABUSE_BREVO_API_KEY}" -H 'content-type: application/json' \
      -d "{\"sender\":{\"email\":\"${from}\"},\"to\":[{\"email\":\"${LABUSE_ALERT_TO}\"}],\"subject\":$(_json "$sujet"),\"textContent\":$(_json "$corps")}" \
      >> "$LOG" 2>&1 && echo "$now  (mail Brevo envoyé)" >> "$LOG"
  fi
  # notification macOS (toujours — visible sans ouvrir le mail)
  osascript -e "display notification \"${corps}\" with title \"${sujet}\"" >/dev/null 2>&1 || true
}

# échappe une chaîne en littéral JSON (guillemets inclus) — pas de dépendance (python présent sur mac).
_json() { printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

if [ "$sain" -eq 1 ]; then
  if [ "$statut" = "down" ]; then
    envoyer "[LABUSE] serveur RÉTABLI" "https://app.labuse.immo/readyz répond de nouveau (200)."
  fi
  statut="up"; fails=0; dernier_mail=""
  echo "$now  OK (200)" >> "$LOG"
else
  fails=$((fails + 1))
  motif="$(head -c 200 /tmp/labuse_readyz.body 2>/dev/null)"
  echo "$now  ÉCHEC code=$code fails=$fails" >> "$LOG"
  if [ "$fails" -ge "$SEUIL_ECHECS" ]; then
    if [ "$statut" != "down" ]; then
      envoyer "[LABUSE] serveur INJOIGNABLE" "/readyz = $code (${fails} échecs). Détail: ${motif}"
      statut="down"; dernier_mail="$jour"
    elif [ "$dernier_mail" != "$jour" ]; then
      envoyer "[LABUSE] serveur toujours injoignable" "/readyz = $code depuis hier. Rappel quotidien."
      dernier_mail="$jour"
    fi
  fi
fi

# persiste l'état (format sourçable par sh)
cat > "$STATE" <<EOF
statut="$statut"
fails=$fails
dernier_mail="$dernier_mail"
EOF
