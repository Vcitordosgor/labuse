import { useQuery } from '@tanstack/react-query'
import maplibregl from 'maplibre-gl'
import { useEffect, useRef, useState } from 'react'
import { getParcelGeojson, getParcelsGeojson, getParcellaireEpoque, parcelAt } from '../../lib/api'
import { useApp } from '../../store/useApp'
import { BASEMAP_SOURCES, basemapLabel, TEMPS_MILLESIMES, type BasemapDef } from '../map/basemaps'
import { Chip } from '../ui/Chip'
// RETOURS-15 C2 — la frise du bas (ventes/permis/propriétaire/découpe) est retirée : HistoireFrise n'est
// plus rendue par le comparateur.

const SP_BOUNDS: [number, number, number, number] = [55.21, -21.14, 55.35, -20.97]

// Comparateur générique : les deux fonds sont choisis (défaut 1950 ↔ aujourd'hui, l'usage « 1950 »).

/** Carte nue (fond sombre) — le fond de plan est posé/échangé ensuite par applyBasemap. */
function mkMap(el: HTMLDivElement) {
  return new maplibregl.Map({
    container: el,
    style: {
      version: 8, sources: {},
      layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#060A08' } }],
    },
    bounds: SP_BOUNDS, fitBoundsOptions: { padding: 40 }, attributionControl: false,
  })
}

/** Pose/échange le fond de plan SUR PLACE (même instance → caméra, synchro et parcelles préservées).
 *  Le raster 'bm' est réinséré SOUS la couche parcelles 'p' pour que le contour reste au-dessus. */
function applyBasemap(m: maplibregl.Map, def: BasemapDef) {
  const add = () => {
    if (m.getLayer('bm')) m.removeLayer('bm')
    if (m.getSource('bm')) m.removeSource('bm')
    m.addSource('bm', { type: 'raster', tiles: def.tiles, tileSize: 256, attribution: def.attribution, maxzoom: def.maxzoom ?? 19 })
    // RETOURS-15 C2 — le raster ortho reste SOUS le parcellaire (contours au-dessus), puis sous 'p'.
    const below = m.getLayer('parcellaire') ? 'parcellaire' : m.getLayer('p') ? 'p' : undefined
    m.addLayer({ id: 'bm', type: 'raster', source: 'bm' }, below)
  }
  if (m.isStyleLoaded()) add()
  else m.once('load', add)
}

function muteTileErrors(m: maplibregl.Map) {
  m.on('error', (e) => {
    const msg = String((e as { error?: Error }).error?.message ?? '')
    if (/AJAXError|40[04]/.test(msg)) return
    console.error(e.error ?? e)
  })
}

/** M08 / point 24 — comparateur SWIPE de fonds de plan : deux cartes superposées, celle de droite
 *  rognée par la poignée (clip-path). Caméras synchronisées dans les deux sens (garde anti-boucle).
 *  Défaut = 1950 ↔ aujourd'hui (l'usage historique « 1950 ») ; les deux fonds sont maintenant
 *  librement choisis. Parcelles promues affichées des deux côtés. */
