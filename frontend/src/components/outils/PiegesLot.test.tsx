import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { M10 } from './ModulePanel'

// PIEGES-RISQUES-2 (Lot A) — « Un lot » = UNION des contraintes lues par la MÊME source que « Une
// parcelle » (couches en direct), chaque contrainte portant « N parcelles sur M ». Plus de score de
// risque ni de checklist cascade. La réponse N'A PLUS de champ `items`/`risque`/`checklist`/`seuils`.
const DILIGENCE = {
  n_demandes: 2, n_trouvees: 2, n_parcelles: 2, erreurs: [], non_couvert: ['Procédures PLU en cours — voir l\'outil PLU'],
  parcelles: [
    { idu: '97411000BZ1065', commune: 'Saint-Denis', surface_m2: 1625, n_contraintes: 2 },
    { idu: '97415000CT1837', commune: 'Saint-Paul', surface_m2: 900, n_contraintes: 1 },
  ],
  contraintes: [
    { categorie: 'Assainissement non collectif (ANC)', effet: 'Dispositif individuel à prévoir (coût à anticiper au budget)',
      source: 'GPU — zonages d\'assainissement', date: '2026-08-21', n_parcelles: 2, parcelles: ['97411000BZ1065', '97415000CT1837'] },
    { categorie: 'Droit de préemption (DPU)', effet: 'Droit de préemption urbain — la commune peut se substituer à l\'acquéreur à la vente',
      source: 'GPU — droit de préemption urbain', date: '2026-09-07', n_parcelles: 1, parcelles: ['97411000BZ1065'] },
  ],
}

function mockFetch() {
  global.fetch = vi.fn(async (url: string) => {
    if (String(url).includes('/duediligence')) return { ok: true, json: async () => DILIGENCE }
    return { ok: true, json: async () => ({}) }
  }) as unknown as typeof fetch
}
function renderM10() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><M10 /></QueryClientProvider>)
}
// construit le lot via le collage (fiable en jsdom), puis analyse.
function batirEtAnalyser() {
  const paste = document.querySelector('[data-diligence-paste]') as HTMLTextAreaElement
  fireEvent.change(paste, { target: { value: '97411000BZ1065\n97415000CT1837' } })
  fireEvent.click(document.querySelector('[data-diligence-add]')!)
  fireEvent.click(document.querySelector('[data-diligence-analyser]')!)
}

describe('PIEGES — « Un lot »', () => {
  beforeEach(() => { mockFetch(); useApp.setState({ courrierPrefillIdus: null, module: 'risques' }) })
  afterEach(() => { vi.restoreAllMocks(); useApp.setState({ courrierPrefillIdus: null, module: null }) })

  it('la barre/collage construit un lot de chips', async () => {
    renderM10()
    const paste = document.querySelector('[data-diligence-paste]') as HTMLTextAreaElement
    fireEvent.change(paste, { target: { value: '97411000BZ1065\n97415000CT1837' } })
    fireEvent.click(document.querySelector('[data-diligence-add]')!)
    expect(document.querySelectorAll('[data-diligence-chip]')).toHaveLength(2)
  })

  it('rend l\'UNION par contrainte avec « N parcelles sur M » (même carte que « Une parcelle »)', async () => {
    renderM10()
    batirEtAnalyser()
    await waitFor(() => expect(document.querySelectorAll('[data-diligence-contrainte]').length).toBe(2))
    // libellés = ceux du mode parcelle
    expect(screen.getByText('Assainissement non collectif (ANC)')).toBeTruthy()
    expect(screen.getByText('Droit de préemption (DPU)')).toBeTruthy()
    // décompte de parcelles touchées par contrainte
    const parts = Array.from(document.querySelectorAll('[data-diligence-part]')).map((e) => e.textContent?.replace(/\s+/g, ' ').trim())
    expect(parts).toContain('2 parcelles sur 2')   // ANC : les 2
    expect(parts).toContain('1 parcelle sur 2')    // DPU : une seule
    // plus AUCUN vestige de l'ancien crible cascade (score de risque, checklist, PDF)
    expect(document.querySelector('[data-diligence-risque]')).toBeNull()
    expect(document.querySelector('[data-diligence-seuils]')).toBeNull()
    expect(screen.queryByText(/⬇ PDF/)).toBeNull()
  })

  it('pont Courrier : « Préparer les courriers » pose courrierPrefillIdus + ouvre l\'outil', async () => {
    renderM10()
    batirEtAnalyser()
    const btn = await waitFor(() => { const b = document.querySelector('[data-diligence-courrier]'); if (!b) throw new Error('no btn'); return b as HTMLElement })
    expect(btn.textContent).toContain('(2)')
    fireEvent.click(btn)
    expect(useApp.getState().courrierPrefillIdus).toEqual(['97411000BZ1065', '97415000CT1837'])
    expect(useApp.getState().module).toBe('courriers')
  })
})
