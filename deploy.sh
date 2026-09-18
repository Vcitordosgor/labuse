#!/bin/sh
# CRON-1 (lot 3) — POSE de l'exploitation planifiée sur le serveur, DEPUIS LE REGISTRE.
# À lancer SUR LE VPS (root). Le crontab /etc/cron.d/labuse est GÉNÉRÉ depuis le registre
# (labuse.jobs) — jamais écrit à la main. Trois principes :
#
#   1. VERROUS — `labuse circuit verrous` est la porte : un verrou OU une garantie BLOQUANTE
#      cassée → refus. G8 est NON BLOQUANT (`-w G8`) : il mesure la FRAÎCHEUR DE LA VEILLE
#      (sources hors sonde, agent à 0 €), pas la santé du code. Déployer n'aggrave jamais ce
#      que G8 signale, et le bloquer empêcherait de poser les horloges qui le feraient passer
#      au vert. G8 s'AFFICHE (sources nommées), n'empêche pas.
#   2. REGISTRE = VÉRITÉ — le crontab est régénéré du registre et VÉRIFIÉ : aucun écart toléré
#      (un crontab édité à la main est refusé). Les fichiers legacy /etc/cron.d/labuse-* (hors
#      registre) sont RETIRÉS.
#   3. BACKUP SANS TROU — le nouveau crontab (qui contient le backup, à l'horaire EXACT du legacy)
#      est posé AVANT le retrait des legacy → jamais une nuit sans sauvegarde.
#
#   FUSEAU — le registre porte les heures en UTC ; `labuse jobs crontab --tz reunion` convertit
#   (+4 h, modulo 24) pour un serveur en Indian/Reunion (le piège qui bloquait l'ancien wrapper).
#
# Idempotent. N'installe RIEN d'autre (code/venv/systemd : deploy/scripts/deploy_app.sh).
set -eu

REPO="$(cd "$(dirname "$0")" && pwd)"
LABUSE_BIN="${LABUSE_BIN:-$(command -v labuse || echo /opt/labuse/venv/bin/labuse)}"

# ── Porte 1 : les verrous (G8 non bloquant) ────────────────────────────────────────────────
echo "→ Porte des verrous : $LABUSE_BIN circuit verrous -w G8…"
if [ ! -x "$LABUSE_BIN" ]; then
  echo "✗ REFUS : binaire labuse introuvable ($LABUSE_BIN) — on ne déploie pas sans jouer les verrous." >&2
  exit 1
fi
if ! "$LABUSE_BIN" circuit verrous --par deploy -w G8; then
  cat >&2 <<MSG
✗ REFUS : un verrou BLOQUANT est cassé (détail ci-dessus, phrases dans docs/CIRCUIT/VERROUS.md).
  (G8 « sources sans contrôle » est non bloquant : il s'affiche mais n'empêche pas le déploiement.)
  Corriger, rejouer « labuse circuit verrous », puis relancer ce déploiement.
MSG
  exit 1
fi
echo "  ✓ verrous bloquants OK (G8 en avertissement si rouge — non bloquant)"

# ── Porte 2 : la suite de tests ────────────────────────────────────────────────────────────
echo "→ Porte de la suite : $LABUSE_BIN circuit suite…"
if ! "$LABUSE_BIN" circuit suite --racine "$REPO"; then
  echo "✗ REFUS : la suite de tests n'est pas verte (détail ci-dessus)." >&2
  exit 1
fi
echo "  ✓ la suite est verte"

# ── Fuseau serveur → tz de génération ──────────────────────────────────────────────────────
echo "→ Fuseau serveur…"
srvtz="$(timedatectl show -p Timezone --value 2>/dev/null || cat /etc/timezone 2>/dev/null || echo inconnu)"
case "$srvtz" in
  UTC|Etc/UTC)        gentz="utc"     ; echo "  ✓ UTC" ;;
  Indian/Reunion)     gentz="reunion" ; echo "  ✓ Indian/Reunion — conversion +4 h du registre" ;;
  *) echo "✗ REFUS : fuseau serveur « $srvtz » ni UTC ni Indian/Reunion (le registre est en UTC)." >&2; exit 1 ;;
esac

# ── Pose du crontab GÉNÉRÉ depuis le registre (AVANT retrait legacy → backup sans trou) ─────
echo "→ Génération du crontab depuis le registre (tz=$gentz)…"
tmp="$(mktemp)"
"$LABUSE_BIN" jobs crontab --tz "$gentz" > "$tmp"
install -o root -g root -m 644 "$tmp" /etc/cron.d/labuse
rm -f "$tmp"
echo "  ✓ /etc/cron.d/labuse posé (contient le backup à son horaire exact — pose avant retrait legacy)"

# ── Refuse tout écart : le fichier posé DOIT être le registre régénéré ──────────────────────
echo "→ Vérification : aucun écart crontab/registre…"
if ! "$LABUSE_BIN" jobs crontab --tz "$gentz" --verifier /etc/cron.d/labuse; then
  echo "✗ REFUS : /etc/cron.d/labuse diverge du registre (édité à la main ?)." >&2
  exit 1
fi

# ── Retrait des fichiers legacy /etc/cron.d/labuse-* (hors registre) — APRÈS la pose du neuf ─
echo "→ Retrait des crons legacy /etc/cron.d/labuse-* (hors registre)…"
legacy="$(ls /etc/cron.d/labuse-* 2>/dev/null || true)"
if [ -n "$legacy" ]; then
  sauve="/root/crons-legacy-$(date +%Y%m%d-%H%M)"; mkdir -p "$sauve"
  for f in $legacy; do cp "$f" "$sauve/"; rm "$f"; echo "  − $f (sauvé dans $sauve/)"; done
  echo "  ✓ legacy retiré ($(echo "$legacy" | wc -w | tr -d ' ') fichiers) — le nouveau crontab était déjà posé (aucun trou)"
else
  echo "  ✓ aucun cron legacy"
fi
command -v systemctl >/dev/null 2>&1 && systemctl restart cron 2>/dev/null || service cron restart 2>/dev/null || true

# ── logrotate + dossiers d'état/logs ───────────────────────────────────────────────────────
echo "→ Pose du logrotate + dossiers d'état/logs…"
install -o root -g root -m 644 "$REPO/deploy/logrotate.d/labuse-jobs" /etc/logrotate.d/labuse-jobs
install -d -o labuse -g labuse -m 755 /opt/labuse/state/jobs /var/log/labuse
echo "  ✓ logrotate (30 j) · /opt/labuse/state/jobs · /var/log/labuse"

echo "✓ Exploitation planifiée posée depuis le registre. Vérifier : labuse jobs list · tail -f /var/log/labuse/*.log"
