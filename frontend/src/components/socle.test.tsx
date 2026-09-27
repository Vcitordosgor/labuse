// RETOURS-15 SOCLE — tests-gardes des comportements PARTAGÉS (S1, S2).
//   S1 : cliquer une suggestion recopie le LIBELLÉ COMPLET dans le champ (adresse, IDU, propriétaire).
//   S2 : dès qu'une parcelle est résolue par la barre, le bouton « Cliquez une parcelle sur la carte »
//        DISPARAÎT (pas grisé), et réapparaît si le champ est vidé ; plus aucun bouton « Utiliser… ».
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, waitFor } from '@testing-library/react'
import { AddressAutocomplete } from './AddressAutocomplete'
import { ParcelInput } from './ParcelInput'

// Suggest mock paramétrable : on renvoie un groupe unique du type demandé, libellé complet.
function mockSuggest(groupes: unknown) {
  global.fetch = vi.fn(async (url: string) => {
    const u = String(url)
    const json = async (v: unknown) => v
    if (u.includes('/api/recherche/suggest')) {
      return { ok: true, json: () => json({ q: '', total: 1, ms: 1, formats: '', groupes }) }
    }
    return { ok: true, json: () => json({}) }
  }) as unknown as typeof fetch
}

const LABEL_ADRESSE = '3 Chemin de la Citerne, 97417 Saint-Denis'

describe('RETOURS-15 S1 — la suggestion cliquée remplit le champ de son libellé complet', () => {
  afterEach(() => vi.restoreAllMocks())

  it('AddressAutocomplete : un clic adresse recopie le libellé complet', async () => {
    mockSuggest([{ type: 'adresse', items: [{ label: LABEL_ADRESSE, lon: 55.4, lat: -20.9, idu: '97411000AB0001' }] }])
    render(<AddressAutocomplete onSelect={() => {}} grammaires={['adresse', 'cadastre']} />)
    const input = document.querySelector<HTMLInputElement>('[data-suggest-input]')!
    fireEvent.change(input, { target: { value: '3 chemin' } })
    const opt = await waitFor(() => {
      const el = document.querySelector('[data-suggest-item="adresse"]')
      expect(el).toBeTruthy()
      return el as HTMLElement
    })
    fireEvent.mouseDown(opt)
    expect(input.value).toBe(LABEL_ADRESSE)
  })

  it('ParcelInput : un clic IDU (cadastre) recopie le libellé complet', async () => {
    mockSuggest([{ type: 'cadastre', items: [{ label: '97411000BZ1065', sub: 'Saint-Denis', idu: '97411000BZ1065' }] }])
    render(<ParcelInput onPick={() => {}} withCarte={false} />)
    const input = document.querySelector<HTMLInputElement>('[data-suggest-input]')!
    fireEvent.change(input, { target: { value: 'BZ1065' } })
    const opt = await waitFor(() => {
      const el = document.querySelector('[data-suggest-item="cadastre"]')
      expect(el).toBeTruthy()
      return el as HTMLElement
    })
    fireEvent.mouseDown(opt)
    expect(input.value).toBe('97411000BZ1065')
  })
})
