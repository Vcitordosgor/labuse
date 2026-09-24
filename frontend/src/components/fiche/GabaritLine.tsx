import { useQuery } from '@tanstack/react-query'
import { getGabarit, type GabGeom } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { FactRow, PorteOutil, Vigilance } from './primitives'

// Tiroir §10 Potentiel — ligne « Gabarit réglementaire » (GABARIT-2). Réutilise les primitives
// .fiche-v6 (FactRow/PorteOutil/Vigilance), aucun redesign. La hauteur PLU vit en §4 Urbanisme :
// le tiroir la CITE (source « §4 Urbanisme »), ne la redéclare pas. Mini-plan 2D = SVG des géométries
// servies (contour / retraits / zone / exclusion), sans carte ni recalcul.

const C_ZONE = '#36c99a'
const C_RETRAIT = '#e0a44a'
const C_EXCL = '#e8491d'

// GABARIT-6 — hauteur décimale sûre (l'égout vaut souvent 4,5 m : fmtInt l'arrondirait à tort).
const fmtH = (m?: number | null) => (m == null ? '' : m.toLocaleString('fr-FR'))

function* rings(geom: GabGeom): Generator<number[][]> {
  if (!geom) return
  const co = (geom as { coordinates: unknown }).coordinates
  if (geom.type === 'Polygon') {
    for (const r of co as number[][][]) yield r
  } else if (geom.type === 'MultiPolygon') {
    for (const poly of co as number[][][][]) for (const r of poly) yield r
  }
}

/** Mini-plan 2D des géométries réglementaires servies (schéma, pas une carte). */
function MiniPlan({ contour, zone, retrait, excl }: {
  contour?: GabGeom; zone?: GabGeom; retrait?: GabGeom; excl?: GabGeom
}) {
  const W = 150, H = 110, PAD = 6
  let minx = 1e9, miny = 1e9, maxx = -1e9, maxy = -1e9
  for (const g of [contour, zone, retrait, excl]) {
    for (const r of rings(g ?? null)) for (const [x, y] of r) {
      minx = Math.min(minx, x); miny = Math.min(miny, y)
      maxx = Math.max(maxx, x); maxy = Math.max(maxy, y)
    }
  }
  if (minx > maxx) return null
  const sx = (W - 2 * PAD) / Math.max(maxx - minx, 1e-9)
  const sy = (H - 2 * PAD) / Math.max(maxy - miny, 1e-9)
  const s = Math.min(sx, sy)
  const px = (x: number) => PAD + (x - minx) * s
  const py = (y: number) => H - PAD - (y - miny) * s   // flip : lat vers le haut
  const path = (g?: GabGeom) => {
    let d = ''
    for (const r of rings(g ?? null)) {
      d += 'M' + r.map(([x, y]) => `${px(x).toFixed(1)},${py(y).toFixed(1)}`).join('L') + 'Z'
    }
    return d
  }
  return (
    <svg data-gabarit-miniplan viewBox={`0 0 ${W} ${H}`} width={W} height={H}
      className="rounded-md border border-line-2 bg-surface-3/40" role="img"
      aria-label="Plan de la zone d'implantation réglementaire">
      {retrait && <path d={path(retrait)} fill={C_RETRAIT} fillOpacity={0.3} stroke="none" />}
      {excl && <path d={path(excl)} fill={C_EXCL} fillOpacity={0.45} stroke="none" />}
      {zone && <path d={path(zone)} fill={C_ZONE} fillOpacity={0.55} stroke={C_ZONE} strokeWidth={0.6} />}
      {contour && <path d={path(contour)} fill="none" stroke="#9aa0a6" strokeWidth={0.8} strokeDasharray="3 1.5" />}
    </svg>
  )
}

