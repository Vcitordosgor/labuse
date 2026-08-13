// M26-B — les états 2 à 5 de la maquette B4, pipeline réel (vue + hook + réducteur) :
//  · état 2 : fil vivant, entonnoir partiel, AUCUN résultat partiel (règle 5), annulation ;
//  · état 3 : question + options + champ libre, le run REPREND (after_seq), sans redémarrage ;
//  · état 4 : zéro = done (règle 6), entonnoir complet, relances NON chiffrées ;
//  · état 5 : 429 avant création — aucun run, aucun flux ouvert ;
//  · rafraîchissement en plein run : le fil revient à l'identique (run épinglé + rejeu).
import { act, fireEvent, render, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CopiloteEvent } from '../../../lib/copilote'
import { CopiloteView } from '../CopiloteView'
import { etat1Calibre, etat2EnCours, etat3Clarification, etat4Zero } from './fixtures'

class FauxEventSource {
  static instances: FauxEventSource[] = []
  url: string
  ferme = false
  private ecouteurs = new Map<string, Array<(e: MessageEvent) => void>>()
  onerror: ((e?: unknown) => void) | null = null
  constructor(url: string) {
    this.url = url
    FauxEventSource.instances.push(this)
  }
  addEventListener(kind: string, fn: (e: MessageEvent) => void) {
    this.ecouteurs.set(kind, [...(this.ecouteurs.get(kind) ?? []), fn])
  }
  close() { this.ferme = true }
  emet(e: CopiloteEvent) {
    for (const fn of this.ecouteurs.get(e.kind) ?? [])
      fn(new MessageEvent(e.kind, { data: JSON.stringify(e) }))
  }
  fin(status: string) {
    for (const fn of this.ecouteurs.get('fin') ?? [])
      fn(new MessageEvent('fin', { data: JSON.stringify({ status }) }))
  }
}

const normalise = (s: string | null) => (s ?? '').replace(/[\u202f\u00a0\u2009]/g, ' ')
let fetchMock: ReturnType<typeof vi.fn>

async function lancerRun() {
  const rendu = render(<CopiloteView />)
  fireEvent.change(document.querySelector('[data-brief]')!, { target: { value: 'brief de test' } })
  // M78 · 2a — la barre d'accueil dispatche par le routeur (mocké → RECHERCHE) puis lance le run.
  fireEvent.click(document.querySelector('[data-accueil-envoyer]')!)
  await waitFor(() => expect(FauxEventSource.instances.length).toBeGreaterThan(0))
  return { es: FauxEventSource.instances[0], rendu }
}

// routeur v2 mocké : /ask → RECHERCHE (mission lourde) ; le reste → run_id.
const reponse = (url: unknown) => String(url).includes('/copilote-v2/ask')
  ? { intent: 'RECHERCHE' } : { run_id: 'run-test' }

