// M26-B — verrous DOM de l'état 1, exigés par le mandat (§4) :
//  · aucun résultat partiel pendant l'instruction (règle 5) ;
//  · « N autres retenues » TOUJOURS visible quand retenues > restituées (règle 4) ;
//  · commune non calibrée → AUCUNE occurrence de « tracée par article » (règle 2) ;
//  · exhaustif: false → requalification présente et visible, jamais repliée (règle 3) ;
//  · reconnexion SSE after_seq sans doublon ni trou (via le vrai hook).
// Le pipeline testé est le RÉEL : CopiloteView + useCopiloteRun + réducteur, flux
// alimenté par un EventSource simulé qui rejoue les fixtures figées.
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CopiloteEvent } from '../../../lib/copilote'
import { CopiloteView } from '../CopiloteView'
import { etat1Calibre, etat1GeneriqueGardeFou } from './fixtures'

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

const normalise = (s: string | null) => (s ?? '').replace(/[  ]/g, ' ')

async function lancerRun(): Promise<FauxEventSource> {
  render(<CopiloteView />)
  fireEvent.change(document.querySelector('[data-brief]')!, { target: { value: 'brief de test' } })
  fireEvent.click(document.querySelector('[data-instruire]')!)
  await waitFor(() => expect(FauxEventSource.instances.length).toBeGreaterThan(0))
  return FauxEventSource.instances[0]
}

beforeEach(() => {
  FauxEventSource.instances = []
  vi.stubGlobal('EventSource', FauxEventSource as unknown as typeof EventSource)
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => ({ run_id: 'run-test' }) })))
})
afterEach(() => vi.unstubAllGlobals())

