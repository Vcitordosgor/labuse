import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { Plu } from './Plu'

// OUTIL-COMMUNES-FIX-14 LOT 1 — le bouton « Vérif procédure » de la fiche (Fiche.tsx) pose
// pluVue='procedure' puis setModule('plu'). OR setModule EFFACE selectedIdu (useApp.ts:1061) : la
// parcelle était perdue et l'outil redemandait une saisie (constat ASTRA-11 n°1, 8/8). La parcelle
// doit VOYAGER par un prefill (qui survit au changement d'outil) et amorcer la vérification sans
// ressaisie. Aux Trois-Bassins : débat PADD du 04/09/2025 servi d'emblée.

vi.mock('../../lib/api', () => ({
  verifProcedure: vi.fn(async (idu: string) => ({
    idu, commune: 'Trois-Bassins', insee: idu.slice(0, 5), tier_servi: null,
    consulte_le: '2026-11-26', procedure_en_cours: true, synthese: 'Révision générale en cours',
    source: 'registre', source_citation: 'Ville des Trois-Bassins — révision générale',
    confiance: 'SOURCE', date_constat: '2026-11-25',
    consequences: { sursis: null, veille_au: null, debat_padd_tenu: '2025-09-04' },
  })),
  pluAnnuaireCommunes: vi.fn(async () => []),
  pluAnnuaireSearch: vi.fn(async () => ({ extraits: [] })),
  pluAnnuairePack: vi.fn(async () => ({})),
}))

const qc = () => new QueryClient({ defaultOptions: { queries: { retry: false } } })
const renderPlu = () => render(<QueryClientProvider client={qc()}><Plu /></QueryClientProvider>)

afterEach(() => { useApp.setState({ pluVue: null, selectedIdu: null, pluPrefill: null }) })

describe('LOT 1 — « Vérif procédure » garde la parcelle après le changement d\'outil', () => {
  it('selectedIdu effacé par setModule → la parcelle survit par le prefill et amorce la vérification', async () => {
    // état POST-setModule : selectedIdu est null (effacé), l'IDU voyage dans le prefill PLU.
    useApp.setState({ pluVue: 'procedure', selectedIdu: null,
      pluPrefill: { insee: '97423', zone: null, idu: '97423000AB0005' } })
    const { container } = renderPlu()
    await waitFor(() => {
      expect(container.querySelector('[data-verif-result]')).not.toBeNull()
    })
    const api = await import('../../lib/api')
    expect(api.verifProcedure).toHaveBeenCalledWith('97423000AB0005')
    // la date du débat PADD est servie d'emblée, sans ressaisie
    expect(container.textContent).toContain('04/09/2025')
  })
})
