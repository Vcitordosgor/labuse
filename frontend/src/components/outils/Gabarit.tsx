import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getGabarit, type GabaritResult, type GabGeom } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { ParcelInput } from '../ParcelInput'

// GABARIT-1 — outil « Gabarit réglementaire ». Traduit graphiquement et mathématiquement des règles
// SOURCÉES : SOURCE → VALIDATION → CALCUL → AFFICHAGE. Jamais d'estimation (logements/étages/SDP/coût/
// valeur/potentiel). Le front n'affiche que ce que le moteur pur sert (zéro recalcul).
// DA LABUSE : fond sombre, accent vert mint ; le mauve reste réservé à l'IA. Aucun redesign.
// ⚠ GABARIT-1 : la classification des limites est différée (GABARIT-2) → sur une parcelle réelle le
// moteur renvoie honnêtement « Calcul incomplet ». La démonstration (données fictives, CDC §9) montre
// le calcul complet.

const C_ZONE = '#36c99a'      // zone d'implantation — vert franc, distinct du fond (pas de camaïeu)
const C_RETRAIT = '#e0a44a'   // bandes de recul — ambre
const C_EXCL = '#e8491d'      // exclusions (PPR rouge) — rouge
const C_CONTOUR = '#ffffff'   // contour cadastral

const SRC = 'gabarit-outil'
const LAYERS = ['gabarit-zone', 'gabarit-contour', 'gabarit-retrait', 'gabarit-excl', 'gabarit-zone-3d']

type MapLike = {
  getSource: (id: string) => unknown
  addSource: (id: string, s: unknown) => void
  removeSource: (id: string) => void
  getLayer: (id: string) => unknown
  addLayer: (l: unknown) => void
  removeLayer: (id: string) => void
  fitBounds: (b: number[][], o?: unknown) => void
}

function getMap(): MapLike | null {
  return (window as unknown as Record<string, MapLike | undefined>).__labuse_map ?? null
}

function feat(geom: GabGeom, kind: string) {
  return geom ? { type: 'Feature', properties: { kind }, geometry: geom } : null
}

function bboxOf(geom: GabGeom): number[][] | null {
  if (!geom) return null
  let minx = 180, miny = 90, maxx = -180, maxy = -90
  const walk = (a: unknown) => {
    if (typeof (a as number[])[0] === 'number' && (a as number[]).length >= 2) {
      const [x, y] = a as number[]
      minx = Math.min(minx, x); miny = Math.min(miny, y)
      maxx = Math.max(maxx, x); maxy = Math.max(maxy, y)
    } else (a as unknown[]).forEach(walk)
  }
  walk((geom as { coordinates: unknown }).coordinates)
  return [[minx, miny], [maxx, maxy]]
}

/** Dessine (ou retire) les couches réglementaires sur la carte, seulement après validation réussie. */
function useMapLayers(res: GabaritResult | undefined, terrain3d: boolean) {
  useEffect(() => {
    const m = getMap()
    if (!m) return
    const clear = () => {
      LAYERS.forEach((id) => { try { if (m.getLayer(id)) m.removeLayer(id) } catch { /* noop */ } })
      try { if (m.getSource(SRC)) m.removeSource(SRC) } catch { /* noop */ }
    }
    clear()
    if (!res || res.status !== 'ok' || !res.zoneImplantationGeoJSON) return
    const features = [
      feat(res.retraitsGeoJSON ?? null, 'retrait'),
      feat(res.exclusionsGeoJSON ?? null, 'excl'),
      feat(res.zoneImplantationGeoJSON ?? null, 'zone'),
      feat(res.contourGeoJSON ?? null, 'contour'),
    ].filter(Boolean)
    m.addSource(SRC, { type: 'geojson', data: { type: 'FeatureCollection', features } })
    m.addLayer({ id: 'gabarit-retrait', type: 'fill', source: SRC, filter: ['==', 'kind', 'retrait'],
      paint: { 'fill-color': C_RETRAIT, 'fill-opacity': 0.3 } })
    m.addLayer({ id: 'gabarit-excl', type: 'fill', source: SRC, filter: ['==', 'kind', 'excl'],
      paint: { 'fill-color': C_EXCL, 'fill-opacity': 0.45 } })
    m.addLayer({ id: 'gabarit-zone', type: 'fill', source: SRC, filter: ['==', 'kind', 'zone'],
      paint: { 'fill-color': C_ZONE, 'fill-opacity': 0.5 } })
    m.addLayer({ id: 'gabarit-contour', type: 'line', source: SRC, filter: ['==', 'kind', 'contour'],
      paint: { 'line-color': C_CONTOUR, 'line-width': 1.5, 'line-dasharray': [2, 1] } })
    // 3D : extrusion de la SEULE zone calculée, à la hauteur SOURCÉE (aucun fallback) ; jamais un bâtiment réel.
    if (terrain3d && res.hauteurReglementaireM != null) {
      m.addLayer({ id: 'gabarit-zone-3d', type: 'fill-extrusion', source: SRC,
        filter: ['==', 'kind', 'zone'],
        paint: { 'fill-extrusion-color': C_ZONE, 'fill-extrusion-opacity': 0.6,
                 'fill-extrusion-height': res.hauteurReglementaireM, 'fill-extrusion-base': 0 } })
    }
    const bb = bboxOf(res.contourGeoJSON ?? res.zoneImplantationGeoJSON ?? null)
    if (bb) { try { m.fitBounds(bb, { padding: 80, duration: 600, maxZoom: 19 }) } catch { /* noop */ } }
    return clear
  }, [res, terrain3d])
}