describe('état 1 — instruction terminée (fixture calibrée)', () => {
  it('règle 5 : AUCUN résultat partiel pendant l’instruction, tout à la fin', async () => {
    const evts = etat1Calibre()
    const es = await lancerRun()
    // toutes les étapes moteurs, mais ni assemblage ni run_completed
    act(() => { for (const e of evts.slice(0, evts.length - 2)) es.emet(e) })
    expect(document.querySelector('[data-resultats]')).toBeNull()
    expect(document.querySelector('[data-entonnoir]')).toBeNull()
    expect(document.querySelector('[data-restituee]')).toBeNull()
    expect(document.querySelector('[data-en-cours]')).toBeInTheDocument()
    // fin du run : l'état 1 complet apparaît
    act(() => { for (const e of evts.slice(evts.length - 2)) es.emet(e); es.fin('done') })
    await waitFor(() => expect(document.querySelector('[data-resultats]')).toBeInTheDocument())
    expect(document.querySelector('[data-entonnoir]')).toBeInTheDocument()
  })

  it('entonnoir : 6 étages, chiffres et étiquettes du payload, badges calibré + exhaustif', async () => {
    const evts = etat1Calibre()
    const es = await lancerRun()
    act(() => { for (const e of evts) es.emet(e); es.fin('done') })
    await waitFor(() => expect(document.querySelector('[data-entonnoir]')).toBeInTheDocument())
    expect(document.querySelectorAll('[data-etage]')).toHaveLength(6)
    const texte = normalise(document.querySelector('[data-entonnoir]')!.textContent)
    expect(texte).toContain('13 155')
    expect(texte).toContain('sourcé/estimé selon calibrage')   // étiquette d'étage, verbatim
    expect(screen.getByText('Examen exhaustif')).toBeInTheDocument()
    expect(screen.getByText('PLU calibré — tracé par article')).toBeInTheDocument()
  })

  it('règle 4 : « N autres retenues » toujours visible (2 753 retenues, 20 restituées)', async () => {
    const evts = etat1Calibre()
    const es = await lancerRun()
    act(() => { for (const e of evts) es.emet(e); es.fin('done') })
    await waitFor(() => expect(document.querySelector('[data-autres-retenues]')).toBeInTheDocument())
    const note = normalise(document.querySelector('[data-autres-retenues]')!.textContent)
    expect(note).toContain('2 733 autres retenues')
    expect(note).toContain('non restituées')
    expect(document.querySelector('[data-autres-retenues]')).toBeVisible()
  })

  it('20 restituées rendues, indicateur de charge supportable en information (règle 7)', async () => {
    const evts = etat1Calibre()
    const es = await lancerRun()
    act(() => { for (const e of evts) es.emet(e); es.fin('done') })
    await waitFor(() => expect(document.querySelectorAll('[data-restituee]')).toHaveLength(20))
    // 3 parcelles au-dessus de la charge supportable : flag affiché, parcelles RESTITUÉES
    expect(document.querySelectorAll('[data-charge-flag]')).toHaveLength(3)
    const lead = normalise(document.querySelector('[data-charge-flag]')!.textContent)
    expect(lead).toContain('charge supportable')
    expect(lead).toContain('385 k€')
  })

  it('fil : 8 étapes du plan figé, chaque étape faite porte son étiquette', async () => {
    const evts = etat1Calibre()
    const es = await lancerRun()
    act(() => { for (const e of evts) es.emet(e); es.fin('done') })
    await waitFor(() => expect(document.querySelectorAll('[data-fil-etape]')).toHaveLength(8))
    expect(document.querySelectorAll('[data-fil-etape] [data-etiquette]').length).toBe(8)
    const faisa = document.querySelector('[data-fil-etape="faisabilite"]')!
    expect(normalise(faisa.textContent)).toContain('SDP tracée par article (PLU calibré)')
  })

  it('livrable : journal consultable, PDF désactivé « bientôt » (M26-C)', async () => {
    const evts = etat1Calibre()
    const es = await lancerRun()
    act(() => { for (const e of evts) es.emet(e); es.fin('done') })
    await waitFor(() => expect(document.querySelector('[data-livrable]')).toBeInTheDocument())
    expect(document.querySelector('[data-pdf-bientot]')).toBeDisabled()
    fireEvent.click(document.querySelector('[data-journal-ouvrir]')!)
    expect(document.querySelector('[data-journal]')).toBeInTheDocument()
    expect(normalise(document.querySelector('[data-journal]')!.textContent)).toContain('run_completed')
  })

  it('reconnexion SSE after_seq : coupure + rejeu chevauchant → ni doublon ni trou', async () => {
    const evts = etat1Calibre()
    const es0 = await lancerRun()
    expect(es0.url).toContain('after_seq=0')
    act(() => { for (const e of evts.slice(0, 8)) es0.emet(e) })
    // filet serveur 180 s : le flux expire, le hook rouvre AU DERNIER SEQ REÇU
    act(() => es0.fin('flux_expire'))
    await waitFor(() => expect(FauxEventSource.instances.length).toBe(2))
    const es1 = FauxEventSource.instances[1]
    expect(es1.url).toContain(`after_seq=${evts[7].seq}`)
    // rejeu LARGE (chevauchement volontaire du déjà-vu) puis fin du run
    act(() => { for (const e of evts.slice(4)) es1.emet(e); es1.fin('done') })
    await waitFor(() => expect(document.querySelectorAll('[data-restituee]')).toHaveLength(20))
    expect(document.querySelectorAll('[data-fil-etape]')).toHaveLength(8)   // pas de doublon
    expect(document.querySelectorAll('[data-entonnoir]')).toHaveLength(1)
  })
})

describe('verrous — commune non calibrée + garde-fou (fixture générique)', () => {
  async function rendreGenerique() {
    const evts = etat1GeneriqueGardeFou()
    const es = await lancerRun()
    act(() => { for (const e of evts) es.emet(e); es.fin('done') })
    await waitFor(() => expect(document.querySelector('[data-entonnoir]')).toBeInTheDocument())
  }

  it('règle 2 : AUCUNE occurrence de « tracé(e) par article » dans le rendu', async () => {
    await rendreGenerique()
    const corps = normalise(document.body.textContent)
    expect(corps).not.toMatch(/tracée? par article/i)
    expect(screen.getByText('Règle générique — PLU non calibré')).toBeInTheDocument()
  })

  it('règle 3 : la requalification est présente, intégrale et VISIBLE (jamais repliée)', async () => {
    await rendreGenerique()
    const requalif = document.querySelector('[data-requalification]')
    expect(requalif).toBeInTheDocument()
    expect(requalif).toBeVisible()
    expect(requalif!.closest('details')).toBeNull()
    expect(normalise(requalif!.textContent)).toContain('Résultat NON exhaustif')
    expect(normalise(requalif!.textContent)).toContain('5 000 examinées sur 6 100 candidates')
    expect(screen.getByText('Examen partiel')).toBeInTheDocument()
  })

  it('la mention SDP générique du payload est affichée telle quelle dans le fil', async () => {
    await rendreGenerique()
    const faisa = document.querySelector('[data-fil-etape="faisabilite"]')!
    expect(normalise(faisa.textContent)).toContain('SDP estimée — règle générique, PLU non calibré')
  })
})