export function GabaritLine({ idu }: { idu: string }) {
  const setParcelPrefill = useApp((s) => s.setParcelPrefill)
  const setModule = useApp((s) => s.setModule)
  const pushOutilRetour = useApp((s) => s.pushOutilRetour)
  const q = useQuery({ queryKey: ['gabarit', idu], queryFn: () => getGabarit(idu), retry: false })
  const r = q.data
  // GABARIT-6 P2 — parcelle à cheval : cadastre entier (= la fiche) puis portion servie en sous-ligne.
  const rc = (r?.raccordement ?? null) as { parcelle?: { surface_m2?: number | null }; zone?: { code?: string; a_cheval?: boolean } } | null
  const cadM2 = rc?.parcelle?.surface_m2 ?? null
  const chev = !!rc?.zone?.a_cheval && cadM2 != null && r?.surfaceParcelleM2 != null
  const pctChev = chev ? Math.round((r!.surfaceParcelleM2! / cadM2!) * 100) : null

  const ouvrir = () => {
    setParcelPrefill(idu)
    setModule('gabarit')
    pushOutilRetour({ module: '', label: 'Fiche', restore: {} })
  }

  const porte = (
    <PorteOutil ico="◱" data="gabarit" titre="Ouvrir le Gabarit" compacte
      sous="Zone d'implantation, retraits, 2D / 3D sur la carte" onClick={ouvrir} />
  )

  return (
    <div data-gabarit-fiche className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-2/60 p-2.5">
      <p className="label-caps text-[9.5px] text-txt-dim">Gabarit réglementaire</p>
      {q.isLoading && <span className="text-[11px] text-txt-dim">Calcul…</span>}
      {q.isError && <span className="text-[11px] text-st-ecartee">Gabarit indisponible.</span>}
      {r && r.status === 'incomplete' && (
        <>
          <Vigilance title="Calcul incomplet — donnée réglementaire manquante">
            {(r.validationErrors?.[0] ?? r.message ?? '')}
          </Vigilance>
          {porte}
        </>
      )}
      {r && r.status === 'ok' && (
        <>
          <div className="flex gap-3">
            <div className="flex min-w-0 flex-1 flex-col">
              <FactRow label="Surface parcelle" value={chev
                ? <span style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-end', lineHeight: 1.15 }}>
                    <span>{fmtInt(cadM2)} m²</span>
                    <span style={{ fontSize: 10, color: 'var(--txt-dim)' }}>dont {fmtInt(r.surfaceParcelleM2)} m² en {rc?.zone?.code} ({pctChev} %)</span>
                  </span>
                : `${fmtInt(r.surfaceParcelleM2)} m²`} />
              <FactRow label="Zone d'implantation" value={`${fmtInt(r.zoneImplantationM2)} m²`} />
              <FactRow label="Plafond d'emprise"
                value={r.plafondEmpriseStatus === 'absent' ? 'Non réglementé' : `${fmtInt(r.plafondEmpriseM2)} m²`}
                tone={r.plafondEmpriseStatus === 'absent' ? 'mute' : undefined} />
              <FactRow label="Hauteur réglementaire"
                value={r.hauteurStatus === 'not_integrated'
                  ? 'Non chiffrée (prospect)'
                  : r.hauteurBase === 'egout'
                    ? `${fmtH(r.hauteurReglementaireM)} m à l'égout`
                    : r.hauteurEgoutM != null
                      ? <span style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-end', lineHeight: 1.15 }}>
                          <span>{fmtH(r.hauteurReglementaireM)} m max</span>
                          <span style={{ fontSize: 10, color: 'var(--txt-dim)' }}>égout {fmtH(r.hauteurEgoutM)} m</span>
                        </span>
                      : `${fmtH(r.hauteurReglementaireM)} m`}
                tone={r.hauteurStatus === 'not_integrated' ? 'mute' : undefined} src="§4 Urbanisme" />
            </div>
            <MiniPlan contour={r.contourGeoJSON} zone={r.zoneImplantationGeoJSON}
              retrait={r.retraitsGeoJSON} excl={r.exclusionsGeoJSON} />
          </div>
          {porte}
        </>
      )}
    </div>
  )
}