export function TimeMachine({ center }: { center?: [number, number] | null }) {
  const leftRef = useRef<HTMLDivElement>(null)
  const rightRef = useRef<HTMLDivElement>(null)
  const maps = useRef<[maplibregl.Map, maplibregl.Map] | null>(null)
  const [split, setSplit] = useState(50)
  // M15 D1 : les DEUX fonds sont pilotés depuis le BANDEAU GAUCHE (M08) via le store — plus de
  // barre de contrôle en surimpression sur la carte. Seule la poignée de glissement reste sur la carte.
  const leftKey = useApp((s) => s.cmpLeft)
  const rightKey = useApp((s) => s.cmpRight)
  // TEMPS (refonte) — la parcelle DÉSIGNÉE (M08), épinglée sur LES DEUX fonds (contour mint appuyé),
  // pour ne jamais la perdre en glissant la poignée. Son contour ignore le filtre de statut de 'p'.
  const pinIdu = useApp((s) => s.tempsPinIdu)
  const dragging = useRef(false)
  const commune = useApp((s) => s.commune)
  const labelMarkers = useRef<maplibregl.Marker[]>([])
  // RECETTE-9 T6 — le contour BLANC (W13) ne s'affichait JAMAIS depuis la fiche : la source `cible`
  // restait à 0 feature (prouvé : geojson 200, source présente, mais setData jamais appliqué). Cause :
  // course entre la (re)création des cartes en StrictMode et l'effet qui pose la géométrie — quand la
  // donnée arrive avant que la source de la NOUVELLE carte soit ajoutée, le `setData` tombe dans le vide
  // et rien ne le rejoue. On garde la FC voulue dans un ref, réappliquée À LA FOIS quand la donnée
  // change ET quand une carte (re)charge et (re)crée la source — plus de course possible.
  const cibleFC = useRef<{ type: 'FeatureCollection'; features: unknown[] }>({ type: 'FeatureCollection', features: [] })
  // REMONTER-TEMPS-2 Lot B — « Parcellaire de l'époque » (off par défaut) : superpose sur la vue AVANT
  // le contour de la parcelle MÈRE d'origine (cadastre_historique, parcelles disparues). Disponible
  // seulement quand la période « avant » atteint 2017 (début de l'ingestion cadastre). Cadastre plein
  // écran NON servi (choix RT-2 : version minimale — l'ancien contour de CETTE parcelle, sinon message).
  const [cadastreOn, setCadastreOn] = useState(false)
  const periodAn = leftKey === 'bm-ortho-now'
    ? 9999
    : Number(TEMPS_MILLESIMES.find((m) => m.key === leftKey)?.an ?? 0)
  const cadastreDispo = periodAn >= 2016   // 2016-2020 recouvre déjà 2017 (1er millésime cadastre)
  const cadEpoque = useQuery({
    queryKey: ['cad-epoque', pinIdu],
    queryFn: () => getParcellaireEpoque(pinIdu!),
    enabled: !!pinIdu && cadastreOn && cadastreDispo, retry: false,
  })
  const cadFC = useRef<{ type: 'FeatureCollection'; features: unknown[] }>({ type: 'FeatureCollection', features: [] })
  // mode île : pas de GeoJSON (431k features) — le comparateur reste utilisable sans la
  // surcouche parcelles (l'ortho historique est l'objet de l'outil)
  const geo = useQuery({ queryKey: ['geojson', commune], queryFn: getParcelsGeojson, enabled: commune != null })
  // O2-4 (OUTILS-2) — géométrie de LA parcelle désignée, chargée SEULE (indépendante de la commune) :
  // c'est elle qui garantit le contour sur les deux volets même en mode île (l'ancienne épingle
  // dépendait du GeoJSON commune, jamais chargé sans commune → parcelle invisible, tout l'objet raté).
  const cible = useQuery({ queryKey: ['temps-cible', pinIdu], queryFn: () => getParcelGeojson(pinIdu!), enabled: !!pinIdu, retry: false })

  useEffect(() => {
    if (!leftRef.current || !rightRef.current || maps.current) return
    const past = mkMap(leftRef.current)
    const now = mkMap(rightRef.current)
    maps.current = [past, now]
    muteTileErrors(past)
    muteTileErrors(now)
    ;(window as unknown as Record<string, unknown>).__labuse_tm = { past, now } // hook QA (synchro)
    let lock = false
    const sync = (src: maplibregl.Map, dst: maplibregl.Map) => () => {
      if (lock) return
      lock = true
      dst.jumpTo({ center: src.getCenter(), zoom: src.getZoom(), bearing: src.getBearing(), pitch: src.getPitch() })
      lock = false
    }
    past.on('move', sync(past, now))
    now.on('move', sync(now, past))
    // M82 (refonte) — CLIC CARTE = désigner la parcelle : parcelAt(point)→idu→parcelPrefill (motif
    // M-ENTREE, pas un nouveau mécanisme). Le bandeau M08 consomme parcelPrefill et recentre.
    const onPick = (e: maplibregl.MapMouseEvent) => {
      parcelAt(e.lngLat.lng, e.lngLat.lat).then((r) => { if (r.idu) useApp.getState().setParcelPrefill(r.idu) }).catch(() => {})
    }
    past.on('click', onPick); now.on('click', onPick)
    const addParcels = (m: maplibregl.Map) => m.on('load', () => {
      // RETOURS-15 C2 — LE PARCELLAIRE ET SES CONTOURS comme dans la vue Ortho de l'accueil : mêmes
      // tuiles vectorielles (`parcels-ile`, /map/tiles), même contour discret sur l'ortho. Rendu sous
      // le contour blanc de la parcelle étudiée. Fonctionne sans commune (tuiles île, pas de GeoJSON).
      m.addSource('parcels-ile', { type: 'vector', minzoom: 9, maxzoom: 15,
        tiles: [`${window.location.origin}/map/tiles/{z}/{x}/{y}.pbf`] })
      m.addLayer({ id: 'parcellaire', type: 'line', source: 'parcels-ile', 'source-layer': 'parcels',
        paint: { 'line-color': '#ECF5EF', 'line-width': 0.5, 'line-opacity': 0.4 } })
      m.addSource('p', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } as never })
      m.addLayer({ id: 'p', type: 'line', source: 'p',
        filter: ['in', ['get', 'status'], ['literal', ['chaude', 'a_surveiller', 'a_creuser']]],
        paint: { 'line-color': '#5CE6A1', 'line-width': 1 } })
      // O2-4 — CONTOUR de la parcelle désignée : source DÉDIÉE `cible` (une seule feature, chargée par
      // IDU), indépendante du GeoJSON commune. Casing sombre (halo léger, lisible sur l'ortho claire de
      // 1950) + trait BLANC appuyé.
      // RECETTE-8 W13 (B5) — le contour de la parcelle est BLANC (#ECF5EF), pas vert : sur les deux
      // fonds d'époque (ortho claire ancienne ET récente), un trait blanc à casing sombre reste
      // lisible des DEUX côtés du curseur, là où le vert se noyait dans la végétation. Il est tracé
      // une fois sur la carte partagée → présent sur les deux volets du swipe.
      m.addSource('cible', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } as never })
      m.addLayer({ id: 'cible-casing', type: 'line', source: 'cible',
        paint: { 'line-color': '#06110B', 'line-width': 5, 'line-opacity': 0.85, 'line-blur': 0.5 } })
      m.addLayer({ id: 'cible', type: 'line', source: 'cible',
        paint: { 'line-color': '#ECF5EF', 'line-width': 2.5 } })
      // RECETTE-9 T6 — dès que la source existe (y compris après un remount StrictMode), on lui pose la
      // géométrie DÉJÀ connue (ref) : le contour survit à la course donnée↔carte.
      ;(m.getSource('cible') as maplibregl.GeoJSONSource | undefined)?.setData(cibleFC.current as never)
      // Lot B — parcellaire d'époque (contour de la mère d'origine) : trait AMBRE fin en tirets, sous
      // le contour blanc de la parcelle courante. Vide tant que le chip est off ; posé depuis un ref
      // (même parade à la course donnée↔carte que `cible`). Tracé sur les deux volets ; ne porte de
      // donnée que sur le volet AVANT (setData ciblé), pour rester « sur la vue avant ».
      m.addSource('cad-epoque', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } as never })
      m.addLayer({ id: 'cad-epoque', type: 'line', source: 'cad-epoque',
        paint: { 'line-color': '#E0A94F', 'line-width': 1.4, 'line-dasharray': [3, 2], 'line-opacity': 0.9 } },
        m.getLayer('cible-casing') ? 'cible-casing' : undefined)
      ;(m.getSource('cad-epoque') as maplibregl.GeoJSONSource | undefined)?.setData(cadFC.current as never)
    })
    addParcels(past); addParcels(now)
    if (center) { past.jumpTo({ center, zoom: 17 }) }
    return () => { past.remove(); now.remove(); maps.current = null }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // M82 (refonte) — recentrer sur la parcelle désignée après le montage (le bandeau M08 pose flyTo
  // → center change ; l'init ne s'exécute qu'une fois). jumpTo l'une → la synchro recadre l'autre.
  useEffect(() => {
    if (!center) return
    for (const m of maps.current ?? []) m.jumpTo({ center, zoom: 17 })
  }, [center])

  // Fond de gauche / de droite : posés au montage, ré-échangés sur place si le choix change.
  useEffect(() => {
    const m = maps.current?.[0]
    if (m && BASEMAP_SOURCES[leftKey]) applyBasemap(m, BASEMAP_SOURCES[leftKey])
  }, [leftKey])
  useEffect(() => {
    const m = maps.current?.[1]
    if (m && BASEMAP_SOURCES[rightKey]) applyBasemap(m, BASEMAP_SOURCES[rightKey])
  }, [rightKey])

  useEffect(() => {
    for (const m of maps.current ?? []) {
      if (geo.data && m.isStyleLoaded()) (m.getSource('p') as maplibregl.GeoJSONSource | undefined)?.setData(geo.data as never)
      else if (geo.data) m.once('load', () => (m.getSource('p') as maplibregl.GeoJSONSource | undefined)?.setData(geo.data as never))
    }
  }, [geo.data])

  // O2-4 — pose la géométrie de la parcelle désignée sur les DEUX volets (source `cible`), recentre la
  // vue dessus, et place une étiquette IDU (Marker HTML) qui traverse la poignée du comparateur. Vidée
  // proprement quand la parcelle change ou disparaît.
  useEffect(() => {
    const feat = cible.data
    const fc = { type: 'FeatureCollection' as const, features: feat ? [feat] : [] }
    cibleFC.current = fc          // RECETTE-9 T6 — mémorise la FC pour la (re)pose au (re)chargement des cartes
    for (const m of maps.current ?? []) {
      // applique si la source existe DÉJÀ ; sinon la pose se fera à l'ajout de la source (load handler,
      // qui lit `cibleFC.current`). Plus de `once('load')` qui manque le train quand load a déjà eu lieu.
      ;(m.getSource('cible') as maplibregl.GeoJSONSource | undefined)?.setData(fc as never)
    }
    // étiquette IDU — un seul Marker (sur le volet gauche, plein écran) : les deux cartes partageant la
    // même caméra, sa position écran vaut pour les deux. Le contour, lui, est tracé sur chaque volet.
    labelMarkers.current.forEach((mk) => mk.remove())
    labelMarkers.current = []
    const past = maps.current?.[0]
    if (feat && past) {
      const el = document.createElement('div')
      el.setAttribute('data-temps-idu', pinIdu ?? '')
      el.textContent = pinIdu ?? ''
      el.style.cssText = 'font:600 10px ui-monospace,Menlo,monospace;color:#4ADE80;background:rgba(6,17,11,.82);'
        + 'padding:2px 7px;border-radius:5px;letter-spacing:.06em;white-space:nowrap;pointer-events:none;transform:translateY(-8px)'
      // RETOURS-11 C9 (03/09) — l'étiquette IDU se pose AU-DESSUS DU CONTOUR (bord haut de la parcelle),
      // jamais dessus : ancre = [centroïde en X, latitude MAX de la géométrie en Y], ancrée par le bas.
      const centroid = feat.centroid as [number, number]
      let maxLat = -Infinity
      const walk = (a: unknown): void => {
        if (Array.isArray(a) && typeof a[0] === 'number') { if ((a[1] as number) > maxLat) maxLat = a[1] as number }
        else if (Array.isArray(a)) a.forEach(walk)
      }
      walk((feat.geometry as { coordinates?: unknown })?.coordinates ?? [])
      const ancre: [number, number] = Number.isFinite(maxLat) ? [centroid[0], maxLat] : centroid
      const mk = new maplibregl.Marker({ element: el, anchor: 'bottom' }).setLngLat(ancre).addTo(past)
      labelMarkers.current.push(mk)
    }
    if (feat) for (const m of maps.current ?? []) m.jumpTo({ center: feat.centroid as [number, number], zoom: 17 })
  }, [cible.data, pinIdu])

  // Lot B — pose le parcellaire d'époque (mère d'origine) sur le volet AVANT (carte gauche) uniquement,
  // et l'efface dès que le chip retombe / la période passe sous 2017 / la parcelle change. Le contour
  // n'est JAMAIS inventé : si la mère n'est pas captée, la FC reste vide (le message le dit à côté).
  useEffect(() => {
    const past = maps.current?.[0]
    const actif = cadastreOn && cadastreDispo && !!cadEpoque.data && cadEpoque.data.features.length > 0
    const fc = { type: 'FeatureCollection' as const, features: actif ? cadEpoque.data!.features : [] }
    cadFC.current = fc
    ;(past?.getSource('cad-epoque') as maplibregl.GeoJSONSource | undefined)?.setData(fc as never)
  }, [cadEpoque.data, cadastreOn, cadastreDispo, pinIdu])

  useEffect(() => {
    const t = setTimeout(() => maps.current?.forEach((m) => m.resize()), 60)
    return () => clearTimeout(t)
  }, [split])

  return (
    // OUTILS-MUSCLER-2 C1 — le comparateur (inchangé : mêmes curseurs, mêmes libellés) prend la
    // hauteur restante ; la FRISE DES FAITS se pose DESSOUS quand une parcelle est désignée.
    <div className="flex min-w-0 flex-1 flex-col">
    <div
      className="relative min-w-0 flex-1 select-none"
      onMouseMove={(e) => {
        if (!dragging.current) return
        const r = (e.currentTarget as HTMLElement).getBoundingClientRect()
        setSplit(Math.min(92, Math.max(8, ((e.clientX - r.left) / r.width) * 100)))
      }}
      onMouseUp={() => { dragging.current = false }}
      onMouseLeave={() => { dragging.current = false }}
    >
      {/* maplibre-gl.css (`.maplibregl-map{position:relative}`, chargée APRÈS l'app via le lazy-load
          M-V) écrase la classe Tailwind `.absolute` posée sur ces conteneurs → les deux cartes
          retombaient en FLUX NORMAL (empilées verticalement : « now » poussée hors écran sous
          « past »), si bien qu'on ne voyait QUE le fond de gauche (1950) sur toute la largeur — le
          comparateur montrait la MÊME image des deux côtés (bug M137). Correctif : `position`
          + `inset` en STYLE INLINE (spécificité > règle de classe) → les cartes se superposent
          bien, celle de droite rognée par la poignée. `h-full w-full` gardé pour la hauteur. */}
      <div ref={leftRef} className="h-full w-full" style={{ position: 'absolute', inset: 0 }} />
      <div ref={rightRef} className="h-full w-full" style={{ position: 'absolute', inset: 0, clipPath: `inset(0 0 0 ${split}%)` }} />
      {/* M15 D1 : la barre de contrôle « Comparer » (choix des deux fonds + Quitter) a été
          DÉPLACÉE dans le bandeau gauche (M08, ModulePanel). Seule la poignée reste sur la carte. */}
      {/* poignée */}
      <div className="absolute inset-y-0 z-10 w-[2px] bg-mint" style={{ left: `${split}%` }}>
        <button
          onMouseDown={() => { dragging.current = true }}
          className="absolute left-1/2 top-1/2 flex h-10 w-10 -translate-x-1/2 -translate-y-1/2 cursor-ew-resize items-center justify-center rounded-full border border-mint bg-[#0F1A14] text-mint"
          aria-label="Glisser pour comparer"
        >
          <span aria-hidden="true">⇔</span>
        </button>
      </div>
      <span className="absolute bottom-3 left-3 rounded-full border border-line-2 bg-surface-2 px-3 py-1 font-mono text-[11px] text-txt">{basemapLabel(leftKey)}</span>
      <span className="absolute bottom-3 right-3 rounded-full border border-line-2 bg-surface-2 px-3 py-1 font-mono text-[11px] text-txt">{basemapLabel(rightKey)}</span>
      {/* TEMPS (refonte) — LÉGENDE des zones noires : présente dès qu'un fond ortho ANCIEN est affiché
          (le seul cas où des dalles noires « limites de mission / mer » peuvent apparaître). Elle dit
          honnêtement que ce n'est pas un défaut de chargement — jamais un faux « RAS ». */}
      {leftKey !== 'bm-ortho-now' && (
        <div data-temps-legende className="absolute left-3 top-3 z-10 flex max-w-[19rem] items-start gap-2 rounded-lg border border-line-2 bg-surface-2/95 px-3 py-2">
          <span aria-hidden className="mt-0.5 h-3 w-3 shrink-0 rounded-[3px] border border-line-2 bg-black" />
          <span className="text-[10.5px] leading-snug text-txt-mut">
            <b className="text-txt">Zones noires</b> : secteurs non couverts par l'ortho ancienne (mer, limites
            de mission IGN) — ce n'est pas un défaut de chargement.
          </span>
        </div>
      )}
      {/* Lot B — chip « Parcellaire de l'époque » (haut-droite ; la légende des zones noires est à
          gauche). Off par défaut, grisé quand la période « avant » est < 2017. Millésime et état
          (contour trouvé / pas de parcellaire) dits sous le chip. Survol = rien (règle DA). */}
      {pinIdu && (
        <div className="absolute right-3 top-3 z-10 flex max-w-[17rem] flex-col items-end gap-1">
          <Chip data-temps-cadastre ton="ambre" on={cadastreOn && cadastreDispo} disabled={!cadastreDispo}
            onClick={() => setCadastreOn((v) => !v)}>Parcellaire de l'époque</Chip>
          {!cadastreDispo && (
            <span className="rounded bg-surface-2/95 px-2 py-0.5 text-right text-[9.5px] leading-snug text-txt-dim">
              parcellaire d'époque disponible à partir de 2017
            </span>
          )}
          {cadastreOn && cadastreDispo && cadEpoque.data && cadEpoque.data.features.length > 0 && (
            <span data-temps-cadastre-mil className="rounded bg-surface-2/95 px-2 py-0.5 text-right text-[9.5px] leading-snug text-amber">
              Cadastre d'époque {cadEpoque.data.millesime} — parcelle d'origine (contour ambre)
            </span>
          )}
          {cadastreOn && cadastreDispo && cadEpoque.data && cadEpoque.data.features.length === 0 && (
            <span data-temps-cadastre-vide className="rounded bg-surface-2/95 px-2 py-0.5 text-right text-[9.5px] leading-snug text-txt-mut">
              pas de parcellaire d'époque pour cette parcelle
            </span>
          )}
        </div>
      )}
    </div>
    </div>
  )
}
