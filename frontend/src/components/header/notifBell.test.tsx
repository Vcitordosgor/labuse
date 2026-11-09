// RETOURS-19 (pt 2) — test du COMPTEUR « non vues » de la cloche :
//  · le badge compte les événements CLIENT arrivés depuis la dernière ouverture (vuMax) ;
//  · OUVRIR la cloche remet le badge à 0 (tout vu) ;
//  · CLIQUER une notification la marque LUE (POST /events/{id}/read) — son point disparaît.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { NotifBell } from './Header'

// trois événements CLIENT (kind de la liste blanche), ids 10/11/12, non lus.
const EVENTS = {
  unread: 3,
  items: [
    { id: 12, kind: 'parcelle_suivie', lu: false, titre: 'Changement sur BZ1065', idu: '97411000BZ1065', ts: '2026-11-09T10:00:00Z' },
    { id: 11, kind: 'radar', lu: false, titre: 'Nouvelle annonce', lien: 'https://x', ts: '2026-11-09T09:00:00Z' },
    { id: 10, kind: 'bodacc', lu: false, titre: 'Procédure BODACC', idu: '97411000BZ1066', ts: '2026-11-09T08:00:00Z' },
  ],
}

let readCalls: number[] = []
function mockFetch() {
  readCalls = []
  global.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const u = String(url)
    const json = async (v: unknown) => v
    const m = u.match(/\/events\/(\d+)\/read/)
    if (m && init?.method === 'POST') { readCalls.push(Number(m[1])); return { ok: true, json: () => json({ ok: true }) } }
    if (u.includes('/events?')) return { ok: true, json: () => json(EVENTS) }
    if (u.includes('/events/count')) return { ok: true, json: () => json({ unread: 3, par_parcelle: {} }) }
    return { ok: true, json: () => json({}) }
  }) as unknown as typeof fetch
}
function renderBell() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><NotifBell /></QueryClientProvider>)
}

describe('RETOURS-19 (pt 2) — compteur « non vues » de la cloche', () => {
  beforeEach(() => { mockFetch(); try { localStorage.clear() } catch { /* jsdom */ } })
  afterEach(() => { vi.restoreAllMocks() })

  it('le badge compte les non vues, puis OUVRIR la cloche le remet à 0', async () => {
    const { container, getByLabelText } = renderBell()
    // badge = 3 non vues (vuMax 0 au départ)
    await waitFor(() => expect(getByLabelText(/Notifications 3 non vues/)).toBeTruthy())
    // ouvrir la cloche → tout vu → plus de badge
    fireEvent.click(getByLabelText(/Notifications 3 non vues/))
    await waitFor(() => expect(container.querySelector('[aria-label="Notifications"]')).toBeTruthy())
    // le compteur persisté (vuMax) couvre bien le plus grand id vu
    expect(Number(localStorage.getItem('labuse:notif-vu-max'))).toBe(12)
  })

  it('CLIQUER une notification la marque LUE (POST /read)', async () => {
    const { getByLabelText, findByText } = renderBell()
    fireEvent.click(await waitFor(() => getByLabelText(/Notifications 3 non vues/)))   // ouvrir
    const ligne = await findByText('Changement sur BZ1065')
    fireEvent.click(ligne)
    await waitFor(() => expect(readCalls).toContain(12))
  })
})
