// RETOURS-15 SOCLE — tests-gardes des comportements PARTAGÉS (S1, S2).
//   S1 : cliquer une suggestion recopie le LIBELLÉ COMPLET dans le champ (adresse, IDU, propriétaire).
//   S2 : dès qu'une parcelle est résolue par la barre, le bouton « Cliquez une parcelle sur la carte »
//        DISPARAÎT (pas grisé), et réapparaît si le champ est vidé ; plus aucun bouton « Utiliser… ».
import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, waitFor } from '@testing-library/react'
import { act } from 'react'
import { AddressAutocomplete } from './AddressAutocomplete'
import { ParcelInput } from './ParcelInput'
import { useApp } from '../store/useApp'

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

  // RETOURS-15 D5 — l'adresse BAN arrive SCINDÉE (label = numéro + voie ; sub = CP + commune). Le
  // champ doit afficher l'adresse ENTIÈRE, code postal et commune compris — jamais la seule voie.
  it('AddressAutocomplete : label + sub recollés → adresse entière avec code postal', async () => {
    mockSuggest([{ type: 'adresse', items: [{ label: '3 Chemin de la Citerne', sub: '97490 Saint-Denis', lon: 55.4, lat: -20.9, idu: '97411000AB0001' }] }])
    render(<AddressAutocomplete onSelect={() => {}} grammaires={['adresse', 'cadastre']} />)
    const input = document.querySelector<HTMLInputElement>('[data-suggest-input]')!
    fireEvent.change(input, { target: { value: '3 chemin' } })
    const opt = await waitFor(() => {
      const el = document.querySelector('[data-suggest-item="adresse"]')
      expect(el).toBeTruthy()
      return el as HTMLElement
    })
    fireEvent.mouseDown(opt)
    expect(input.value).toBe('3 Chemin de la Citerne, 97490 Saint-Denis')
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

describe('RETOURS-15 S2 — l’invite carte disparaît quand une parcelle est résolue', () => {
  afterEach(() => vi.restoreAllMocks())

  it('invite présente au repos, absente après résolution par la barre, de retour quand vidé', async () => {
    mockSuggest([])
    const picked: string[] = []
    render(<ParcelInput onPick={(idu) => picked.push(idu)} />)
    const input = document.querySelector<HTMLInputElement>('[data-suggest-input]')!
    // au repos (withCarte défaut = true) : l'invite « cliquez une parcelle » est là
    expect(document.querySelector('[data-parcelinput-carte]')).toBeTruthy()
    // on résout un IDU complet à la volée (Entrée sans suggestion active → onEnterRaw)
    fireEvent.change(input, { target: { value: '97411000BZ1065' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => expect(picked).toEqual(['97411000BZ1065']))
    // l'invite a DISPARU (pas grisée : absente du DOM)
    expect(document.querySelector('[data-parcelinput-carte]')).toBeFalsy()
    // on vide le champ → l'invite revient
    fireEvent.change(input, { target: { value: '' } })
    await waitFor(() => expect(document.querySelector('[data-parcelinput-carte]')).toBeTruthy())
  })

  it('plus aucun bouton « Utiliser la parcelle » n’est rendu', () => {
    mockSuggest([])
    const { container } = render(<ParcelInput onPick={() => {}} />)
    expect(container.textContent).not.toContain('Utiliser la parcelle')
  })

  // RETOURS-15 D2 — un outil qui consomme le clic carte lui-même (Pièges) passe withCarte={false}
  // inviteCarte : l'invite « ou cliquez une parcelle » se voit quand même (le second geste existe).
  it('inviteCarte réaffiche l’invite même avec withCarte={false}', () => {
    mockSuggest([])
    render(<ParcelInput onPick={() => {}} withCarte={false} inviteCarte />)
    expect(document.querySelector('[data-parcelinput-carte]')).toBeTruthy()
  })
})

describe('RETOURS-15 S4 — le clic carte agit directement (auto-consommation de selectedIdu)', () => {
  afterEach(() => vi.restoreAllMocks())

  it('une nouvelle sélection carte est remontée via onPick, sans bouton', async () => {
    mockSuggest([])
    act(() => useApp.setState({ selectedIdu: null }))
    const picked: string[] = []
    render(<ParcelInput onPick={(idu) => picked.push(idu)} />)
    // simulate un clic carte : le handler MapView pose selectedIdu (branche par défaut = select)
    act(() => useApp.setState({ selectedIdu: '97411000BZ1065' }))
    await waitFor(() => expect(picked).toEqual(['97411000BZ1065']))
    // …et l'invite carte a disparu (parcelle résolue)
    expect(document.querySelector('[data-parcelinput-carte]')).toBeFalsy()
    act(() => useApp.setState({ selectedIdu: null }))
  })

  it('withCarte=false (Comparer) : n’auto-consomme pas selectedIdu (clic géré par comparePicking)', async () => {
    mockSuggest([])
    act(() => useApp.setState({ selectedIdu: null }))
    const picked: string[] = []
    render(<ParcelInput onPick={(idu) => picked.push(idu)} withCarte={false} />)
    act(() => useApp.setState({ selectedIdu: '97411000BZ1065' }))
    // laisse les effets tourner
    await new Promise((r) => setTimeout(r, 20))
    expect(picked).toEqual([])
    act(() => useApp.setState({ selectedIdu: null }))
  })
})
