import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { M09, remplirGabaritCourrier } from './ModulePanel'

// Mandat COURRIER — service d'envoi en 3 étapes : destinataires → rédaction → DEMANDER l'envoi à
// LABUSE. OUTILS-1 A4/B6 : la confirmation porte le N° de demande + renvoi « Mes courriers », SANS
// état interne d'exécution (le cycle imprimé/posté reste à la Tour de contrôle admin).
const FICHE = { commune: 'Saint-Denis', surface_m2: 1625 }
// RECETTE-1 R13 — le back renvoie `rang_compte` (rang PROPRE AU COMPTE) ; l'id 42 est la PK globale
// qui ne doit PLUS être montrée au client (elle fuitait le volume plateforme).
const DEMANDE = { ok: true, id: 42, rang_compte: 3, ts: 't', n: 1, communes: 'Saint-Denis ×1', statut: 'demande' }

// COURRIER-2 Lot 2/3 — l'aperçu (composer) et l'adressage sont servis par le back (source unique).
const APERCU = { recto: 'Objet : Votre parcelle BZ 1065, à Saint-Denis\n\nMadame, Monsieur,\n\nLABUSE est une plateforme…',
  verso: ['Synthèse de la parcelle', 'Référence cadastrale : BZ 1065'], ouverture: 'D', reference: 'BZ 1065',
  destinataire: "À l'occupant", adresse_envoi: '12 Rue X, 97400 Saint-Denis', bloque: false, motif: null }
const RESOLUTION = { idu: '97411000BZ1065', type: 'occupant', destinataire: "À l'occupant",
  adresse_envoi: '12 Rue X, 97400 Saint-Denis', mention: 'pli à l’occupant, non nominatif', bloque: false,
  motif: null, bien: { reference: 'BZ 1065', adresse: '12 Rue X, 97400 Saint-Denis', commune: 'Saint-Denis' } }

function mockFetch() {
  global.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const u = String(url)
    if (u.includes('/courrier/composer')) return { ok: true, json: async () => APERCU }
    if (u.includes('/courrier/adressage')) return { ok: true, json: async () => ({ resolutions: [RESOLUTION] }) }
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

  // RECETTE-2 (S8) — un champ vide ne s'imprime jamais dans une lettre postale : ni « — », ni « (—) »,
  // ni « à — ». Commune/surface absente → le segment disparaît, la phrase se reformule sans lui.
  it('S8 — un champ vide ne s\'imprime jamais (segment retiré, jamais « - »)', () => {
    const tpl = 'Objet : votre parcelle {parcelle}, à {commune}\n\n'
      + 'Votre parcelle cadastrée {parcelle} ({surface}), située à {commune}, présente à notre analyse un réel potentiel.'
    // tout renseigné
    const plein = remplirGabaritCourrier(tpl, 'CY 0044', 'Saint-Paul', '748 m²')
    expect(plein).toContain('votre parcelle CY 0044, à Saint-Paul')
    expect(plein).toContain('cadastrée CY 0044 (748 m²), située à Saint-Paul, présente')
    // rien renseigné (fiche non résolue) — AUCUN tiret, phrase reformulée
    const vide = remplirGabaritCourrier(tpl, 'ZZ 9999', '', '')
    expect(vide).not.toMatch(/[—-]/)          // ni tiret cadratin ni trait d'union orphelin
    expect(vide).not.toContain('()')
    expect(vide).not.toContain('à ,')
    expect(vide).toContain('Objet : votre parcelle ZZ 9999')
    expect(vide).toContain('cadastrée ZZ 9999, présente')
    // surface seule manquante
    const sansSurf = remplirGabaritCourrier(tpl, 'AB 12', 'Le Port', '')
    expect(sansSurf).toContain('cadastrée AB 12, située à Le Port, présente')
  })

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
    // ② aperçu COMPOSÉ serveur (lecture seule), plus de gabarit éditable
    await waitFor(() => expect(document.querySelector('[data-courrier-apercu]')).toBeTruthy())
    expect(document.querySelector('[data-courrier-apercu]')!.textContent!.length).toBeGreaterThan(10)
    // ② → ③
    fireEvent.click(document.querySelector('[data-courrier-next]')!)
    // ③ adressage résolu, non bloqué → demander l'envoi
    await waitFor(() => expect(document.querySelector('[data-courrier-resolution]')).toBeTruthy())
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
    await waitFor(() => expect(document.querySelector('[data-courrier-apercu]')).toBeTruthy())
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