function Num({ label, value, unit, accent }: {
  label: string; value: number | null | undefined; unit: string; accent?: boolean
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="label-caps text-[9.5px] leading-tight text-txt-dim">{label}</span>
      <span className={`font-mono text-[15px] tabular-nums ${accent ? 'text-mint' : 'text-txt-hi'}`}>
        {value != null ? `${fmtInt(value)} ${unit}` : '—'}
      </span>
    </div>
  )
}

export function Gabarit() {
  const selectedIdu = useApp((s) => s.selectedIdu)
  const terrain3d = useApp((s) => s.terrain3d)
  const [idu, setIdu] = useState<string | null>(selectedIdu)
  const [demo, setDemo] = useState(false)

  useEffect(() => {
    if (selectedIdu && selectedIdu !== idu) { setIdu(selectedIdu); setDemo(false) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIdu])

  const target = demo ? 'demo' : idu
  const q = useQuery({
    queryKey: ['gabarit', target],
    queryFn: () => getGabarit(target!),
    enabled: !!target, retry: false,
  })
  const res = q.data
  useMapLayers(res, terrain3d)

  const familles = res?.coverage
    ? [
        { k: 'reculs', ok: res.coverage.reculs, label: 'Reculs vérifiés' },
        { k: 'hauteur', ok: res.coverage.hauteur, label: 'Hauteur vérifiée' },
        { k: 'emprise', ok: res.coverage.emprise, label: 'Emprise vérifiée' },
        { k: 'risques', ok: res.coverage.risques, label: 'Risques intégrés' },
      ]
    : []
  const nbVerifiees = familles.filter((f) => f.ok).length
  const appliedSetbacks = useMemo(
    () => (res?.appliedRules ?? []).filter((r) => r.category === 'setback'), [res])
  const appliedOther = useMemo(
    () => (res?.appliedRules ?? []).filter((r) => r.category !== 'setback'), [res])

  const reset = () => { setIdu(null); setDemo(false) }

  return (
    <div data-gabarit-panel className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <p className="text-[11px] leading-snug text-txt-mut">
        Où et jusqu'où une construction peut s'implanter, selon les règles réglementaires
        <b className="text-txt"> intégrées et sourcées</b> dans LABUSE.
      </p>

      <ParcelInput dataAttr="gabarit-parcelle" withCarte={false}
        onPick={(i: string) => { setIdu(i); setDemo(false) }}
        placeholder="Adresse, IDU ou référence (ex. BZ1065)" />
      <p className="text-[10px] text-txt-dim">… ou cliquez une parcelle sur la carte.</p>

      <button data-gabarit-demo onClick={() => setDemo(true)}
        className="self-start rounded-md border border-line-2 bg-surface-3 px-2.5 py-1 text-[10.5px] text-txt-mut hover:border-mint hover:text-mint">
        Voir la démonstration (données fictives)
      </button>

      {!target && (
        <p className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] leading-snug text-txt-dim">
          Choisissez une parcelle, ou ouvrez la démonstration.
        </p>
      )}

      {q.isLoading && <p className="text-[11px] text-txt-mut">Calcul…</p>}
      {q.isError && <p className="text-[11px] text-st-ecartee">Parcelle inconnue ou service indisponible.</p>}

      {/* CALCUL INCOMPLET — message EXACT, aucune zone / métrique / 3D (CDC §3). */}
      {res && res.status === 'incomplete' && (
        <div data-gabarit-incomplet className="flex flex-col gap-1.5 rounded-lg border border-st-creuser/40 bg-st-creuser/10 px-3 py-2.5">
          <p className="text-[12px] font-medium text-st-creuser">{res.message}</p>
          {res.validationErrors?.length > 0 && (
            <ul className="ml-3 list-disc text-[10.5px] leading-snug text-txt-mut">
              {res.validationErrors.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          )}
        </div>
      )}

      {/* RÉSULTAT COMPLET (démonstration en GABARIT-1) */}
      {res && res.status === 'ok' && (
        <>
          {demo && (
            <p data-gabarit-fictif className="rounded-md border border-line-2 bg-surface-3/60 px-2.5 py-1 text-[10px] text-txt-dim">
              Démonstration — données fictives (CDC §9). Sources marquées « fictif ».
            </p>
          )}
          <div data-gabarit-chiffres className="grid grid-cols-2 gap-x-3 gap-y-2 rounded-lg border border-line-2 bg-surface-2 p-3">
            <Num label="Surface parcelle" value={res.surfaceParcelleM2} unit="m²" />
            <Num label="Zone d'implantation" value={res.zoneImplantationM2} unit="m²" accent />
            <Num label="Plafond d'emprise" value={res.plafondEmpriseM2} unit="m²" />
            <Num label="Hauteur réglementaire" value={res.hauteurReglementaireM} unit="m" />
          </div>

          {/* COUVERTURE — les 4 familles (ni segments ni articles) */}
          <div data-gabarit-couverture className="rounded-lg border border-line-2 bg-surface-2 p-3">
            <p className="text-[11px] text-txt">
              <b className="text-mint">{nbVerifiees} familles vérifiées</b>
              {res.nonIntegratedRules.length > 0 && (
                <span className="text-txt-dim"> · {res.nonIntegratedRules.length} règle{res.nonIntegratedRules.length > 1 ? 's' : ''} non intégrée{res.nonIntegratedRules.length > 1 ? 's' : ''}</span>
              )}
            </p>
            <ul className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1 text-[10.5px]">
              {familles.map((f) => (
                <li key={f.k} className={f.ok ? 'text-txt-mut' : 'text-txt-dim'}>
                  {f.ok ? '✓' : '·'} {f.label}
                </li>
              ))}
            </ul>
          </div>

          {/* RÈGLES APPLIQUÉES — générées depuis le moteur, aucune valeur en dur */}
          <details data-gabarit-regles className="group rounded-lg border border-line-2 bg-surface-2">
            <summary className="hover-fill flex cursor-pointer list-none items-center gap-1.5 rounded-lg px-3 py-2 text-[11px] text-txt">
              <span aria-hidden className="text-txt-dim transition-transform duration-quick group-open:rotate-90">›</span>
              <b>Voir les règles appliquées</b>
            </summary>
            <div className="flex flex-col gap-2 px-3 pb-3">
              {[...appliedSetbacks, ...appliedOther].map((r, i) => (
                <div key={i} data-gabarit-regle className="border-b border-line pb-1.5 last:border-0">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-[11px] text-txt">✓ {r.label}</span>
                    {r.value != null && <span className="font-mono text-[11px] tabular-nums text-mint">{r.value}{r.unit ? ` ${r.unit}` : ''}</span>}
                  </div>
                  <span className="block text-[9.5px] leading-snug text-txt-dim">
                    {[r.source.document, r.source.zone, r.source.article].filter(Boolean).join(' — ')}
                    {r.source.versionDate ? ` — ${r.source.versionDate}` : ''}
                  </span>
                </div>
              ))}
              {res.nonIntegratedRules.length > 0 && (
                <div className="mt-1 rounded-md border border-st-creuser/30 bg-st-creuser/5 px-2.5 py-1.5">
                  <p className="text-[10.5px] font-medium text-st-creuser">
                    ⚠ {res.nonIntegratedRules.length} règle{res.nonIntegratedRules.length > 1 ? 's' : ''} applicable{res.nonIntegratedRules.length > 1 ? 's' : ''} non intégrée{res.nonIntegratedRules.length > 1 ? 's' : ''}
                  </p>
                  <ul className="ml-3 list-disc text-[10px] leading-snug text-txt-mut">
                    {res.nonIntegratedRules.map((n, i) => <li key={i}>{n.label}</li>)}
                  </ul>
                </div>
              )}
            </div>
          </details>

          {/* CARTE / 3D */}
          <div data-gabarit-carte className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[10.5px] leading-snug text-txt-dim">
            <p><span className="mr-1 inline-block h-2 w-2 rounded-sm align-middle" style={{ background: C_ZONE }} /> Zone d'implantation réglementaire sur la carte.</p>
            {terrain3d
              ? <p className="mt-1 text-txt-mut">3D active — <b className="text-txt">Enveloppe réglementaire selon les règles intégrées</b> (hauteur sourcée {res.hauteurReglementaireM} m).</p>
              : <p className="mt-1">Bascule 2D / 3D : bouton <b className="text-txt">3D</b> de la carte.</p>}
          </div>

          <button data-gabarit-reset onClick={reset}
            className="self-start rounded-md border border-line-2 bg-surface-3 px-2.5 py-1 text-[10.5px] text-txt-mut hover:border-mint hover:text-mint">
            Réinitialiser
          </button>
        </>
      )}
    </div>
  )
}