beforeEach(() => {
  localStorage.clear()
  FauxEventSource.instances = []
  vi.stubGlobal('EventSource', FauxEventSource as unknown as typeof EventSource)
  fetchMock = vi.fn(async (url: unknown) => ({ ok: true, json: async () => reponse(url) }))
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

describe('état 2 — instruction en cours', () => {
  it('fil vivant + entonnoir partiel, AUCUN résultat partiel (règle 5)', async () => {
    const { es } = await lancerRun()
    act(() => { for (const e of etat2EnCours()) es.emet(e) })
    // fil : étape active qui pulse, suivantes en attente, interprétation faite
    expect(document.querySelector('[data-fil-etape="faisabilite"][data-etat="active"]')).toBeInTheDocument()
    expect(document.querySelector('[data-fil-etape="marche_dvf"][data-etat="attente"]')).toBeInTheDocument()
    expect(document.querySelector('[data-fil-etape="interpretation"][data-etat="faite"]')).toBeInTheDocument()
    // entonnoir : étages atteints remplis, étages à venir en attente (—), jamais inventés
    const pool = document.querySelector('[data-etage="pool"]')!
    expect(pool).toHaveAttribute('data-etage-atteint', '1')
    expect(normalise(pool.textContent)).toContain('13 155')
    expect(document.querySelector('[data-etage="restituees"]')).not.toHaveAttribute('data-etage-atteint')
    expect(normalise(document.querySelector('[data-etage="restituees"]')!.textContent)).toContain('—')
    // calibrage déjà connu (payload du filtre géométrique) ; exhaustivité pas encore affichable
    expect(document.querySelector('[data-badge="calibrage"]')).toBeInTheDocument()
    expect(document.querySelector('[data-badge="exhaustivite"]')).toBeNull()
    // règle 5 : rien d'assemblé à l'écran
    expect(document.querySelector('[data-resultats]')).toBeNull()
    expect(document.querySelector('[data-restituee]')).toBeNull()
    expect(document.querySelector('[data-en-cours]')).toBeInTheDocument()
  })

  it('annulation active pendant l’instruction → POST /cancel', async () => {
    const { es } = await lancerRun()
    act(() => { for (const e of etat2EnCours()) es.emet(e) })
    fireEvent.click(document.querySelector('[data-annuler]')!)
    await waitFor(() => expect(fetchMock.mock.calls.some(
      (c) => String(c[0]).includes('/cancel'))).toBe(true))
  })

  it('rafraîchissement en plein run : le même fil revient, sans doublon ni trou', async () => {
    const { es, rendu } = await lancerRun()
    act(() => { for (const e of etat2EnCours()) es.emet(e) })
    rendu.unmount()
    // remontage (= refresh) : le run épinglé est rechargé depuis seq 0, le back rejoue
    render(<CopiloteView />)
    await waitFor(() => expect(FauxEventSource.instances.length).toBe(2))
    const es1 = FauxEventSource.instances[1]
    expect(es1.url).toContain('after_seq=0')
    act(() => { for (const e of etat2EnCours()) es1.emet(e) })
    expect(document.querySelectorAll('[data-fil]')).toHaveLength(1)
    expect(document.querySelectorAll('[data-fil-etape="criblage"]')).toHaveLength(1)
    expect(document.querySelector('[data-fil-etape="faisabilite"][data-etat="active"]')).toBeInTheDocument()
    expect(normalise(document.querySelector('[data-etage="pool"]')!.textContent)).toContain('13 155')
    expect(document.querySelector('[data-restituee]')).toBeNull()
  })
})

describe('état 3 — demande de précision', () => {
  async function enPause() {
    const { es } = await lancerRun()
    act(() => { for (const e of etat3Clarification()) es.emet(e); es.fin('awaiting_user') })
    await waitFor(() => expect(document.querySelector('[data-clarification]')).toBeInTheDocument())
    return es
  }

  it('question + options + champ libre, fil en pause', async () => {
    await enPause()
    expect(normalise(document.querySelector('[data-clarification]')!.textContent))
      .toContain('Sur quelle commune dois-je instruire ce dossier ?')
    expect(document.querySelectorAll('[data-clarif-option]')).toHaveLength(4)
    expect(document.querySelector('[data-clarif-libre]')).toBeInTheDocument()
    expect(document.querySelector('[data-fil-etape="interpretation"][data-etat="pause"]')).toBeInTheDocument()
    expect(document.querySelector('[data-fil-etape="criblage"][data-etat="attente"]')).toBeInTheDocument()
    // console suspendue : pas de bouton Instruire pendant la pause
    expect(document.querySelector('[data-instruire]')).toBeNull()
    expect(document.querySelector('[data-en-attente]')).toBeDisabled()
  })

  it('répondre → POST /answer, le run REPREND au même after_seq (jamais redémarré)', async () => {
    await enPause()
    fireEvent.click(document.querySelectorAll('[data-clarif-option]')[0])
    await waitFor(() => expect(fetchMock.mock.calls.some(
      (c) => String(c[0]).includes('/answer'))).toBe(true))
    const appelAnswer = fetchMock.mock.calls.find((c) => String(c[0]).includes('/answer'))!
    expect(String(appelAnswer[1]?.body)).toContain('Saint-Paul')
    // le flux est rouvert sur LE MÊME run, à la suite du fil — pas un nouveau run
    await waitFor(() => expect(FauxEventSource.instances.length).toBe(2))
    expect(FauxEventSource.instances[1].url).toContain('/runs/run-test/')
    expect(FauxEventSource.instances[1].url).toContain('after_seq=2')
    expect(fetchMock.mock.calls.filter(
      (c) => String(c[0]).endsWith('/api/copilote/runs') ).length).toBe(1)
    // la suite du fil arrive : l'interprétation redevient active puis le criblage démarre
    const es1 = FauxEventSource.instances[1]
    act(() => {
      es1.emet({ seq: 3, kind: 'clarification_answered', payload: { reponse: 'Saint-Paul' },
                 created_at: '2026-07-27T12:00:00Z' })
    })
    expect(document.querySelector('[data-clarification]')).toBeNull()
    expect(document.querySelector('[data-fil-etape="interpretation"][data-etat="active"]')).toBeInTheDocument()
  })
})

describe('état 4 — zéro retenue (jamais une erreur)', () => {
  async function zeroRendu() {
    const { es } = await lancerRun()
    act(() => { for (const e of etat4Zero()) es.emet(e); es.fin('done') })
    await waitFor(() => expect(document.querySelector('[data-zero]')).toBeInTheDocument())
  }

  it('entonnoir COMPLET visible (0 compris), message honnête, aucun ton d’erreur', async () => {
    await zeroRendu()
    expect(document.querySelectorAll('[data-etage]')).toHaveLength(6)
    expect(document.querySelectorAll('[data-etage][data-etage-atteint]')).toHaveLength(6)
    expect(normalise(document.querySelector('[data-etage="dans_budget"]')!.textContent)).toContain('0')
    expect(document.querySelector('[data-echec]')).toBeNull()
    expect(normalise(document.querySelector('[data-zero]')!.textContent)).toContain('Aucun critère n’a été assoupli')
    expect(document.querySelector('[data-livrable]')).toBeInTheDocument()
  })

  it('relances proposées SANS chiffre, pré-remplissant la console avec le brief d’origine', async () => {
    await zeroRendu()
    const relances = [...document.querySelectorAll('[data-relance]')]
    expect(relances).toHaveLength(2)
    for (const r of relances) expect(r.textContent).not.toMatch(/\d/)
    fireEvent.click(relances[0])
    expect((document.querySelector('[data-brief]') as HTMLTextAreaElement).value)
      .toBe('Terrain pour 25 logements à Cilaos, budget foncier 200 k€, hors PPR')
  })
})

describe('état 5 — quota atteint (429 avant création)', () => {
  it('aucun run créé, aucun flux ouvert, message honnête du 429 verbatim', async () => {
    // le routeur /ask réussit (RECHERCHE) ; la création de run /runs bute sur le 429.
    fetchMock.mockImplementation(async (url: unknown) => String(url).includes('/copilote-v2/ask')
      ? { ok: true, json: async () => ({ intent: 'RECHERCHE' }) }
      : { ok: false, status: 429,
          json: async () => ({ detail: 'Quota Copilote atteint (10 runs/jour). Reprend à minuit.',
                               quota: 10, gel_jusqua: 'minuit' }) })
    render(<CopiloteView />)
    fireEvent.change(document.querySelector('[data-brief]')!, { target: { value: 'brief de test' } })
    fireEvent.click(document.querySelector('[data-accueil-envoyer]')!)
    await waitFor(() => expect(document.querySelector('[data-quota-panel]')).toBeInTheDocument())
    expect(FauxEventSource.instances).toHaveLength(0)             // aucun moteur appelé
    const panel = normalise(document.querySelector('[data-quota-panel]')!.textContent)
    expect(panel).toContain('Vos 10 instructions du jour sont utilisées.')
    expect(panel).toContain('Reprend à minuit.')                  // le corps du 429, verbatim
    expect(document.querySelector('[data-en-cours]')).toBeNull()
    // v2 : aucun run créé → retour à l'accueil (plus de bouton Instruire actif)
    expect(document.querySelector('[data-accueil]')).toBeInTheDocument()
  })
})

describe('replay complet après refresh sur run terminé', () => {
  it('l’état 1 revient identique depuis le run épinglé', async () => {
    const { es, rendu } = await lancerRun()
    act(() => { for (const e of etat1Calibre()) es.emet(e); es.fin('done') })
    await waitFor(() => expect(document.querySelector('[data-resultats]')).toBeInTheDocument())
    rendu.unmount()
    render(<CopiloteView />)
    await waitFor(() => expect(FauxEventSource.instances.length).toBe(2))
    const es1 = FauxEventSource.instances[1]
    act(() => { for (const e of etat1Calibre()) es1.emet(e); es1.fin('done') })
    await waitFor(() => expect(document.querySelectorAll('[data-restituee]')).toHaveLength(20))
    expect(document.querySelectorAll('[data-entonnoir]')).toHaveLength(1)
  })
})
