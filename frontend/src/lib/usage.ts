// DASHBOARD-V1 · D1 — capteur d'usage FIRE-AND-FORGET (Tour de contrôle).
// Des compteurs, jamais du contenu : (outil, ts) à l'ouverture d'un outil + un heartbeat de
// session (pas de 5 min, onglet visible seulement) pour estimer le temps d'usage. Aucune
// erreur ne remonte jamais à l'UI — un capteur en panne ne doit rien casser côté client.

const last: Record<string, number> = {}

function send(body: { kind: 'outil' | 'heartbeat'; outil?: string }) {
  try {
    fetch('/usage/event', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body), keepalive: true,
    }).catch(() => {})
  } catch { /* capteur best-effort */ }
}

/** Ouverture d'outil — dédoublonnée à 1/min/outil (les re-rendus React ne comptent pas). */
export function signalOutil(outil: string) {
  const now = Date.now()
  if (now - (last[outil] ?? 0) < 60_000) return
  last[outil] = now
  send({ kind: 'outil', outil: outil.slice(0, 48) })
}

/** Heartbeat de session : une balise à l'ouverture puis toutes les 5 min si l'onglet est
 *  visible. Le temps d'usage servi au dashboard = nombre de balises × 5 min (estimation dite). */
export function startHeartbeat() {
  send({ kind: 'heartbeat' })
  window.setInterval(() => {
    if (document.visibilityState === 'visible') send({ kind: 'heartbeat' })
  }, 5 * 60_000)
}
