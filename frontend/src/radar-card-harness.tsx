// RADAR-FIX-2 (Lot D) — harness de recette : rend la VRAIE <TableauDeBord/> (section « Est-ce que tout
// tourne ? ») pour trois états de la carte Radar — AVANT (pas de carte), APRÈS vert, APRÈS ambre (>48 h).
// Playwright screenshote la page. N'est utilisé qu'en recette (jamais dans l'app).
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createRoot } from 'react-dom/client'

import { CIRCUIT_CSS } from './components/admin/circuit/style'
import { TableauDeBord } from './components/admin/circuit/TableauDeBord'

const tuiles = [
  { id: 'veille', titre: 'Veille des sources', pastille: 'vert', ligne: 'Le veilleur est passé à 07:00 · 99 sources suivies' },
  { id: 'livraisons', titre: 'Livraisons du jour', pastille: 'vert', ligne: 'DVF, BODACC, DPE' },
  { id: 'controle', titre: 'Contrôle de nuit', pastille: 'vert', ligne: '0 chiffre faux chez le client' },
  { id: 'courrier', titre: 'Courrier aux clients', pastille: 'vert', ligne: 'part régulièrement' },
]
const mkData = (radar: any) => ({
  run_servi: 'q_v20', candidat: null,
  cockpit: {
    aujourdhui: { n: 0, cartes: [] },
    tout_tourne: { resume: { postes: 29, vert: 24, echec: 0, arret: 2 }, tuiles },
    mise_a_jour: { etapes: [] },
    radar,
  },
}) as any

const vert = {
  id: 'radar', titre: 'Radar', pastille: 'vert', donnees_on: true, notifs_on: false,
  etat: 'Données ON · Notifications OFF',
  capture: 'Dernière capture auto 28/10 21:17 · 35 annonce(s), 2 page(s)',
  cycle: 'radar-cycle : 04:00',
}
const ambre = {
  id: 'radar', titre: 'Radar', pastille: 'ambre', donnees_on: true, notifs_on: false,
  etat: 'Données ON · Notifications OFF',
  capture: 'Aucune capture automatique',
  cycle: 'radar-cycle : 04:00',
}

const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
const Panneau = ({ titre, radar }: { titre: string; radar: any }) => (
  <div style={{ marginBottom: 26 }}>
    <div style={{ color: '#94a099', font: '600 12px system-ui', margin: '0 0 8px 2px', letterSpacing: '.04em' }}>{titre}</div>
    <div className="cxp">
      <style>{CIRCUIT_CSS}</style>
      <TableauDeBord data={mkData(radar)} onVoirUsine={() => {}} onDepotManuel={() => {}} />
    </div>
  </div>
)

createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={qc}>
    <div style={{ padding: '18px 24px 60px', background: '#0f1512', minHeight: '100vh', maxWidth: 980, margin: '0 auto', color: '#e7ece8', font: '14px system-ui' }}>
      <Panneau titre="AVANT — RADAR-ETAT-1 (aucune carte Radar)" radar={null} />
      <Panneau titre="APRÈS — Données ON / Notifications OFF · capture récente (vert)" radar={vert} />
      <Panneau titre="APRÈS — pas de capture depuis 48 h (ambre)" radar={ambre} />
    </div>
  </QueryClientProvider>,
)
