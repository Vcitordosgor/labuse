import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getGabarit, type GabaritResult, type GabGeom } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { ParcelInput } from '../ParcelInput'
import { Squelette } from '../Loading'
import { ErrorState } from '../States'
import { Bouton } from '../ui/Bouton'
import { Chevron } from '../ui/Chevron'

// Outil « Gabarit réglementaire ». Traduit graphiquement et mathématiquement des règles SOURCÉES :
// SOURCE → VALIDATION → CALCUL → AFFICHAGE. Jamais d'estimation (logements/étages/SDP/coût/valeur/
// potentiel). Le front n'affiche que ce que le moteur pur sert (zéro recalcul). DA LABUSE : fond
// sombre, accent vert mint ; le mauve reste réservé à l'IA. Aucun redesign.
// GABARIT-2 : classification des limites (voie/séparative) servie sur le réel (adjacence cadastre +
// BD TOPO). Sur une parcelle sans façade ou à limite non qualifiée, le moteur renvoie honnêtement
// « Calcul incomplet » + le motif.

const C_ZONE = '#36c99a'      // zone d'implantation — vert franc, distinct du fond (pas de camaïeu)
const C_RETRAIT = '#e0a44a'   // bandes de recul — ambre
const C_EXCL = '#e8491d'      // exclusions (PPR rouge) — rouge
const C_CONTOUR = '#ffffff'   // contour cadastral
const C_BATI = '#9aa0a6'      // bâti existant — gris neutre (un FAIT contextuel, jamais un signal)

