import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { M09 } from './ModulePanel'

// Mandat COURRIER — service d'envoi en 3 étapes : destinataires → rédaction → DEMANDER l'envoi à
// LABUSE. OUTILS-1 A4/B6 : la confirmation porte le N° de demande + renvoi « Mes courriers », SANS
// état interne d'exécution (le cycle imprimé/posté reste à la Tour de contrôle admin).
const FICHE = { commune: 'Saint-Denis', surface_m2: 1625 }
// RECETTE-1 R13 — le back renvoie `rang_compte` (rang PROPRE AU COMPTE) ; l'id 42 est la PK globale
// qui ne doit PLUS être montrée au client (elle fuitait le volume plateforme).
const DEMANDE = { ok: true, id: 42, rang_compte: 3, ts: 't', n: 1, communes: 'Saint-Denis ×1', statut: 'demande' }

function mockFetch() {
  global.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const u = String(url)
    if (u.includes('/courrier/demande') && init?.method === 'POST') return { ok: true, json: async () => DEMANDE }
    if (u.includes('/courrier/demandes')) return { ok: true, json: async () => ({ demandes: [] }) }
    if (u.includes('/parcels/')) return { ok: true, json: async () => FICHE }
    return { ok: true, json: async () => ({}) }
  }) as unknown as typeof fetch
}
function renderTool() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><M09 /></QueryClientProvider>)
}

describe('COURRIER — service d\'envoi (3 étapes)', () => {
  beforeEach(() => {
    mockFetch()
    // import « en un geste » depuis Assemblage : le prefill multi-parcelles amorce les destinataires.
    useApp.setState({ courrierPrefillIdus: ['97411000BZ1065'], courrierPrefill: null, selectedIdu: null, msel: [] })
  })
  afterEach(() => { vi.restoreAllMocks(); useApp.setState({ courrierPrefillIdus: null }) })

  it('① le prefill Assemblage amorce un destinataire (chip)', async () => {
    renderTool()
    await waitFor(() => expect(document.querySelectorAll('[data-courrier-dest]').length).toBe(1))
    expect(screen.getByText('BZ 1065')).toBeTruthy()   // idu court dans la chip
  })

  it('parcours complet → « Demander l\'envoi » → confirmation avec n° (SANS état interne)', async () => {
    renderTool()
    await waitFor(() => expect(document.querySelectorAll('[data-courrier-dest]').length).toBe(1))
    // ① → ②
    fireEvent.click(document.querySelector('[data-courrier-next]')!)
    // ② modèles présents (dont « Approche standard »), corps par défaut rempli
    expect(document.querySelector('[data-courrier-modele="standard"]')).toBeTruthy()
    expect((document.querySelector('[data-courrier-texte]') as HTMLTextAreaElement).value.length).toBeGreaterThan(10)
    // ② → ③
    fireEvent.click(document.querySelector('[data-courrier-next]')!)
    // ③ demander l'envoi
    fireEvent.click(document.querySelector('[data-courrier-demander]')!)
    await waitFor(() => expect(document.querySelector('[data-courrier-confirm]')).toBeTruthy())
    // RECETTE-1 R13 — la confirmation porte le rang PROPRE AU COMPTE (n° 3), PAS le id PK global (42).
    expect(screen.getByText(/Demande n° 3 transmise/)).toBeTruthy()
    expect(screen.queryByText(/n° 42/)).toBeNull()
    expect(screen.getByText(/Mes courriers/)).toBeTruthy()
    // AUCUN état interne (imprimé/posté) ni timeline côté client.
    expect(screen.queryByText('Imprimé')).toBeNull()
    expect(screen.queryByText('Posté')).toBeNull()
  })

  it('③ aperçu PDF de relecture disponible (secondaire)', async () => {
    renderTool()
    await waitFor(() => expect(document.querySelectorAll('[data-courrier-dest]').length).toBe(1))
    fireEvent.click(document.querySelector('[data-courrier-next]')!)   // → ②
    fireEvent.click(document.querySelector('[data-courrier-next]')!)   // → ③
    expect(document.querySelector('[data-courrier-pdf]')).toBeTruthy()
  })

  it('CONNEXIONS-2 Lot 3 (KO-5) — prefill MONO parcelle (fiche → Courrier) amorce un destinataire', async () => {
    // La tuile/porte « Courrier » de la fiche pose `courrierPrefill` (IDU seul) avant d'ouvrir l'outil.
    // Avant le fix, l'outil s'ouvrait VIDE. Échoue si le canal mono n'amorce pas de destinataire.
    useApp.setState({ courrierPrefillIdus: null, courrierPrefill: '97411000BZ1065', selectedIdu: null, msel: [] })
    renderTool()
    await waitFor(() => expect(document.querySelectorAll('[data-courrier-dest]').length).toBe(1))
    expect(screen.getByText('BZ 1065')).toBeTruthy()
  })
})
