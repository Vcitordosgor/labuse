import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { MODULES } from './registry'
import { EtudeEcran } from './EtudeEcran'
import { DocumentsView } from '../documents/DocumentsView'

// IMPLANTATION-4 (LOT A) — l'Étude de faisabilité a QUITTÉ les Outils et vit dans Docs : overlay plein
// écran piloté par le store (`etudeIdus`), ouvert par la 9e carte Docs / la tuile fiche / le pont
// Assemblage / les anciens liens #m=programme. On vérifie : (1) `programme` n'est plus une carte du menu
// (verrou du nombre d'outils) ; (2) ouvrir/fermer l'overlay et sa fermeture à TOUTE navigation ;
// (3) l'overlay rend l'écran d'étude complet (même composant M22, en embedded).

const qc = () => new QueryClient({ defaultOptions: { queries: { retry: false } } })
const renderEtude = () => render(<QueryClientProvider client={qc()}><EtudeEcran /></QueryClientProvider>)

describe('LOT A — l\'Étude quitte les Outils', () => {
  it('« programme » est au registre mais HORS menu (hidden) — 15 tuiles visibles', () => {
    const prog = MODULES.find((m) => m.key === 'programme')
    expect(prog).toBeTruthy()                 // la clé reste valide (COMPONENTS, rétro-compat liens)
    expect(prog!.hidden).toBe(true)           // mais plus de carte au Rail
    const visibles = MODULES.filter((m) => !m.hidden)
    expect(visibles.some((m) => m.key === 'programme')).toBe(false)
    expect(visibles.length).toBe(15)          // le compte de tuiles a bien baissé (16 → 15)
  })
})

describe('LOT A — overlay Étude dans Docs', () => {
  beforeEach(() => { useApp.setState({ etudeIdus: null }); global.fetch = vi.fn(async (u: string) =>
    (String(u).includes('/moteurs/config')
      ? { ok: true, json: async () => ({ assemblage_max_ecran: 8 }) }
      : { ok: true, json: async () => ({}) }) as never) as unknown as typeof fetch })
  afterEach(() => { vi.restoreAllMocks(); useApp.setState({ etudeIdus: null }) })

  it('ouvrirEtude pose l\'assiette, fermerEtude la retire', () => {
    useApp.getState().ouvrirEtude(['97404000AW0099'])
    expect(useApp.getState().etudeIdus).toEqual(['97404000AW0099'])
    useApp.getState().fermerEtude()
    expect(useApp.getState().etudeIdus).toBeNull()
  })

  it('TOUTE navigation ferme l\'overlay (CLOSE_OVERLAYS)', () => {
    useApp.getState().ouvrirEtude(['97404000AW0099'])
    useApp.getState().setView('documents')
    expect(useApp.getState().etudeIdus).toBeNull()        // fermé par le cleanup centralisé
    useApp.getState().ouvrirEtude(['97404000AW0099'])
    useApp.getState().setModule('assemblage')
    expect(useApp.getState().etudeIdus).toBeNull()
  })

  it('fermé → ne rend rien ; ouvert → l\'écran d\'étude (titre + config, même composant M22)', async () => {
    const { container, rerender } = renderEtude()
    expect(container.querySelector('[data-etude-ecran]')).toBeNull()   // etudeIdus null → rien
    useApp.getState().ouvrirEtude(['97404000AW0099'])
    rerender(<QueryClientProvider client={qc()}><EtudeEcran /></QueryClientProvider>)
    await waitFor(() => expect(container.querySelector('[data-etude-ecran]')).toBeTruthy())
    expect(container.textContent).toContain('Étude de faisabilité')
    // l'assiette (initialIdus) amorce la sélection locale → la puce de parcelle + le bouton Générer
    expect(container.querySelector('[data-etude-chip]')).toBeTruthy()
    expect(container.querySelector('[data-etude-generer]')).toBeTruthy()
  })

  it('« ← Fermer » referme l\'overlay', async () => {
    useApp.getState().ouvrirEtude(['97404000AW0099'])
    const { container, getByText } = renderEtude()
    await waitFor(() => expect(container.querySelector('[data-etude-ecran]')).toBeTruthy())
    fireEvent.click(getByText('← Fermer'))
    expect(useApp.getState().etudeIdus).toBeNull()
  })
})

// IMPLANTATION-4 (parcelles multiples) — dans Docs, la carte « Étude de faisabilité » ouvre DIRECTEMENT
// l'écran d'étude (état 1, assiette VIDE à composer), SANS la fenêtre « Sur quelle parcelle ? ».
describe('parcelles multiples — la carte Docs ouvre l\'état 1 (pas de picker)', () => {
  beforeEach(() => { useApp.setState({ etudeIdus: null }); global.fetch = vi.fn(async (u: string) =>
    ({ ok: true, json: async () => (String(u).includes('/documents') ? { documents: [], total: 0 } : {}) }) as never) as unknown as typeof fetch })
  afterEach(() => { vi.restoreAllMocks(); useApp.setState({ etudeIdus: null }) })

  it('clic sur la carte Étude → ouvrirEtude([]) et AUCUNE fenêtre « Sur quelle parcelle ? »', async () => {
    render(<QueryClientProvider client={qc()}><DocumentsView /></QueryClientProvider>)
    const carte = await waitFor(() => {
      const b = [...document.querySelectorAll('button')].find((x) => /Étude de faisabilité/.test(x.textContent ?? ''))
      if (!b) throw new Error('carte Étude introuvable')
      return b as HTMLElement
    })
    fireEvent.click(carte)
    expect(useApp.getState().etudeIdus).toEqual([])          // overlay demandé, assiette vide
    expect(screen.queryByText('Sur quelle parcelle ?')).toBeNull()   // pas de fenêtre de choix
  })
})
