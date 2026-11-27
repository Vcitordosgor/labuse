import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { Plu } from './Plu'

// OUTIL-COMMUNES-FIX-13 LOT 3 — le bouton « Vérif procédure » de la fiche (Fiche.tsx:1927) pose
// pluVue='procedure' + module='plu'. AVANT le fix, Plu.tsx IGNORAIT pluVue (setPluVue(null)) et
// montrait TOUJOURS l'Annuaire (data-plu-annuaire) : l'audit ASTRA-10 n°3 arrivait sur « PLU — Le
// règlement d'urbanisme de chaque commune ». APRÈS, Plu rend l'outil de VÉRIFICATION (radar sourcé),
// amorcé sur la commune de la parcelle (selectedIdu).

// On neutralise les appels réseau des deux sous-écrans (le test porte sur l'AIGUILLAGE, pas le contenu).
vi.mock('../../lib/api', () => ({
  verifProcedure: vi.fn(async () => ({
    idu: '97423000AB0005', commune: 'Trois-Bassins', insee: '97423', tier_servi: null,
    consulte_le: '2026-11-25', procedure_en_cours: true, synthese: 'Révision générale en cours',
    source: 'registre', confiance: 'SOURCE', date_constat: '2026-11-25',
    consequences: { sursis: null, veille_au: null, debat_padd_tenu: '2025-09-04' },
  })),
  pluAnnuaireCommunes: vi.fn(async () => []),
  pluAnnuaireSearch: vi.fn(async () => ({ extraits: [] })),
  pluAnnuairePack: vi.fn(async () => ({})),
}))

const qc = () => new QueryClient({ defaultOptions: { queries: { retry: false } } })
const renderPlu = () => render(<QueryClientProvider client={qc()}><Plu /></QueryClientProvider>)

afterEach(() => { useApp.setState({ pluVue: null, selectedIdu: null }) })

describe('LOT 3 — « Vérif procédure » ouvre l\'outil de vérification, pas l\'Annuaire', () => {
  it('pluVue=procedure (deep-link du bouton) → rend VerifProcedure sur la commune de la parcelle', async () => {
    useApp.setState({ pluVue: 'procedure', selectedIdu: '97423000AB0005' })
    const { container } = renderPlu()
    await waitFor(() => {
      expect(container.querySelector('[data-verif-procedure]')).not.toBeNull()
    })
    // ce n'est PAS l'annuaire des PLU
    expect(container.querySelector('[data-plu-annuaire]')).toBeNull()
    const api = await import('../../lib/api')
    expect(api.verifProcedure).toHaveBeenCalledWith('97423000AB0005')
  })

  it('pluVue absent (ouverture par le menu) → rend l\'Annuaire, pas la vérification', async () => {
    useApp.setState({ pluVue: null, selectedIdu: null })
    const { container } = renderPlu()
    await waitFor(() => {
      expect(container.querySelector('[data-plu-annuaire]')).not.toBeNull()
    })
    expect(container.querySelector('[data-verif-procedure]')).toBeNull()
  })
})