const SRC = 'gabarit-outil'
const LAYERS = ['gabarit-zone', 'gabarit-contour', 'gabarit-retrait', 'gabarit-excl', 'gabarit-zone-3d',
                'gabarit-bati', 'gabarit-bati-line', 'gabarit-bati-3d']

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
function useMapLayers(res: GabaritResult | undefined, terrain3d: boolean, batiVisible: boolean) {
  useEffect(() => {
    const m = getMap()
    if (!m) return
    const clear = () => {
      LAYERS.forEach((id) => { try { if (m.getLayer(id)) m.removeLayer(id) } catch { /* noop */ } })
      try { if (m.getSource(SRC)) m.removeSource(SRC) } catch { /* noop */ }
    }
    clear()
    if (!res) return
    const ok = res.status === 'ok' && !!res.zoneImplantationGeoJSON
    // GABARIT-6 lot B : même quand le calcul est incomplet, on centre sur la parcelle et on trace son
    // contour cadastral (jamais d'écran vide). Les couches réglementaires (zone/retrait/3D) restent
    // réservées au calcul complet.
    // RETOURS-15 D4 — RÉGRESSION : une parcelle « terrain exigu » revient status='ok' MAIS sans zone
    // constructible (zoneImplantationGeoJSON null) — ex. 97411000BZ1065. L'ancien contourOnly ne
    // couvrait QUE status='incomplete' → ni zone ni contour n'étaient tracés, la parcelle disparaissait
    // en 2D. On trace donc le contour dès qu'on l'a et que la zone n'est pas dessinable (tout statut).
    const contourOnly = !ok && !!res.contourGeoJSON
    if (!ok && !contourOnly) return
    // GABARIT-6 P4 — le bâti EXISTANT (emprise BD TOPO), FAIT contextuel, servi que le calcul soit
    // complet ou non (l'outil dit où l'on PEUT construire ; ceci dit ce qui est DÉJÀ là). Chaque
    // Feature porte sa hauteur mesurée (LiDAR HD, à défaut BD TOPO) pour l'extrusion 3D.
    const batiFeats = (res.batiExistantGeoJSON?.features ?? []).map((f) => ({
      type: 'Feature' as const,
      properties: { kind: 'bati', hauteur_m: f.properties?.hauteur_m ?? null },
      geometry: f.geometry,
    }))
    const features = [
      ...(ok
        ? [
            feat(res.retraitsGeoJSON ?? null, 'retrait'),
            feat(res.exclusionsGeoJSON ?? null, 'excl'),
            feat(res.zoneImplantationGeoJSON ?? null, 'zone'),
            feat(res.contourGeoJSON ?? null, 'contour'),
          ]
        : [feat(res.contourGeoJSON ?? null, 'contour')]).filter(Boolean),
      ...batiFeats,
    ]
    m.addSource(SRC, { type: 'geojson', data: { type: 'FeatureCollection', features } })
    if (ok) {
      m.addLayer({ id: 'gabarit-retrait', type: 'fill', source: SRC, filter: ['==', 'kind', 'retrait'],
        paint: { 'fill-color': C_RETRAIT, 'fill-opacity': 0.3 } })
      m.addLayer({ id: 'gabarit-excl', type: 'fill', source: SRC, filter: ['==', 'kind', 'excl'],
        paint: { 'fill-color': C_EXCL, 'fill-opacity': 0.45 } })
      m.addLayer({ id: 'gabarit-zone', type: 'fill', source: SRC, filter: ['==', 'kind', 'zone'],
        paint: { 'fill-color': C_ZONE, 'fill-opacity': 0.5 } })
    }
    // GABARIT-6 P4 — bâti existant en surimpression 2D (emprise grise + contour), sous le contour cadastral.
    if (batiFeats.length) {
      m.addLayer({ id: 'gabarit-bati', type: 'fill', source: SRC, filter: ['==', 'kind', 'bati'],
        paint: { 'fill-color': C_BATI, 'fill-opacity': 0.35 } })
      m.addLayer({ id: 'gabarit-bati-line', type: 'line', source: SRC, filter: ['==', 'kind', 'bati'],
        paint: { 'line-color': C_BATI, 'line-width': 1 } })
    }
    m.addLayer({ id: 'gabarit-contour', type: 'line', source: SRC, filter: ['==', 'kind', 'contour'],
      paint: { 'line-color': C_CONTOUR, 'line-width': 1.5, 'line-dasharray': [2, 1] } })
    // 3D : extrusion de la zone calculée (enveloppe réglementaire, vert) à la hauteur SOURCÉE. Le bâti
    // existant (gris) est extrudé À PART, à sa hauteur MESURÉE (LiDAR HD, à défaut BD TOPO) : où l'on
    // PEUT construire vs ce qui est DÉJÀ là. Deux couches distinctes, jamais confondues.
    if (ok && terrain3d && res.hauteurReglementaireM != null) {
      m.addLayer({ id: 'gabarit-zone-3d', type: 'fill-extrusion', source: SRC,
        filter: ['==', 'kind', 'zone'],
        paint: { 'fill-extrusion-color': C_ZONE, 'fill-extrusion-opacity': 0.6,
                 'fill-extrusion-height': res.hauteurReglementaireM, 'fill-extrusion-base': 0 } })
    }
    // RETOURS-13 P4 — le bâti existant s'extrude en 3D UNIQUEMENT si le chip « Bâtiments » est actif.
    // Chip off → l'empreinte 2D grise (gabarit-bati, plus haut) reste : « bâti à plat », relief seul.
    if (terrain3d && batiVisible && batiFeats.length) {
      m.addLayer({ id: 'gabarit-bati-3d', type: 'fill-extrusion', source: SRC,
        filter: ['==', 'kind', 'bati'],
        paint: { 'fill-extrusion-color': C_BATI, 'fill-extrusion-opacity': 0.55,
                 'fill-extrusion-height': ['coalesce', ['get', 'hauteur_m'], 3], 'fill-extrusion-base': 0 } })
    }
    const bb = bboxOf(res.contourGeoJSON ?? res.zoneImplantationGeoJSON ?? null)
    if (bb) { try { m.fitBounds(bb, { padding: 80, duration: 600, maxZoom: 19 }) } catch { /* noop */ } }
    return clear
  }, [res, terrain3d, batiVisible])
}

function Num({ label, value, unit, accent, statusLabel, sub }: {
  label: string; value: number | null | undefined; unit: string; accent?: boolean
  statusLabel?: string | null; sub?: string | null
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="label-caps text-[9.5px] leading-tight text-txt-dim">{label}</span>
      {statusLabel
        ? <span className="text-[12px] font-medium text-txt-mut">{statusLabel}</span>
        : <span className={`font-mono text-[15px] tabular-nums ${accent ? 'text-mint' : 'text-txt-hi'}`}>
            {value != null ? `${fmtInt(value)} ${unit}` : '—'}
          </span>}
      {sub && <span className="text-[9px] leading-tight text-txt-dim">{sub}</span>}
    </div>
  )
}

