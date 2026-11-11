import { useEffect, useMemo, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'   // RETOURS-26 (pt 4) — étiquettes de hauteur sur la vue 3D (Marker)
import { useQuery } from '@tanstack/react-query'
import { getGabarit, docGabaritUrl, type GabaritResult, type GabGeom } from '../../lib/api'
import { useOuvrirDocument } from '../../lib/ouvrirDocument'   // RECETTE-OUTILS-1 (34) — export = doc Gabarit
import { fmtInt } from '../../lib/format'
import { CAPACITE_MAX_MENTION_COURTE } from '../../lib/capaciteMax'
import { useApp } from '../../store/useApp'
import { EntreeParcelle, type SourceParcelle } from './EntreeParcelle'   // RECETTE-1 F2
import { Squelette } from '../Loading'
import { ErrorState } from '../States'
import { Bouton } from '../ui/Bouton'
import { Tip } from '../Tip'   // OUTILS-REFONTE-1 (9b) — « i » des puces « Non intégrées »

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
// RECETTE-OUTILS-2 (R15) — le liseré blanc de sélection de la carte de base (`selection-line`/`-halo`,
// posé depuis `getParcelGeojson`) est tracé depuis une AUTRE source que le gabarit (contour du moteur) :
// les deux parcelles sont la même mais légèrement décalées → « double contour en pointillés décalé ».
// On masque le liseré de base tant que le gabarit affiche SON contour (aligné à ses couches
// zone/retrait/bâti, toutes issues du même moteur), rétabli au nettoyage. Mesure géométrique :
// 0 % de bâti hors du contour moteur → le « bâti qui déborde » n'était QUE cet écart base/gabarit.
const SEL_BASE = ['selection-line', 'selection-halo']

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

/** Centre (lng,lat) d'une ou plusieurs géométries — pour poser une étiquette au milieu de la parcelle. */
function centerOf(...geoms: (GabGeom | null | undefined)[]): [number, number] | null {
  let minx = 180, miny = 90, maxx = -180, maxy = -90, seen = false
  for (const g of geoms) {
    const bb = g ? bboxOf(g) : null
    if (!bb) continue
    seen = true
    minx = Math.min(minx, bb[0][0]); miny = Math.min(miny, bb[0][1])
    maxx = Math.max(maxx, bb[1][0]); maxy = Math.max(maxy, bb[1][1])
  }
  return seen ? [(minx + maxx) / 2, (miny + maxy) / 2] : null
}

/** RETOURS-26 (pt 4) — étiquette de hauteur posée SUR la vue : pastille HTML (Marker). Les Markers
 *  maplibre sont alignés sur l'écran (billboard) : ils restent droits et lisibles sous TOUS les angles
 *  (pitch/rotation) de la 3D. Le décalage écran est passé via l'option `offset` du Marker (PAS un
 *  `transform` CSS, que maplibre écrase par son propre transform de positionnement). */
function mkHauteurEl(texte: string, couleur: string): HTMLDivElement {
  const el = document.createElement('div')
  el.setAttribute('data-gabarit-3d-label', texte)
  el.textContent = texte
  el.style.cssText = `font:600 11px ui-sans-serif,system-ui,sans-serif;color:${couleur};`
    + 'background:rgba(6,17,11,.86);padding:2px 8px;border-radius:6px;white-space:nowrap;pointer-events:none;'
    + `border:1px solid ${couleur}66;box-shadow:0 1px 4px rgba(0,0,0,.4)`
  return el
}

/** Dessine (ou retire) les couches réglementaires sur la carte, seulement après validation réussie. */
function useMapLayers(res: GabaritResult | undefined, terrain3d: boolean, batiVisible: boolean) {
  // RETOURS-26 (pt 4) — étiquettes de hauteur (Marker) posées sur la vue 3D ; retirées à chaque passe.
  const labels = useRef<maplibregl.Marker[]>([])
  useEffect(() => {
    const m = getMap()
    if (!m) return
    const setBaseSel = (v: 'visible' | 'none') =>
      SEL_BASE.forEach((id) => { try { const mm = m as unknown as { setLayoutProperty?: (i: string, p: string, x: string) => void }; if (m.getLayer(id)) mm.setLayoutProperty?.(id, 'visibility', v) } catch { /* noop */ } })
    const clear = () => {
      labels.current.forEach((mk) => { try { mk.remove() } catch { /* noop */ } })
      labels.current = []
      LAYERS.forEach((id) => { try { if (m.getLayer(id)) m.removeLayer(id) } catch { /* noop */ } })
      try { if (m.getSource(SRC)) m.removeSource(SRC) } catch { /* noop */ }
      setBaseSel('visible')   // R15 — le gabarit ne dessine plus : rendre le liseré de base
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
    setBaseSel('none')   // R15 — un seul contour (celui du gabarit, aligné à ses couches)
    // 3D : seule la ZONE (enveloppe réglementaire, vert) est extrudée — à la hauteur SOURCÉE (une RÈGLE,
    // fiable). RETOURS-27 (pt 3, correction) — le bâti existant n'est PLUS extrudé à la hauteur LiDAR :
    // cette hauteur n'est pas rattachée de façon sûre au bâtiment dessiné (elle peut venir d'un bâtiment
    // voisin qui touche la parcelle). On ne dessine donc AUCUN volume de bâti ; l'empreinte 2D grise
    // (gabarit-bati) reste pour situer le bâti, et le faîtage LiDAR est donné comme une valeur de PARCELLE
    // (étiquette flottante, non attachée à un volume).
    if (ok && terrain3d && res.hauteurReglementaireM != null) {
      m.addLayer({ id: 'gabarit-zone-3d', type: 'fill-extrusion', source: SRC,
        filter: ['==', 'kind', 'zone'],
        paint: { 'fill-extrusion-color': C_ZONE, 'fill-extrusion-opacity': 0.6,
                 'fill-extrusion-height': res.hauteurReglementaireM, 'fill-extrusion-base': 0 } })
    }
    // RETOURS-26/27 — DEUX pastilles écrites sur la vue (Marker, billboard = lisibles sous tous les
    // angles). « Règle : X m » (vert) = enveloppe réglementaire, attachée à son volume vert (hauteur
    // fiable). RETOURS-27 (pt 3, correction) — « Faîtage LiDAR sur la parcelle : X m » (gris) = la plus
    // haute toiture mesurée sur/au contact de la parcelle, donnée comme une valeur de PARCELLE, NON
    // attachée à un volume (la mesure n'est pas rattachée de façon sûre au bâtiment dessiné) ; offset
    // FIXE (pas proportionnel à une hauteur de volume), et AUCUNE comparaison « dépasse la règle ».
    const mapGl = m as unknown as maplibregl.Map
    const hRegle = ok && res.hauteurReglementaireM != null ? res.hauteurReglementaireM : null
    const hBati = batiFeats.length
      ? Math.round(Math.max(0, ...batiFeats.map((f) => Number(f.properties?.hauteur_m) || 0))) : 0
    const cParc = centerOf(res.zoneImplantationGeoJSON ?? null, res.contourGeoJSON ?? null)
    if (terrain3d && cParc && hRegle != null) {
      const dyRegle = -14 - Math.round((hRegle / Math.max(hRegle, 1)) * 42)   // pastille au niveau du toit de l'enveloppe
      const el = mkHauteurEl(`Règle : ${hRegle} m`, C_ZONE)
      labels.current.push(new maplibregl.Marker({ element: el, anchor: 'bottom', offset: [-46, dyRegle] }).setLngLat(cParc).addTo(mapGl))
    }
    if (terrain3d && batiVisible && cParc && hBati > 0) {
      const el = mkHauteurEl(`Faîtage LiDAR sur la parcelle : ${hBati} m`, C_BATI)
      labels.current.push(new maplibregl.Marker({ element: el, anchor: 'bottom', offset: [46, -30] }).setLngLat(cParc).addTo(mapGl))
    }
    // RECETTE-OUTILS-2 (R13) — le cadrage est le SEUL propriétaire de la caméra du Gabarit (MapView ne
    // recentre plus en gabarit). En 3D on cadre AVEC l'inclinaison (pitch 55, bearing 0) — comme « Vue
    // par défaut » — sinon un fitBounds à plat suivi du pitch poussait la parcelle hors champ (écran
    // noir « très zoomé à côté »). En 2D, cadrage normal.
    // RECETTE-OUTILS-2 (R13) — le Gabarit est SEUL propriétaire de la caméra (MapView ne recentre plus
    // en gabarit, et pose un terrain PLAT). En 3D on cadre avec l'inclinaison (pitch 45, bearing 0),
    // comme « Vue par défaut ». Terrain plat → le centroïde tombe au centre de l'écran, donc un seul
    // fitBounds suffit (plus de course avec le chargement du relief, plus d'écran noir sur pente forte).
    const bb = bboxOf(res.contourGeoJSON ?? res.zoneImplantationGeoJSON ?? null)
    if (bb) {
      const opts = terrain3d
        ? { padding: 70, bearing: 0, pitch: 45, duration: 600, maxZoom: 18 }
        : { padding: 80, duration: 600, maxZoom: 19 }
      try { m.fitBounds(bb, opts) } catch { /* noop */ }
    }
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
  const select = useApp((s) => s.select)   // RECETTE-1 F1/F3
  const terrain3d = useApp((s) => s.terrain3d)
  const setTerrain3d = useApp((s) => s.setTerrain3d)   // RETOURS-15 D4 — bascule 2D / 3D dans le panneau
  const batiVisible = useApp((s) => s.batiVisible)   // RETOURS-13 P4 — chip « Bâtiments » (session)
  const [idu, setIdu] = useState<string | null>(selectedIdu)
  const [source, setSource] = useState<SourceParcelle>(selectedIdu ? 'carte' : null)   // RECETTE-1 F2
  // OUTILS-REFONTE-1 (9b) — plus d'accordéons « Voir les règles »/« Non intégrées » (lignes + puces
  // toujours visibles), donc plus d'état d'ouverture.

  // RECETTE-1 (F1) — une parcelle désignée SUR LA CARTE (selectedIdu) est adoptée (source carte) ;
  // fermer la fiche de cette parcelle (selectedIdu → null) VIDE l'outil. Un pick dans le champ reste
  // autonome (source adresse). RECETTE-1 (H11) — quitter l'outil remet la vue en 2D (fond sombre).
  useEffect(() => {
    if (selectedIdu && selectedIdu !== idu) { setIdu(selectedIdu); setSource('carte') }
    else if (selectedIdu == null && source === 'carte') { setIdu(null); setSource(null) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIdu])
  useEffect(() => () => { setTerrain3d(false) }, [setTerrain3d])   // RECETTE-1 H11 — sortie → 2D
  const resetAll = () => {
    if (selectedIdu) select(null)
    setIdu(null); setSource(null); setTerrain3d(false)
  }

  const target = idu
  const q = useQuery({
    queryKey: ['gabarit', target],
    queryFn: () => getGabarit(target!),
    enabled: !!target, retry: false,
  })
  const res = q.data
  useMapLayers(res, terrain3d, batiVisible)
  // RECETTE-OUTILS-1 (point 34 / T6) — export PDF = le document « Gabarit » de Docs (même générateur).
  const { ouvrir, enCours } = useOuvrirDocument()
  // RECETTE-OUTILS-1 (point 33) — « Vue par défaut » : recentre sur la parcelle, orientation initiale
  // (bearing 0, pitch 55), même cadrage que l'entrée en 3D.
  const vueParDefaut = () => {
    const m = (window as unknown as { __labuse_map?: { fitBounds: (b: number[][], o?: unknown) => void; easeTo: (o: unknown) => void } }).__labuse_map
    if (!m) return
    const bb = bboxOf(res?.contourGeoJSON ?? res?.zoneImplantationGeoJSON ?? null)
    // R13 — même cadrage 3D que l'entrée (pitch 45, maxZoom 18) : cohérent et sûr sur pente forte.
    if (bb) m.fitBounds(bb, { padding: 70, bearing: 0, pitch: 45, duration: 600, maxZoom: 18 })
    else m.easeTo({ bearing: 0, pitch: 45, duration: 600 })
  }
  // RECETTE-OUTILS-3 (S11) — le bouton « Recentrer » (◎) du bloc de contrôle 3D de la carte demande au
  // Gabarit (propriétaire de la caméra) de reprendre la vue de départ : même recadrage que « Vue par
  // défaut », désormais déclenché par la carte.
  const recentrer3dNonce = useApp((s) => s.recentrer3dNonce)
  useEffect(() => { if (recentrer3dNonce && terrain3d) vueParDefaut() }, [recentrer3dNonce])   // eslint-disable-line react-hooks/exhaustive-deps

  // FIX-FINAL-1 (NU-D-027) — part de la parcelle en zone d'exclusion ; > 50 % ⇒ « majoritairement
  // inconstructible » : le gabarit tient sur une portion résiduelle (bandeau d'avertissement).
  // OUTILS-REFONTE-1 (9b) — la carte « Couverture · N familles vérifiées » est RETIRÉE (doublon des
  // règles appliquées). `familles`/`nbVerifiees`/`pprNonIntegre` ne sont donc plus calculés.
  const partExclue = res?.partExcluePct ?? null
  const exclusionMajoritaire = partExclue != null && partExclue > 50
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
  // FAISA-REGLES-1 (D-025) — la portion servie porte le nom de la zone CONSTRUCTIBLE (où le gabarit est
  // calculé), jamais la zone DOMINANTE (souvent A/N). Le back la sert dans `multizone.servie_sur` (ex.
  // « Ub (46.6 %) ») ; on en prend le code court, repli sur raccZone.code si absent.
  const multizone = (res?.raccordement?.multizone ?? null) as { servie_sur?: string } | null
  const zoneServieCode = (multizone?.servie_sur?.split(' ')[0]) || raccZone?.code
  // CHASSE-FIX-1 (C06) — zone AU non ouverte : bandeau « potentiel différé » servi par le back.
  const auDiffere = (res?.raccordement?.au_differe ?? null) as { libelle?: string } | null
  const cadastreM2 = parcelle?.surface_m2 ?? null
  const aCheval = !!raccZone?.a_cheval && cadastreM2 != null && res?.surfaceParcelleM2 != null
  // FRONT-CHIFFRES-2 (F50/F57) — % « à cheval » SERVI (pctPortionZone) ; ce ratio vivait à DEUX sites
  // front (ici + GabaritLine) → recalculé une seule fois au back, les deux le lisent (plus de divergence).
  const pctPortion = res?.pctPortionZone ?? null

  return (
    <div data-gabarit-panel className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      {/* RECETTE-2 (T3) — Réinitialiser SEUL sur sa ligne (haut-droite) ; l'intro vient EN DESSOUS,
          pleine largeur (plus côte à côte). Présent ssi une parcelle est désignée. */}
      {/* RETOURS-25 (pt 7) — phrase d'intro « Où et jusqu'où une construction peut s'implanter… » retirée. */}

      {/* RECETTE-1 (F2) — EntreeParcelle : adresse/IDU OU clic carte, l'une grise l'autre. */}
      <EntreeParcelle source={source} picked={target} onChanger={resetAll}
        onPick={(i, src) => { setSource(src); setIdu(i); focusParcelle(i) }} />

      {/* RECETTE-2 (D11) — section « Choisissez une parcelle (barre ci-dessus ou clic sur la carte) »
          retirée (l'entrée parcelle ci-dessus le dit déjà). */}

      {q.isLoading && <Squelette lignes={4} />}
      {q.isError && <ErrorState message="Parcelle inconnue ou service indisponible." retry={() => q.refetch()} />}

      {/* CHASSE-FIX-1 (C06) — l'enveloppe est calculée mais la zone AU n'est pas ouverte. */}
      {auDiffere && (
        <p className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-[11px] leading-snug text-amber-300">
          {auDiffere.libelle ?? 'Potentiel différé — ouverture de la zone requise'}
        </p>
      )}

      {/* FIX-FINAL-1 (NU-D-027) — majorité de la parcelle en zone d'exclusion (PPR rouge & autres) :
          l'enveloppe ne tient que sur la portion restante. Mise en garde explicite, jamais « risques ✓ ». */}
      {exclusionMajoritaire && (
        <p data-gabarit-exclusion-majoritaire
           className="rounded-lg border border-coral/50 bg-coral/10 px-3 py-2 text-[11px] leading-snug text-coral">
          Parcelle majoritairement inconstructible : {partExclue} % en zone d'exclusion (PPR zone rouge et autres
          interdictions). Le gabarit n'est calculé que sur la portion restante — à confirmer au règlement.
        </p>
      )}

      {/* NU5-FIX-1 (A-O1/O2) — INCONSTRUCTIBLE : verdict DÉFINITIF (habitat interdit, zone fermée A/N,
          AU non ouverte, terrain exigu, PPR rédhibitoire), lu via potentiel_batir — jamais une
          enveloppe géométrique, jamais « le calcul reprendra… ». Contour tracé, motif affiché. */}
      {res && res.status === 'inconstructible' && (
        <div data-gabarit-inconstructible className="flex flex-col gap-1.5 rounded-lg border border-coral/50 bg-coral/10 px-3 py-2.5">
          {(parcelle?.idu || parcelle?.commune) && (
            <p className="text-[11px] font-medium text-txt">
              Parcelle {parcelle?.idu ?? '—'}{parcelle?.commune ? ` · ${parcelle.commune}` : ''}
            </p>
          )}
          <p className="text-[12px] font-medium text-coral">Inconstructible — {res.message}</p>
          <p className="text-[10px] leading-snug text-txt-dim">
            Aucun gabarit d'implantation n'est calculé : le règlement n'autorise pas de construction
            ici. Le contour de la parcelle est tracé sur la carte.
          </p>
        </div>
      )}

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

      {/* RÉSULTAT COMPLET — OUTILS-REFONTE-1 (9b) : 4 tuiles · règles en lignes (libellé · valeur · badge
          zone) · « Non intégrées » en puces (remplace l'encadré jaune + accordéon) · Voir 3D / Export PDF.
          Les sections en double (Couverture, accordéon « Voir les règles ») disparaissent. La vue 3D et
          ses étiquettes de hauteur ne sont pas touchées (leur EXPLICATION reste en ligne discrète). */}
      {res && res.status === 'ok' && (() => {
        // valeur % d'emprise — LUE de la règle PLU appliquée (jamais recalculée ni inventée).
        const empriseRule = (res.appliedRules ?? []).find((r) => /emprise/i.test(r.label))
        const emprisePctRule = empriseRule?.unit === '%' && empriseRule.value != null ? empriseRule.value : null
        // badge d'une règle appliquée : la ZONE PLU servie (ex. « Uh ») — l'article n'est pas servi par
        // le moteur (source.article = null), on n'invente donc aucun numéro d'article. Les règles
        // géométriques (BD TOPO, zone absente) portent le badge « mesuré ».
        const ruleBadge = (r: typeof appliedOther[number]) =>
          r.source?.zone || (/BD ?TOPO/i.test(String(r.source?.document ?? '')) ? 'mesuré' : null)
        const regles = [...appliedSetbacks, ...appliedOther]
        return (
        <>
          {/* 4 tuiles : Zone d'implantation · Emprise maximale · Hauteur maximale · Surface parcelle.
              (La maquette montrait « Plancher maximal » ; le moteur Gabarit ne sert AUCUNE SDP/plancher
              → on n'invente pas, on garde la Surface parcelle réelle.) */}
          <div data-gabarit-chiffres className="grid grid-cols-2 gap-x-3 gap-y-2 rounded-lg border border-line-2 bg-surface-2 p-3">
            <Num label="Zone d'implantation" value={res.zoneImplantationM2} unit="m²" accent
              sub={res.batiDeduitM2 ? `après reculs · bâti déduit ${fmtInt(res.batiDeduitM2)} m²` : 'après reculs'} />
            <Num label="Emprise maximale" value={res.plafondEmpriseM2} unit="m²"
              statusLabel={res.plafondEmpriseStatus === 'absent' ? 'Non réglementé' : null}
              sub={res.plafondEmpriseStatus === 'absent' ? 'pas de règle d’emprise au sol'
                : emprisePctRule != null ? `${fmtInt(emprisePctRule)} % de la parcelle` : null} />
            <Num label="Hauteur maximale" value={res.hauteurReglementaireM} unit="m"
              statusLabel={res.hauteurStatus === 'not_integrated' ? 'Non chiffrée' : null}
              sub={res.hauteurStatus === 'not_integrated'
                ? 'prospect L ≥ H (non intégré)'
                : res.hauteurEgoutM != null ? `${String(res.hauteurEgoutM).replace('.', ',')} m à l’égout`
                : res.hauteurBase ? `au ${res.hauteurBase}` : null} />
            {aCheval
              ? <Num label="Surface parcelle" value={cadastreM2} unit="m²"
                  sub={`dont ${fmtInt(res.surfaceParcelleM2)} m² en ${zoneServieCode ?? 'zone constructible'} (${pctPortion} %)`} />
              : <Num label="Surface parcelle" value={res.surfaceParcelleM2} unit="m²" sub="cadastre" />}
          </div>

          {/* RÈGLES APPLIQUÉES — lignes « libellé · valeur · badge zone », toujours visibles (plus d'accordéon). */}
          <div data-gabarit-regles className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5">
            <p className="label-caps mb-1.5 text-[9.5px] text-txt-dim">Règles appliquées</p>
            <div className="flex flex-col">
              {regles.map((r, i) => {
                const badge = ruleBadge(r)
                return (
                  <div key={i} data-gabarit-regle className="flex items-baseline justify-between gap-2 border-b border-line py-1.5 last:border-0">
                    <span className="min-w-0 flex-1 text-[11px] text-txt">{r.label}</span>
                    {r.value != null
                      ? <span className="shrink-0 font-mono text-[11px] tabular-nums text-txt-hi">{r.value}{r.unit ? ` ${r.unit}` : ''}</span>
                      : r.detail ? <span className="shrink-0 text-[10px] italic text-txt-dim">{r.detail}</span> : null}
                    {badge && <span className="shrink-0 rounded-full border border-mint/40 px-1.5 py-0.5 text-[9px] font-medium text-mint">{badge}</span>}
                  </div>
                )
              })}
            </div>
          </div>

          {/* NON INTÉGRÉES — en puces (remplace l'encadré jaune + son accordéon). Détail (pourquoi · source)
              dans le « i » de chaque puce, rien d'inventé (exactement res.nonIntegratedRules). */}
          {res.nonIntegratedRules.length > 0 && (
            <div data-gabarit-non-integrees className="flex flex-wrap items-center gap-1.5">
              <span className="text-[10.5px] text-txt-mut">Non intégrées :</span>
              {res.nonIntegratedRules.map((n, i) => (
                <Tip key={i} garder side="top"
                  tip={[n.detail, [n.source?.document, n.source?.zone].filter(Boolean).join(' — ')].filter(Boolean).join(' · ') || n.label}>
                  <span data-gabarit-non-integree role="button" tabIndex={0}
                    className="rounded-full border border-st-creuser/40 bg-st-creuser/5 px-2.5 py-0.5 text-[10.5px] text-st-creuser">{n.label}</span>
                </Tip>
              ))}
            </div>
          )}

          {/* Voir en 3D / Exporter en PDF */}
          <div className="grid grid-cols-2 gap-2">
            <Bouton niveau="secondaire" ton="vert" data-gabarit-3d
              onClick={() => setTerrain3d(!terrain3d)} className="w-full justify-center">
              {terrain3d ? 'Revenir en 2D' : 'Voir en 3D'}
            </Bouton>
            {target && res?.status === 'ok' && (
              <Bouton niveau="secondaire" ton="vert" data-gabarit-export
                disabled={enCours != null} onClick={() => ouvrir(docGabaritUrl(target), 'gabarit')} className="w-full justify-center">
                Exporter en PDF
              </Bouton>
            )}
          </div>

          {/* Référence discrète en bas : rappel « enveloppe = maximum » + CALCUL ET ÉCHANTILLON du « ~½ »
              (RETOURS-27 pt 3 : traçable → on le donne dans le « i »). */}
          <p data-gabarit-plafond className="flex flex-wrap items-center gap-1 text-[10px] leading-snug text-txt-dim">
            <span>{CAPACITE_MAX_MENTION_COURTE}</span>
            <Tip garder side="top" tip="Médiane du ratio « autorisé / maximum réglementaire » : 0,46 en surface de plancher (0,40 en logements), mesurée sur 6 601 permis réellement autorisés après l'entrée en vigueur du PLU (Sit@del).">
              <span role="button" tabIndex={0} aria-label="Calcul et échantillon du ~½"
                className="flex h-[13px] w-[13px] shrink-0 items-center justify-center rounded-full border border-line-2 text-[8px] font-bold leading-none text-txt-dim hover:border-mint hover:text-mint">i</span>
            </Tip>
          </p>
          {/* RETOURS-27 (pt 3, correction) — explication NEUTRE : le faîtage LiDAR est une valeur de
              PARCELLE, non rattachée à un bâtiment précis ; AUCUNE phrase « dépasse la règle ». */}
          {terrain3d && res.hauteurReglementaireM != null && (
            <p data-gabarit-3d-hauteurs className="text-[10px] leading-snug text-txt-dim">
              Sur la vue 3D : l'<b className="text-mint">enveloppe (règle)</b> en volume, et le <b className="text-txt-mut">faîtage LiDAR</b> le plus haut mesuré sur la parcelle — une valeur de parcelle, non rattachée à un bâtiment précis (la mesure peut provenir d'un bâtiment voisin au contact).
            </p>
          )}
        </>
        )
      })()}
    </div>
  )
}
