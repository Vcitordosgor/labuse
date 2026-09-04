import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { ZONE_FAM_ORDER, ZONE_FAM_META } from '../../lib/status'

// RETOURS-11 C1 — garde de non-régression du ZONAGE PLU par parcelle (calibré).
// Le bug (SECTEUR-2, 07d16986) : « Zonage PLU par parcelle » coché SANS « Limites parcelles »
// n'affichait que les lettres — l'aplat (fill) disparaissait — et la légende était vide.
// cwd = frontend/ quand vitest tourne (voir vitest.config.ts)
const SRC = readFileSync(resolve(process.cwd(), 'src/components/map/MapView.tsx'), 'utf8')

describe('C1 — la couche zonage garde ses trois calques', () => {
  it('déclare le calque FILL des parcelles (porteur de l\'aplat par famille)', () => {
    expect(SRC).toContain("id: 'parcels-fill'")
    expect(SRC).toContain('ZONE_FAM_COLOR')          // l'aplat par famille est bien appliqué
    expect(SRC).toContain('ZONE_FAM_OPACITY')
  })
  it('déclare le calque LINE et le calque SYMBOL (lettres de zone)', () => {
    expect(SRC).toContain("id: 'parcels-line'")
    expect(SRC).toMatch(/id: 'parcels-zone-label'/)  // symbole = lettres U1f/Ncor…
    expect(SRC).toMatch(/id: 'ile-zone-label'/)
  })
  it('rend le fill visible dès que le zonage-par-parcelle est peint (pas seulement les limites)', () => {
    // le correctif : la visibilité de parcels-fill / ile-fill dépend de `zonageFill`.
    expect(SRC).toMatch(/parcels-fill'.*visibility.*layers\.parcelles \|\| zonageFill/)
    expect(SRC).toMatch(/ile-fill'.*visibility.*layers\.parcelles \|\| zonageFill/)
  })
})

describe('C1 — la légende a une entrée COULEUR par famille de zone', () => {
  it('chaque famille de ZONE_FAM_ORDER a une couleur et un libellé', () => {
    expect(ZONE_FAM_ORDER.length).toBeGreaterThanOrEqual(4)   // U / AU / A / N (+ autre)
    for (const f of ZONE_FAM_ORDER) {
      expect(ZONE_FAM_META[f]).toBeTruthy()
      expect(ZONE_FAM_META[f].color).toMatch(/^#[0-9A-Fa-f]{6}$/)
      expect(ZONE_FAM_META[f].label.length).toBeGreaterThan(0)
    }
  })
})
