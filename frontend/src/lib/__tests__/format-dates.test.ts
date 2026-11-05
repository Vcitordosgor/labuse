// CHASSE-FIX-1 (A-3) — GARDE-FOU : toutes les dates et durées du front passent par UNE SEULE fonction
// de format (`src/lib/format.ts`), en fuseau Indian/Reunion. Ce test refuse, PARTOUT ailleurs dans
// `src/`, tout `toLocaleDateString`/`toLocaleTimeString`, tout `toLocaleString(...timeZone...)` (format
// de date/heure) et tout âge relatif interpolé (`il y a ${...}`) — c'était la grappe de bugs « J-1 »
// (lot A, classe SILENCE-1). Les nombres `n.toLocaleString('fr-FR')` (sans timeZone) restent permis.
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

import {
  ageConversation, ageEnJours, fmtDateCourt, fmtHorodatage, fmtMoisAn,
} from '../format'

const SRC = join(process.cwd(), 'src')                               // vitest tourne depuis frontend/
const CE_FICHIER = join(SRC, 'lib', '__tests__', 'format-dates.test.ts')
// La SEULE exception : le module de format lui-même (c'est lui qui porte les appels Intl).
const AUTORISE = join(SRC, 'lib', 'format.ts')

const INTERDITS: { re: RegExp; quoi: string }[] = [
  { re: /toLocaleDateString/, quoi: 'toLocaleDateString (→ fmtDate/fmtDateNum/fmtDateCourt/…)' },
  { re: /toLocaleTimeString/, quoi: 'toLocaleTimeString (→ fmtHorodatage)' },
  { re: /toLocaleString\([^)]*timeZone/, quoi: 'toLocaleString de date/heure (→ fmtHorodatage)' },
  { re: /il y a \$\{/, quoi: 'âge relatif interpolé (→ ilYA/ageConversation/ageMoisLabel/labelJours)' },
]

function fichiersSource(dir: string): string[] {
  const out: string[] = []
  for (const nom of readdirSync(dir)) {
    const p = `${dir}/${nom}`
    if (statSync(p).isDirectory()) { out.push(...fichiersSource(p)); continue }
    if (/\.tsx?$/.test(nom) && p !== CE_FICHIER && p !== AUTORISE) out.push(p)
  }
  return out
}

describe('A-3 — centralisation des dates/durées (fuseau Indian/Reunion)', () => {
  it('aucun toLocaleDateString / toLocaleString-de-date / âge relatif hors de lib/format.ts', () => {
    const coupables: string[] = []
    for (const f of fichiersSource(SRC)) {
      const src = readFileSync(f, 'utf8')
      for (const { re, quoi } of INTERDITS) {
        if (re.test(src)) coupables.push(`${f.replace(SRC, 'src')} — ${quoi}`)
      }
    }
    expect(coupables, `Dates/durées à router par lib/format.ts :\n${coupables.join('\n')}`).toEqual([])
  })

  it('les formateurs rendent en heure de La Réunion (UTC+4), pas J-1', () => {
    // 2026-07-12 22:00 UTC = 2026-07-13 02:00 à La Réunion → le jour bascule au 13.
    expect(fmtDateCourt('2026-07-12T22:00:00Z')).toBe('13/07')
    // une date-seule (minuit UTC) reste le même jour à La Réunion (+4) : 12/07, jamais 11/07.
    expect(fmtDateCourt('2026-07-12')).toBe('12/07')
    expect(fmtMoisAn('2026-07-12')).toBe('juillet 2026')
    expect(fmtHorodatage('2026-07-12T22:00:00Z')).toMatch(/^13\/07 02:00$/)
    expect(fmtDateCourt(null)).toBe('—')
  })

  it("ageConversation / ageEnJours comptent en jours calendaires (Réunion)", () => {
    const now = new Date().toISOString()
    expect(ageConversation(now)).toBe("aujourd'hui")
    expect(ageEnJours(now)).toBe(0)
    expect(ageConversation(null)).toBe('')
    expect(ageEnJours(null)).toBeNull()
  })
})