export function Gabarit() {
  const selectedIdu = useApp((s) => s.selectedIdu)
  const focusParcelle = useApp((s) => s.focusParcelle)   // RETOURS-15 C4 — zoom + contour à la résolution
  const terrain3d = useApp((s) => s.terrain3d)
  const setTerrain3d = useApp((s) => s.setTerrain3d)   // RETOURS-15 D4 — bascule 2D / 3D dans le panneau
  const batiVisible = useApp((s) => s.batiVisible)   // RETOURS-13 P4 — chip « Bâtiments » (session)
  const [idu, setIdu] = useState<string | null>(selectedIdu)
  const [reglesOuvertes, setReglesOuvertes] = useState(true)   // RETOURS-15 D3 — « Voir les règles appliquées » ouvert par défaut
  const [nonIntOuvertes, setNonIntOuvertes] = useState(true)    // GABARIT-6 P3 — liste des règles non intégrées, ouverte par défaut

  useEffect(() => {
    if (selectedIdu && selectedIdu !== idu) setIdu(selectedIdu)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIdu])

  const target = idu
  const q = useQuery({
    queryKey: ['gabarit', target],
    queryFn: () => getGabarit(target!),
    enabled: !!target, retry: false,
  })
  const res = q.data
  useMapLayers(res, terrain3d, batiVisible)

  const familles = res?.coverage
    ? [
        { k: 'reculs', ok: res.coverage.reculs, label: 'Reculs vérifiés' },
        { k: 'hauteur', ok: res.coverage.hauteur,
          label: res.hauteurStatus === 'not_integrated' ? 'Hauteur non intégrée (prospect L ≥ H)' : 'Hauteur vérifiée' },
        { k: 'emprise', ok: res.coverage.emprise,
          label: res.plafondEmpriseStatus === 'absent' ? 'Emprise vérifiée — sans plafond' : 'Emprise vérifiée' },
        { k: 'risques', ok: res.coverage.risques, label: 'Risques intégrés' },
      ]
    : []
  const nbVerifiees = familles.filter((f) => f.ok).length
  const appliedSetbacks = useMemo(
    () => (res?.appliedRules ?? []).filter((r) => r.category === 'setback'), [res])
  const appliedOther = useMemo(
    () => (res?.appliedRules ?? []).filter((r) => r.category !== 'setback'), [res])
  // GABARIT-6 lot B : référence + commune de la parcelle (servies par raccordement.parcelle), affichées
  // même quand le calcul est incomplet, au-dessus du motif.
  const parcelle = (res?.raccordement?.parcelle ?? null) as
    { idu?: string; commune?: string; surface_m2?: number | null } | null
  // GABARIT-6 P2 — parcelle à cheval : l'outil sert le gabarit sur la portion de la zone constructible
  // dominante. On affiche le CADASTRE ENTIER (= la fiche) puis la portion servie en sous-ligne (cf.
  // GABARIT-AUDIT-1 : « Surface parcelle 7 465 m² » masquait qu'il s'agissait d'un morceau, pas de la parcelle).
  const raccZone = (res?.raccordement?.zone ?? null) as { code?: string; a_cheval?: boolean } | null
  const cadastreM2 = parcelle?.surface_m2 ?? null
  const aCheval = !!raccZone?.a_cheval && cadastreM2 != null && res?.surfaceParcelleM2 != null
  // FRONT-CHIFFRES-2 (F50/F57) — % « à cheval » SERVI (pctPortionZone) ; ce ratio vivait à DEUX sites
  // front (ici + GabaritLine) → recalculé une seule fois au back, les deux le lisent (plus de divergence).
  const pctPortion = res?.pctPortionZone ?? null

  return (
    <div data-gabarit-panel className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <p className="text-[11px] leading-snug text-txt-mut">
        Où et jusqu'où une construction peut s'implanter, selon les règles réglementaires
        <b className="text-txt"> intégrées et sourcées</b> dans LABUSE.
      </p>

      <ParcelInput dataAttr="gabarit-parcelle"
        onPick={(i: string) => { setIdu(i); focusParcelle(i) }}
        placeholder="Adresse, IDU ou référence (BW0917)" />

      {!target && (
        <p className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] leading-snug text-txt-dim">
          Choisissez une parcelle (barre ci-dessus ou clic sur la carte).
        </p>
      )}

      {q.isLoading && <Squelette lignes={4} />}
      {q.isError && <ErrorState message="Parcelle inconnue ou service indisponible." retry={() => q.refetch()} />}

      {/* CALCUL INCOMPLET — la parcelle reste VISIBLE (contour tracé, réf + commune au-dessus du motif).
          Aucune zone / métrique / 3D réglementaire (CDC §3). */}
      {res && res.status === 'incomplete' && (
        <div data-gabarit-incomplet className="flex flex-col gap-1.5 rounded-lg border border-st-creuser/40 bg-st-creuser/10 px-3 py-2.5">
          {(parcelle?.idu || parcelle?.commune) && (
            <p data-gabarit-parcelle-ref className="text-[11px] font-medium text-txt">
              Parcelle {parcelle?.idu ?? '—'}{parcelle?.commune ? ` · ${parcelle.commune}` : ''}
            </p>
          )}
          <p className="text-[12px] font-medium text-st-creuser">{res.message}</p>
          {res.validationErrors?.length > 0 && (
            <ul className="ml-3 list-disc text-[10.5px] leading-snug text-txt-mut">
              {res.validationErrors.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          )}
          <p className="text-[10px] leading-snug text-txt-dim">
            Contour de la parcelle tracé sur la carte. Le calcul du gabarit reprendra dès que la donnée
            manquante sera disponible.
          </p>
        </div>
      )}

      {/* RÉSULTAT COMPLET */}
      {res && res.status === 'ok' && (
        <>
          <div data-gabarit-chiffres className="grid grid-cols-2 gap-x-3 gap-y-2 rounded-lg border border-line-2 bg-surface-2 p-3">
            {aCheval
              ? <Num label="Surface parcelle" value={cadastreM2} unit="m²"
                  sub={`dont ${fmtInt(res.surfaceParcelleM2)} m² en ${raccZone?.code ?? 'zone U'} (${pctPortion} %)`} />
              : <Num label="Surface parcelle" value={res.surfaceParcelleM2} unit="m²" />}
            <Num label="Zone d'implantation" value={res.zoneImplantationM2} unit="m²" accent />
            <Num label="Plafond d'emprise" value={res.plafondEmpriseM2} unit="m²"
              statusLabel={res.plafondEmpriseStatus === 'absent' ? 'Non réglementé' : null}
              sub={res.plafondEmpriseStatus === 'absent' ? 'pas de règle d’emprise au sol' : null} />
            <Num label="Hauteur réglementaire" value={res.hauteurReglementaireM} unit="m"
              statusLabel={res.hauteurStatus === 'not_integrated' ? 'Non chiffrée' : null}
              sub={res.hauteurStatus === 'not_integrated' ? 'prospect L ≥ H (non intégré)' : null} />
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
                  {f.ok ? '✓' : '⚠'} {f.label}
                </li>
              ))}
            </ul>
            {/* GABARIT-6 P3 — la LISTE des règles connues mais non intégrées (le compte seul vivait
                ci-dessus). Nom · pourquoi (souvent avec la citation PLU) · source. Rien d'inventé :
                exactement ce que le moteur renvoie dans nonIntegratedRules. */}
            {res.nonIntegratedRules.length > 0 && (
              <details data-gabarit-non-integrees open={nonIntOuvertes}
                onToggle={(e) => setNonIntOuvertes((e.target as HTMLDetailsElement).open)}
                className="group mt-2 border-t border-line pt-2">
                <summary className="hover-fill flex cursor-pointer list-none items-center gap-1.5 rounded px-0.5 py-0.5 text-[10.5px] text-txt-mut">
                  <Chevron open={nonIntOuvertes} />
                  <b>Le détail des {res.nonIntegratedRules.length} règle{res.nonIntegratedRules.length > 1 ? 's' : ''} non intégrée{res.nonIntegratedRules.length > 1 ? 's' : ''}</b>
                </summary>
                <ul className="mt-1.5 flex flex-col gap-1.5">
                  {res.nonIntegratedRules.map((n, i) => (
                    <li key={i} data-gabarit-non-integree className="border-b border-line pb-1.5 last:border-0">
                      <span className="text-[10.5px] text-txt">{n.label}</span>
                      {n.detail && <span className="block text-[9.5px] italic leading-snug text-txt-dim">{n.detail}</span>}
                      {(n.source?.document || n.source?.zone || n.source?.article) && (
                        <span className="block text-[9px] leading-snug text-txt-ghost">
                          {[n.source.document, n.source.zone, n.source.article].filter(Boolean).join(' — ')}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>

          {/* RÈGLES APPLIQUÉES — générées depuis le moteur, aucune valeur en dur */}
          <details data-gabarit-regles open={reglesOuvertes}
            onToggle={(e) => setReglesOuvertes((e.target as HTMLDetailsElement).open)}
            className="group rounded-lg border border-line-2 bg-surface-2">
            <summary className="hover-fill flex cursor-pointer list-none items-center gap-1.5 rounded-lg px-3 py-2 text-[11px] text-txt">
              <Chevron open={reglesOuvertes} />
              <b>Voir les règles appliquées</b>
            </summary>
            <div className="flex flex-col gap-2 px-3 pb-3">
              {[...appliedSetbacks, ...appliedOther].map((r, i) => (
                <div key={i} data-gabarit-regle className="border-b border-line pb-1.5 last:border-0">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-[11px] text-txt">✓ {r.label}</span>
                    {r.value != null
                      ? <span className="font-mono text-[11px] tabular-nums text-mint">{r.value}{r.unit ? ` ${r.unit}` : ''}</span>
                      : r.detail && <span className="text-[10px] italic text-txt-dim">{r.detail}</span>}
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

          {/* CARTE / 3D — légende des couches réglementaires */}
          <div data-gabarit-carte className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[10.5px] leading-snug text-txt-dim">
            <p className="label-caps mb-1 text-[9px] text-txt-dim">Sur la carte</p>
            <ul className="flex flex-col gap-0.5">
              <li><span className="mr-1.5 inline-block h-2 w-3 rounded-sm align-middle" style={{ background: C_ZONE }} /> Zone d'implantation réglementaire</li>
              <li><span className="mr-1.5 inline-block h-2 w-3 rounded-sm align-middle" style={{ background: C_RETRAIT }} /> Retrait réglementaire</li>
              {res.exclusionsGeoJSON && <li><span className="mr-1.5 inline-block h-2 w-3 rounded-sm align-middle" style={{ background: C_EXCL }} /> Exclusion (PPR)</li>}
              {res.batiExistantGeoJSON?.features?.length ? (
                <li><span className="mr-1.5 inline-block h-2 w-3 rounded-sm align-middle" style={{ background: C_BATI }} /> Bâti existant (BD TOPO · LiDAR HD)</li>
              ) : null}
            </ul>
            {res.hauteurReglementaireM == null
              ? <p className="mt-1.5 text-st-creuser">3D indisponible — hauteur non chiffrée (prospect).</p>
              : terrain3d
                ? <p className="mt-1.5 text-txt-mut">3D active — <b className="text-txt">Enveloppe réglementaire selon les règles intégrées</b> (hauteur sourcée {res.hauteurReglementaireM} m).</p>
                : <p className="mt-1.5">Bascule 2D / 3D : bouton <b className="text-txt">3D</b> de la carte.</p>}
          </div>

          {/* RETOURS-15 D4 — bascule 2D / 3D DANS le panneau : le client n'a plus à passer par le menu
              3D en haut à droite. Même levier que ce menu (setTerrain3d), donc cohérent partout. */}
          <Bouton niveau="secondaire" ton="vert" data-gabarit-3d
            onClick={() => setTerrain3d(!terrain3d)} className="self-start">
            {terrain3d ? 'Revenir en 2D' : 'Voir en 3D'}
          </Bouton>
        </>
      )}
    </div>
  )
}
