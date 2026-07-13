import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useMemo, useRef, useState } from 'react'
import {
  createSegmentPreset, deleteSegmentPreset, exportPublipostage, exportSegmentCsv, getSegments, getStats,
  nlSegmentsSearch, querySegment, refreshSegmentCounts, updateSegmentPreset,
  type NlSegmentsRep, type SegmentFiltre, type SegmentFiltreDef, type SegmentPreset,
  type SegmentsHome,
} from '../../lib/api'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'

// ── Page SEGMENTS (mandat moteur-segments-habitat, Lot 5) ──
// Galerie de presets métiers groupés par catégorie (badge complet/partiel, compteur
// 24 h) → query builder pré-rempli (filtres grisés si source absente), carte + table
// paginée, export CSV « à l'occupant ». Admin (Vic) : CRUD, duplication, act./désact.

const CAT_ORDER = ['exterieur', 'renovation', 'energie', 'securite', 'foncier_bati']
const PAGE = 50

const fmtN = (n: number | null | undefined) =>
  n == null ? '—' : n.toLocaleString('fr-FR')

// libellé court d'un filtre de preset (chips de carte + lignes du builder)
function chipLabel(f: SegmentFiltre, defs: Map<string, SegmentFiltreDef>): string {
  if (f.ou) return f.ou.map((s) => chipLabel(s, defs)).join(' OU ')
  const d = f.cle ? defs.get(f.cle) : undefined
  const lib = d?.libelle ?? f.cle ?? '?'
  const u = d?.unite ? ` ${d.unite}` : ''
  if (f.min != null && f.max != null) return `${lib} ${f.min}–${f.max}${u}`
  if (f.min != null) return `${lib} ≥ ${f.min}${u}`
  if (f.max != null) return `${lib} ≤ ${f.max}${u}`
  if (f.values?.length) return `${lib} : ${f.values.join(', ')}`
  if (f.value === false) return `hors ${lib}`
  return lib
}

// ───────────────────────── carte des résultats (MapLibre, fond carto sombre) ─────────────────────────
function ResultMap({ geojson }: { geojson: { type: string; features: unknown[] } | null }) {
  const ref = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  useEffect(() => {
    if (!ref.current || mapRef.current) return
    const m = new maplibregl.Map({
      container: ref.current,
      style: {
        version: 8,
        sources: {
          carto: {
            type: 'raster',
            tiles: ['https://a.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png',
                    'https://b.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png'],
            tileSize: 256, attribution: '© OSM · CARTO',
          },
        },
        layers: [{ id: 'bm', type: 'raster', source: 'carto' }],
      },
      center: [55.53, -21.13], zoom: 8.6, attributionControl: false,
    })
    m.on('load', () => {
      m.addSource('seg', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      m.addLayer({
        id: 'seg-pts', type: 'circle', source: 'seg',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 8, 2.2, 14, 6],
          'circle-color': '#5CE6A1', 'circle-opacity': 0.75,
          'circle-stroke-color': '#06130C', 'circle-stroke-width': 0.6,
        },
      })
      mapRef.current = m
      setReady((r) => r + 1)
    })
    return () => { m.remove(); mapRef.current = null }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  const [ready, setReady] = useState(0)
  useEffect(() => {
    const m = mapRef.current
    if (!m || !geojson) return
    const src = m.getSource('seg') as maplibregl.GeoJSONSource | undefined
    if (!src) return
    src.setData(geojson as never)
    const feats = geojson.features as { geometry: { coordinates: [number, number] } }[]
    if (feats.length) {
      const b = new maplibregl.LngLatBounds()
      feats.forEach((f) => b.extend(f.geometry.coordinates))
      m.fitBounds(b, { padding: 40, maxZoom: 13, duration: 400 })
    }
  }, [geojson, ready])
  return <div ref={ref} data-seg-map className="h-full w-full rounded-[10px] border border-line-2" />
}

// Item 5 (UX V1) : plus jamais de −50 silencieusement traité comme 0 — hors domaine
// (négatif, ou min > max) → garde visuelle ambre ET critère non envoyé au serveur.
const rangeHorsDomaine = (f: SegmentFiltre) =>
  (f.min != null && f.min < 0) || (f.max != null && f.max < 0)
  || (f.min != null && f.max != null && f.min > f.max)

// ───────────────────────── éditeur d'UN filtre du builder ─────────────────────────
function FiltreRow({ f, defs, onChange, onRemove }: {
  f: SegmentFiltre
  defs: Map<string, SegmentFiltreDef>
  onChange: (nf: SegmentFiltre) => void
  onRemove: () => void
}) {
  if (f.ou) {
    return (
      <div data-seg-filtre className="rounded-lg border border-line-2 bg-surface-3 px-3 py-2">
        <div className="mb-1 flex items-center justify-between">
          <span className="font-mono text-[9.5px] uppercase tracking-widest text-txt-dim">l'un OU l'autre</span>
          <button onClick={onRemove} className="text-txt-dim hover:text-txt" title="Retirer">✕</button>
        </div>
        <div className="space-y-1.5">
          {f.ou.map((s, i) => (
            <FiltreRow key={s.cle ?? i} f={s} defs={defs}
              onChange={(ns) => onChange({ ...f, ou: f.ou!.map((x, j) => (j === i ? ns : x)) })}
              onRemove={() => {
                const rest = f.ou!.filter((_, j) => j !== i)
                onChange(rest.length ? { ...f, ou: rest } : { cle: undefined })
              }} />
          ))}
        </div>
      </div>
    )
  }
  const d = f.cle ? defs.get(f.cle) : undefined
  if (!d) return null
  const off = !d.disponible
  const num = (v: string) => (v === '' ? undefined : Number(v))
  return (
    <div data-seg-filtre data-seg-filtre-off={off ? '1' : undefined}
      className={`rounded-lg border px-3 py-2 ${off ? 'border-line-2 bg-surface-1 opacity-55' : 'border-line-2 bg-surface-3'}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="min-w-0 truncate text-[11.5px] font-medium text-txt" title={d.description}>
          {d.libelle}{d.unite ? <span className="ml-1 text-txt-dim">({d.unite})</span> : null}
        </span>
        <button onClick={onRemove} className="shrink-0 text-txt-dim hover:text-txt" title="Retirer ce filtre">✕</button>
      </div>
      {off ? (
        <p className="mt-1 text-[11px] italic text-txt-dim">
          disponible prochainement{d.mandat ? ` — mandat ${d.mandat}` : ''}
        </p>
      ) : d.type === 'range' ? (
        <>
          <div className="mt-1.5 flex items-center gap-2">
            <input type="number" min={0} placeholder="min" value={f.min ?? ''}
              onChange={(e) => onChange({ ...f, min: num(e.target.value) })}
              className={`w-24 rounded-md border bg-bg px-2 py-1 text-[11px] text-txt outline-none ${
                rangeHorsDomaine(f) ? 'border-[#E8B44C] focus:border-[#E8B44C]' : 'border-line-2 focus:border-mint'}`} />
            <span className="text-[11px] text-txt-dim">à</span>
            <input type="number" min={0} placeholder="max" value={f.max ?? ''}
              onChange={(e) => onChange({ ...f, max: num(e.target.value) })}
              className={`w-24 rounded-md border bg-bg px-2 py-1 text-[11px] text-txt outline-none ${
                rangeHorsDomaine(f) ? 'border-[#E8B44C] focus:border-[#E8B44C]' : 'border-line-2 focus:border-mint'}`} />
          </div>
          {rangeHorsDomaine(f) && (
            <p data-seg-garde className="mt-1 text-[11px] leading-snug text-[#E8B44C]">
              Valeurs hors domaine (≥ 0, min ≤ max) — critère ignoré tant qu'il n'est pas corrigé.
            </p>
          )}
        </>
      ) : d.type === 'bool' ? (
        <div className="mt-1.5 flex gap-1.5">
          {[{ v: true, l: 'oui' }, { v: false, l: 'non' }].map(({ v, l }) => (
            <button key={l} onClick={() => onChange({ ...f, value: v })}
              className={`rounded-md border px-2.5 py-0.5 text-[10.5px] ${
                (f.value ?? true) === v ? 'border-mint bg-mint/10 text-mint' : 'border-line-2 text-txt-dim hover:text-txt'}`}>
              {l}
            </button>
          ))}
        </div>
      ) : (
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {d.enum_values.map((v) => {
            const on = (f.values ?? []).includes(v)
            return (
              <button key={v}
                onClick={() => onChange({ ...f, values: on ? (f.values ?? []).filter((x) => x !== v) : [...(f.values ?? []), v] })}
                className={`rounded-md border px-2 py-0.5 text-[10.5px] ${
                  on ? 'border-mint bg-mint/10 text-mint' : 'border-line-2 text-txt-dim hover:text-txt'}`}>
                {v}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ───────────────────────── le query builder d'un preset ─────────────────────────
function Builder({ home, preset, onBack }: { home: SegmentsHome; preset: SegmentPreset; onBack: () => void }) {
  const defs = useMemo(() => new Map(home.filtres.map((f) => [f.cle, f])), [home.filtres])
  // BOOST CATNAT : quand une commune est sous arrêté récent, le filtre arrive PRÉ-COCHÉ
  // (décochable) sur les presets marqués — jamais seedé en dur (le segment tomberait à
  // zéro entre deux événements).
  const [filtres, setFiltres] = useState<SegmentFiltre[]>(() => {
    const base: SegmentFiltre[] = JSON.parse(JSON.stringify(preset.filtres ?? []))
    if (preset.boost_catnat && home.catnat.communes.length > 0
        && !base.some((f) => f.cle === 'catnat_recent')) {
      base.push({ cle: 'catnat_recent', value: true, optionnel: true })
    }
    return base
  })
  const [tri, setTri] = useState<string | null>(preset.tri_defaut)
  const [offset, setOffset] = useState(0)
  const [ajout, setAjout] = useState('')
  const { setToast } = useApp()
  const qc = useQueryClient()

  // un filtre en cours de saisie (range sans borne, énum sans valeur) n'est pas envoyé —
  // ni un range HORS DOMAINE (item 5 UX V1 : la garde visuelle l'annonce, rien ne part muet)
  const complet = (f: SegmentFiltre): boolean => {
    if (f.ou) return f.ou.some(complet)
    const d = f.cle ? defs.get(f.cle) : undefined
    if (!d) return false
    if (d.type === 'range') return (f.min != null || f.max != null) && !rangeHorsDomaine(f)
    if (d.type === 'enum') return (f.values?.length ?? 0) > 0
    return true
  }
  const effectifs = useMemo(
    () => filtres.map((f) => (f.ou ? { ...f, ou: f.ou.filter(complet) } : f)).filter(complet),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [filtres, defs])
  const body = { slug: preset.slug, filtres: effectifs, tri, limit: PAGE, offset, geojson: true }
  const rq = useQuery({
    queryKey: ['segments-query', preset.slug, effectifs, tri, offset],
    queryFn: () => querySegment(body),
    placeholderData: (prev) => prev,
  })
  const exp = useMutation({
    mutationFn: () => exportSegmentCsv({ slug: preset.slug, filtres: effectifs, tri }, `${preset.slug}_occupants.csv`),
    onSuccess: () => setToast('Export CSV téléchargé — adresses « à l\'occupant », aucune donnée nominative.'),
    onError: () => setToast("L'export a échoué — réessayer."),
  })
  const pub = useMutation({
    mutationFn: () => exportPublipostage({ slug: preset.slug, filtres: effectifs, tri },
      `${preset.slug || 'recherche'}_publipostage.zip`),
    onSuccess: () => setToast('Publipostage téléchargé : CSV normalisé + étiquettes + gabarit de lettre.'),
    onError: (e) => setToast('Publipostage : ' + (e as Error).message),
  })
  // admin : enregistrer les filtres modifiés comme NOUVEAU preset (un preset modifié
  // à la volée ne s'enregistre jamais sur place — doctrine du mandat)
  const dup = useMutation({
    mutationFn: () => {
      const slug = prompt('Slug de la nouvelle vue (minuscules-et-tirets) :', `${preset.slug}-v2`)
      if (!slug) return Promise.reject(new Error('annulé'))
      const nom = prompt('Nom affiché :', `${preset.nom} (variante)`) ?? slug
      return createSegmentPreset({ slug, nom, categorie: preset.categorie, copie_de: preset.slug, filtres: effectifs, tri_defaut: tri })
    },
    onSuccess: (p) => { setToast(`Vue « ${p.nom} » enregistrée.`); qc.invalidateQueries({ queryKey: ['segments'] }) },
    onError: (e) => { if ((e as Error).message !== 'annulé') setToast('Enregistrement refusé : ' + (e as Error).message) },
  })

  const rep = rq.data
  const cols = rep?.colonnes ?? []
  const catnatOn = preset.boost_catnat && home.catnat.communes.length > 0
  const dejaLa = new Set(filtres.flatMap((f) => (f.ou ? f.ou.map((s) => s.cle!) : [f.cle!])))
  // Item 6 (UX V1, mobile) : sous 640 px la colonne filtres fixe 320 px rendait la table
  // inutilisable → onglets « Filtres / Résultats » (la galerie, elle, passe très bien).
  const [ongletMobile, setOngletMobile] = useState<'filtres' | 'resultats'>('resultats')

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col sm:flex-row">
      {/* onglets mobile < 640 px */}
      <div data-seg-onglets className="flex shrink-0 items-center gap-1.5 border-b border-line px-3 py-2 sm:hidden">
        <button onClick={onBack} className="mr-1 px-1 text-sm text-txt-dim hover:text-txt" title="Toutes les vues">←</button>
        {([['filtres', 'Filtres'], ['resultats', `Résultats${rep?.count != null ? ` (${fmtN(rep.count)})` : ''}`]] as const).map(([k, l]) => (
          <button key={k} data-seg-onglet={k} onClick={() => setOngletMobile(k)}
            className={`rounded-full border px-3 py-1 text-[11px] font-medium ${
              ongletMobile === k ? 'border-mint bg-mint/10 text-mint' : 'border-line-2 text-txt-mut'}`}>
            {l}
          </button>
        ))}
      </div>
      {/* colonne filtres */}
      <aside className={`${ongletMobile === 'filtres' ? 'flex' : 'hidden'} min-h-0 w-full flex-1 flex-col border-r border-line bg-surface-1 sm:flex sm:w-[320px] sm:flex-none sm:shrink-0`}>
        <div className="shrink-0 px-4 pb-2 pt-4">
          <button data-seg-retour onClick={onBack} className="text-[11px] text-txt-dim hover:text-txt">← Toutes les vues</button>
          <h2 className="mt-1 text-sm font-medium text-txt-hi">{preset.nom}</h2>
          {preset.argumentaire && <p className="mt-1 text-[10.5px] leading-snug text-txt-dim">{preset.argumentaire}</p>}
          {preset.mention_legale && (
            <div data-seg-mention className="mt-1.5 rounded-md border border-line-2 bg-surface-3 px-2 py-1.5 text-[11px] leading-snug text-txt-dim">
              <p>{preset.mention_legale.texte}</p>
              <p className="mt-1">
                {preset.mention_legale.liens.map((l, i) => (
                  <a key={l.url} href={l.url} target="_blank" rel="noreferrer" className="text-mint hover:underline">
                    {i > 0 ? ' · ' : ''}{l.texte}
                  </a>
                ))}
              </p>
              <p className="mt-1 text-[11px] text-txt-dim/80">{preset.mention_legale.sources_donnees}</p>
            </div>
          )}
          {(dejaLa.has('emprise_residuelle_m2') || dejaLa.has('surelevation_possible')) && (
            <p className="mt-1.5 rounded-md border border-[#E8B44C]/30 bg-[#E8B44C]/5 px-2 py-1 text-[11px] leading-snug text-[#E8B44C]">
              {home.libelle_residuel}
            </p>
          )}
        </div>
        <div className="min-h-0 flex-1 space-y-1.5 overflow-y-auto px-4 pb-3">
          {filtres.map((f, i) => (
            <FiltreRow key={(f.cle ?? 'ou') + i} f={f} defs={defs}
              onChange={(nf) => { setFiltres(filtres.map((x, j) => (j === i ? nf : x))); setOffset(0) }}
              onRemove={() => { setFiltres(filtres.filter((_, j) => j !== i)); setOffset(0) }} />
          ))}
          <select data-seg-ajout value={ajout}
            onChange={(e) => {
              const cle = e.target.value
              if (!cle) return
              const d = defs.get(cle)!
              setFiltres([...filtres, d.type === 'bool' ? { cle, value: true } : d.type === 'enum' ? { cle, values: [] } : { cle }])
              setAjout(''); setOffset(0)
            }}
            className="mt-1 w-full rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 text-[11px] text-txt-dim outline-none focus:border-mint">
            <option value="">+ Ajouter un filtre…</option>
            {home.filtres.filter((d) => !dejaLa.has(d.cle)).map((d) => (
              <option key={d.cle} value={d.cle} disabled={!d.disponible}>
                {d.groupe} · {d.libelle}{d.disponible ? '' : ` — prochainement (${d.mandat ?? 'à venir'})`}
              </option>
            ))}
          </select>
        </div>
        <div className="shrink-0 border-t border-line px-4 py-3">
          <div className="mb-2 flex items-center gap-2">
            <label className="text-[11px] text-txt-dim">Tri</label>
            <select value={tri ?? ''} onChange={(e) => { setTri(e.target.value || null); setOffset(0) }}
              className="min-w-0 flex-1 rounded-md border border-line-2 bg-surface-3 px-2 py-1 text-[10.5px] text-txt outline-none focus:border-mint">
              {home.tris.map((t) => <option key={t.cle} value={t.cle}>{t.libelle}</option>)}
            </select>
          </div>
          <div className="flex gap-2">
            <button data-seg-export onClick={() => exp.mutate()} disabled={exp.isPending || !rep?.count}
              className="flex-1 rounded-lg bg-mint px-3 py-1.5 text-[11px] font-semibold text-[#06130C] hover:brightness-110 disabled:opacity-40">
              {exp.isPending ? 'Export…' : 'Exporter CSV (occupant)'}
            </button>
            <button data-seg-dupliquer onClick={() => dup.mutate()} title="Admin : enregistrer ces filtres comme nouveau preset"
              className="rounded-lg border border-line-2 px-3 py-1.5 text-[11px] text-txt hover:border-mint">
              Enregistrer…
            </button>
          </div>
          {/* Lot 2A (wave-adresses) : publipostage = CSV « À l'occupant » + étiquettes + gabarit */}
          <div className="mt-2 flex items-center gap-2">
            <button data-seg-publipostage onClick={() => pub.mutate()} disabled={pub.isPending || !rep?.count}
              className="flex-1 rounded-lg border border-mint/50 bg-mint/10 px-3 py-1.5 text-[11px] font-medium text-mint hover:bg-mint/20 disabled:opacity-40"
              title="ZIP : CSV normalisé (À l'occupant, adresse BAN), planches d'étiquettes 63,5×38,1, gabarit de lettre du métier">
              {pub.isPending ? 'Préparation…' : 'Publipostage (CSV + étiquettes)'}
            </button>
          </div>
        </div>
      </aside>

      {/* résultats : compteur + carte + table */}
      <div className={`${ongletMobile === 'resultats' ? 'flex' : 'hidden'} min-h-0 min-w-0 flex-1 flex-col overflow-hidden p-4 sm:flex`}>
        {catnatOn && (
          <div data-seg-catnat className="mb-3 rounded-lg border border-[#E8695A]/40 bg-[#E8695A]/10 px-3 py-2 text-[11px] text-[#f0a29a]">
            Communes récemment en état de catastrophe naturelle ({home.catnat.fenetre_mois} mois) :{' '}
            <span className="font-medium text-txt-hi">{home.catnat.communes.map((c) => c.commune).join(', ')}</span>
            {' '}— filtre CATNAT proposé pré-coché.
          </div>
        )}
        <div className="mb-3 flex items-baseline gap-3">
          <span data-seg-count className="font-display text-2xl font-bold text-mint">{fmtN(rep?.count)}</span>
          <span className="text-xs text-txt-dim">parcelles matchées{rq.isFetching ? ' · calcul…' : ''}</span>
          {!!rep?.filtres_inactifs?.length && (
            <span className="rounded-md border border-[#E8B44C]/40 bg-[#E8B44C]/10 px-2 py-0.5 text-[11px] text-[#E8B44C]"
              title={rep.filtres_inactifs.map((f) => `${f.libelle} — ${f.mandat ? `mandat ${f.mandat}` : f.raison ?? ''}`).join('\n')}>
              partiel : {rep.filtres_inactifs.length} filtre(s) en attente de données
            </span>
          )}
        </div>
        <div className="h-[38%] min-h-[180px] shrink-0">
          <ResultMap geojson={rep?.geojson ?? null} />
        </div>
        <div className="mt-3 min-h-0 flex-1 overflow-auto rounded-[10px] border border-line-2">
          <table className="w-full text-left text-[11px]">
            <thead className="sticky top-0 bg-surface-1">
              <tr className="text-[11px] uppercase tracking-wider text-txt-dim">
                <th className="px-3 py-2">Parcelle</th>
                <th className="px-3 py-2">Commune</th>
                <th className="px-3 py-2">Surface (m²)</th>
                {cols.filter((c) => c.cle !== 'surface_m2').map((c) => <th key={c.cle} className="px-3 py-2">{c.libelle}</th>)}
              </tr>
            </thead>
            <tbody>
              {(rep?.items ?? []).map((it) => (
                <tr key={String(it.idu)} data-seg-row className="border-t border-line-2 text-txt hover:bg-surface-3">
                  <td className="px-3 py-1.5 font-mono text-[10.5px] text-txt-hi">{String(it.idu)}</td>
                  <td className="px-3 py-1.5">{String(it.commune)}</td>
                  <td className="px-3 py-1.5">{fmtN(it.surface_m2 as number)}</td>
                  {cols.filter((c) => c.cle !== 'surface_m2').map((c) => {
                    const v = it[c.cle]
                    return <td key={c.cle} className="px-3 py-1.5">{v == null ? '—' : typeof v === 'boolean' ? (v ? 'oui' : 'non') : String(v)}</td>
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          {rep && rep.items.length === 0 && (
            <p className="px-3 py-6 text-center text-[11px] text-txt-dim">Aucune parcelle — élargir les filtres.</p>
          )}
        </div>
        <div className="mt-2 flex shrink-0 items-center justify-between text-[10.5px] text-txt-dim">
          <span>{fmtN(offset + 1)}–{fmtN(offset + (rep?.items.length ?? 0))} sur {fmtN(rep?.count)}</span>
          <div className="flex gap-1.5">
            <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}
              className="rounded-md border border-line-2 px-2.5 py-1 hover:border-mint disabled:opacity-30">← Précédent</button>
            <button disabled={!rep || offset + PAGE >= rep.count} onClick={() => setOffset(offset + PAGE)}
              className="rounded-md border border-line-2 px-2.5 py-1 hover:border-mint disabled:opacity-30">Suivant →</button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Ajout B (UX V1) : copy COMMERCIALE de la galerie — un picto par offre + une phrase de
// bénéfice client (zéro jargon filtre). La description filtre (argumentaire) passe en
// sous-texte. Le compteur du parc piscines est RÉEL (count du segment), jamais codé en dur.
const BENEFICE_PAR_SLUG: Record<string, (n: number | null) => string> = {
  'pergolas-terrasses': () => 'Les maisons avec du jardin nu à équiper — vos prochains chantiers d\'ombre et de terrasse.',
  'paysagistes': () => 'Grands jardins, végétation dense : les adresses où un paysagiste a du travail.',
  'piscinistes-construction': () => 'Du jardin, de la place, pas encore de bassin : vos prospects installation.',
  'parc-piscines-entretien': (n) => n != null
    ? `${n.toLocaleString('fr-FR')} piscines localisées sur l'île : entretien, rénovation, sécurité.`
    : 'Des piscines localisées sur l\'île : entretien, rénovation, sécurité.',
  'pv-residentiel': () => 'Toits bien exposés, factures élevées, pas de panneaux : le solaire qui a du sens.',
}
const PICTO_PAR_SLUG: Record<string, JSX.Element> = {
  // pergola : toile + deux montants
  'pergolas-terrasses': (
    <><path d="M3 7.5 Q10 4.5 17 7.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="5" y1="7" x2="5" y2="16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="15" y1="7" x2="15" y2="16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="3.5" y1="16" x2="16.5" y2="16" stroke="currentColor" strokeWidth="1.3" opacity="0.6" /></>
  ),
  // feuille
  'paysagistes': (
    <><path d="M10 16.5 C4.5 13 4.5 6.5 10 3.5 C15.5 6.5 15.5 13 10 16.5 Z" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <line x1="10" y1="6" x2="10" y2="16.5" stroke="currentColor" strokeWidth="1.2" opacity="0.6" /></>
  ),
  // bassin en creusement : vagues + truelle (trait plus)
  'piscinistes-construction': (
    <><path d="M3 13 Q5 11.5 7 13 T11 13 T15 13 T17 13" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="13.5" y1="3.5" x2="13.5" y2="8.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="11" y1="6" x2="16" y2="6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></>
  ),
  // eau : double vague
  'parc-piscines-entretien': (
    <><path d="M3 8.5 Q5 7 7 8.5 T11 8.5 T15 8.5 T17 8.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M3 13 Q5 11.5 7 13 T11 13 T15 13 T17 13" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.65" /></>
  ),
  // soleil + panneau
  'pv-residentiel': (
    <><circle cx="6.5" cy="6.5" r="2.6" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <line x1="6.5" y1="2" x2="6.5" y2="3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <line x1="2" y1="6.5" x2="3" y2="6.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <rect x="9.5" y="10" width="7.5" height="6" rx="0.8" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <line x1="13.25" y1="10" x2="13.25" y2="16" stroke="currentColor" strokeWidth="1.1" opacity="0.6" /></>
  ),
}
//: repli par catégorie pour les presets créés après coup (dupliqués, variantes admin)
const PICTO_PAR_CATEGORIE: Record<string, JSX.Element> = {
  exterieur: PICTO_PAR_SLUG['paysagistes'],
  renovation: (
    <><path d="M4 16 V8 L10 3.5 L16 8 V16 Z" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M8 16 V11 H12 V16" fill="none" stroke="currentColor" strokeWidth="1.3" /></>
  ),
  energie: (
    <path d="M11 3 L5.5 11 H9.5 L9 17 L14.5 9 H10.5 Z" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
  ),
  securite: (
    <path d="M10 3.5 L16 5.5 V10 C16 13.5 13.5 15.8 10 17 C6.5 15.8 4 13.5 4 10 V5.5 Z" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
  ),
  foncier_bati: (
    <><path d="M3.5 9 L10 3.5 L16.5 9" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5.5 8.5 V16 H14.5 V8.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" /></>
  ),
}

// ───────────────────────── carte d'un preset (galerie) ─────────────────────────
function PresetCard({ p, home, onOpen }: { p: SegmentPreset; home: SegmentsHome; onOpen: () => void }) {
  const defs = useMemo(() => new Map(home.filtres.map((f) => [f.cle, f])), [home.filtres])
  const qc = useQueryClient()
  const { setToast } = useApp()
  const toggle = useMutation({
    mutationFn: () => updateSegmentPreset(p.slug, { ...p, actif: !p.actif }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['segments'] }); setToast(p.actif ? 'Modèle désactivé.' : 'Modèle activé.') },
  })
  const dup = useMutation({
    mutationFn: () => {
      const slug = prompt('Slug de la copie :', `${p.slug}-copie`)
      if (!slug) return Promise.reject(new Error('annulé'))
      return createSegmentPreset({ slug, nom: `${p.nom} (copie)`, categorie: p.categorie, copie_de: p.slug })
    },
    onSuccess: (np) => { qc.invalidateQueries({ queryKey: ['segments'] }); setToast(`Modèle « ${np.nom} » créé.`) },
    onError: (e) => { if ((e as Error).message !== 'annulé') setToast('Duplication refusée : ' + (e as Error).message) },
  })
  const editArg = useMutation({
    mutationFn: () => {
      const argumentaire = prompt('Argumentaire commercial :', p.argumentaire ?? '')
      if (argumentaire == null) return Promise.reject(new Error('annulé'))
      return updateSegmentPreset(p.slug, { ...p, argumentaire })
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['segments'] }); setToast('Argumentaire mis à jour.') },
    onError: (e) => { if ((e as Error).message !== 'annulé') setToast('Édition refusée : ' + (e as Error).message) },
  })
  const suppr = useMutation({
    mutationFn: () => {
      if (!confirm(`Supprimer le modèle « ${p.nom} » ? (définitif)`)) return Promise.reject(new Error('annulé'))
      return deleteSegmentPreset(p.slug)
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['segments'] }); setToast('Modèle supprimé.') },
    onError: (e) => { if ((e as Error).message !== 'annulé') setToast('Suppression refusée : ' + (e as Error).message) },
  })
  const partiel = p.disponibilite === 'partiel'
  const catnatOn = p.boost_catnat && home.catnat.communes.length > 0
  return (
    <div data-seg-preset={p.slug} className={`rounded-xl border bg-surface-3 p-3.5 transition-colors ${
      p.actif ? 'border-line-2 hover:border-mint' : 'border-line-2 opacity-50'}`}>
      <button onClick={onOpen} className="block w-full text-left" data-seg-preset-open>
        <div className="flex items-start justify-between gap-2">
          <span className="flex min-w-0 items-center gap-2">
            {/* Ajout B (UX V1) : un picto par offre — l'artisan reconnaît son métier d'un œil */}
            <span data-seg-picto className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-mint/10 text-mint">
              <svg viewBox="0 0 20 20" className="h-[18px] w-[18px]">
                {PICTO_PAR_SLUG[p.slug] ?? PICTO_PAR_CATEGORIE[p.categorie] ?? PICTO_PAR_CATEGORIE.foncier_bati}
              </svg>
            </span>
            <span className="truncate text-[12.5px] font-medium text-txt-hi">{p.nom}</span>
          </span>
          <span data-seg-badge className={`shrink-0 rounded-md border px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wider ${
            partiel ? 'border-[#E8B44C]/40 bg-[#E8B44C]/10 text-[#E8B44C]' : 'border-mint/40 bg-mint/10 text-mint'}`}
            title={partiel ? p.filtres_inactifs.map((f) => `${f.libelle} — ${f.mandat ? `mandat ${f.mandat}` : f.raison ?? ''}`).join('\n') : 'toutes les sources de données sont disponibles'}>
            {partiel ? `partiel · ${p.filtres_inactifs.length}` : 'complet'}
          </span>
        </div>
        {/* Ajout B : LA phrase de bénéfice client — le pourquoi, pas le comment */}
        {BENEFICE_PAR_SLUG[p.slug] && (
          <p data-seg-benefice className="mt-1.5 text-xs leading-snug text-txt">
            {BENEFICE_PAR_SLUG[p.slug](p.count)}
          </p>
        )}
        <div className="mt-1 flex items-baseline gap-1.5">
          <span data-seg-preset-count className="font-display text-lg font-bold text-mint">{fmtN(p.count)}</span>
          <span className="text-[11px] text-txt-dim">parcelles</span>
          {/* Item 14 (UX V1) : le compteur est un cache 24 h — sa date évite la question
              quand le builder (calcul direct) diffère après un recalcul. */}
          {p.count != null && p.count_at && (
            <span data-seg-count-date className="text-[11px] text-txt-dim"
              title="Compteur recalculé au plus toutes les 24 h — le builder calcule en direct">
              · compteur du {new Date(p.count_at).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })} à{' '}
              {new Date(p.count_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
          {catnatOn && <span className="ml-auto rounded-md bg-[#E8695A]/15 px-1.5 py-0.5 text-[9px] font-medium text-[#f0a29a]">CATNAT actif</span>}
        </div>
        {/* la description filtre (argumentaire) passe en SOUS-TEXTE quand un bénéfice existe */}
        {p.argumentaire && (
          <p data-seg-argumentaire className={`mt-1.5 text-[10.5px] leading-snug text-txt-dim ${BENEFICE_PAR_SLUG[p.slug] ? 'opacity-80' : ''}`}>
            {p.argumentaire}
          </p>
        )}
        <div className="mt-2 flex flex-wrap gap-1">
          {(p.filtres ?? []).map((f, i) => (
            <span key={i} className="rounded-md border border-line-2 bg-surface-1 px-1.5 py-0.5 text-[11px] text-txt-mut">
              {chipLabel(f, defs)}
            </span>
          ))}
        </div>
      </button>
      {/* admin (Vic) : l'app est mono-utilisateur authentifié — ces actions écrivent en base */}
      <div className="mt-2.5 flex gap-2 border-t border-line-2 pt-2 text-[11px] text-txt-dim">
        <button data-seg-admin-dupliquer onClick={() => dup.mutate()} className="hover:text-txt">dupliquer</button>
        <button data-seg-admin-argumentaire onClick={() => editArg.mutate()} className="hover:text-txt">argumentaire</button>
        <button data-seg-admin-toggle onClick={() => toggle.mutate()} className="hover:text-txt">{p.actif ? 'désactiver' : 'activer'}</button>
        {p.created_by !== 'seed' && <button onClick={() => suppr.mutate()} className="hover:text-[#E8695A]">supprimer</button>}
      </div>
    </div>
  )
}

// ── barre de recherche NL (wave-adresses Lot 6) : question libre → filtres du registry,
//    ouverts dans le query builder STANDARD (visibles, modifiables — l'utilisateur voit
//    la « traduction » et corrige les erreurs du LLM). Hors périmètre → réponse honnête.
function BarreNL({ onFiltres }: { onFiltres: (filtres: SegmentFiltre[], explication: string) => void }) {
  const [q, setQ] = useState('')
  const [rep, setRep] = useState<NlSegmentsRep | null>(null)
  const chercher = useMutation({
    mutationFn: (text: string) => nlSegmentsSearch(text),
    onSuccess: (r) => {
      setRep(r)
      if (r.filtres?.length) onFiltres(r.filtres, r.explication ?? '')
    },
    onError: () => setRep({ stub: true, out_of_scope: 'recherche indisponible — réessayez' }),
  })
  return (
    <div data-seg-nl className="mb-4">
      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (q.trim()) chercher.mutate(q.trim()) }}>
        <input data-seg-nl-input value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="Décrivez votre cible : « villas mutées récemment avec grand jardin sans piscine au Tampon »"
          className="h-9 flex-1 rounded-lg border border-line-2 bg-surface-1 px-3 text-[12px] text-txt-hi placeholder:text-txt-dim focus:border-mint focus:outline-none" />
        <button type="submit" disabled={chercher.isPending || !q.trim()}
          className="rounded-lg border border-mint/50 bg-mint/10 px-4 text-[11.5px] font-medium text-mint hover:bg-mint/20 disabled:opacity-40">
          {chercher.isPending ? 'Traduction…' : 'Rechercher'}
        </button>
      </form>
      {rep?.out_of_scope && (
        <p data-seg-nl-oos className="mt-1.5 text-[11px] leading-snug text-[#E8B44C]">
          {rep.out_of_scope}{rep.message ? ` — ${rep.message}` : ''}
        </p>
      )}
      {!!rep?.filtres_rejetes?.length && (
        <p className="mt-1.5 text-[10.5px] text-txt-dim">
          Ignoré (hors registry) : {rep.filtres_rejetes.map((r) => r.raison).join(' · ')}
        </p>
      )}
      {!!rep?.filtres_gates?.length && (
        /* même mécanique que les presets : filtre réservé à un plan supérieur → grisé + CTA */
        <p data-seg-nl-upgrade className="mt-1.5 text-[10.5px] text-[#E8B44C]">
          {rep.filtres_gates.length} filtre(s) réservé(s) au plan Intégral —{' '}
          <span className="underline">passer au plan Intégral</span> pour les activer.
        </p>
      )}
    </div>
  )
}

// ───────────────────────── la page ─────────────────────────
export function SegmentsPage() {
  const [slug, setSlug] = useState<string | null>(null)
  const [nlPreset, setNlPreset] = useState<SegmentPreset | null>(null)
  const { setToast, setView, setVerdict } = useApp()
  // tuile Foncier : compteurs RÉELS du périmètre courant (SQL-exact, jamais codés en dur)
  const statsIle = useQuery({ queryKey: ['stats-vues'], queryFn: () => getStats() })
  const qc = useQueryClient()
  const { data: home, isLoading } = useQuery({ queryKey: ['segments'], queryFn: getSegments })
  const refresh = useMutation({
    mutationFn: refreshSegmentCounts,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['segments'] }); setToast('Compteurs recalculés.') },
  })
  if (isLoading || !home) return <div className="flex flex-1 items-center justify-center"><Loading /></div>
  if (nlPreset) return <Builder home={home} preset={nlPreset} onBack={() => setNlPreset(null)} />
  const sel = slug ? home.presets.find((p) => p.slug === slug) : null
  if (sel) return <Builder home={home} preset={sel} onBack={() => setSlug(null)} />

  return (
    <div data-seg-page className="flex min-w-0 flex-1 flex-col overflow-y-auto px-6 py-5">
      <div className="mb-4 flex items-baseline justify-between">
        <div>
          <h1 className="font-display text-lg font-bold text-txt-hi">Vues</h1>
          <p className="mt-0.5 max-w-2xl text-[11px] leading-snug text-txt-dim">
            Une vue = un ciblage sur le parc foncier de l'île, composable critère par critère,
            exportable et réutilisable. Les modèles ci-dessous sont des points de départ, pas des limites.
          </p>
        </div>
        <button onClick={() => refresh.mutate()} disabled={refresh.isPending}
          className="rounded-lg border border-line-2 px-3 py-1.5 text-[10.5px] text-txt-dim hover:border-mint hover:text-txt disabled:opacity-40">
          {refresh.isPending ? 'Recalcul…' : 'Recalculer les compteurs'}
        </button>
      </div>

      {/* ── HÉROS (décision produit 12/07) : le BUILDER d'abord — c'est l'écran qui faisait
          dire « outil pour piscinistes » : le ciblage libre passe devant les métiers. ── */}
      <section data-vues-hero className="mb-4 rounded-2xl border border-[#2E6B4F]/60 bg-[#0F1A14] p-5">
        <h2 className="font-display text-[15px] font-bold text-txt-hi">
          Composez votre ciblage sur {home.filtres.filter((f) => f.disponible).length} critères,
          ou décrivez-le en français
        </h2>
        <p className="mt-1 text-[11px] leading-snug text-txt-mut">
          Votre phrase devient des filtres visibles et modifiables dans le builder — jamais une boîte noire.
        </p>
        <div className="mt-3">
          <BarreNL onFiltres={(filtres, explication) => {
            setToast(explication || 'Filtres proposés par l\'IA — vérifiez-les dans le builder.')
            setNlPreset({
              slug: '', nom: 'Recherche IA (filtres à vérifier)', categorie: 'foncier_bati',
              description: null, argumentaire: null, filtres, colonnes_export: [],
              tri_defaut: null, boost_catnat: false, actif: true, ordre: 0, created_by: null,
              updated_at: null, disponibilite: 'complet', filtres_inactifs: [],
              count: null, count_at: null,
            })
          }} />
        </div>
        <button data-vues-builder-vierge
          onClick={() => setNlPreset({
            slug: '', nom: 'Nouvelle vue', categorie: 'foncier_bati',
            description: null, argumentaire: null, filtres: [], colonnes_export: [],
            tri_defaut: null, boost_catnat: false, actif: true, ordre: 0, created_by: null,
            updated_at: null, disponibilite: 'complet', filtres_inactifs: [],
            count: null, count_at: null,
          })}
          className="text-[11px] font-medium text-mint hover:underline">
          ou partez d'une vue vierge et composez critère par critère →
        </button>
      </section>

      {/* ── LA première vue : le cœur du produit — Foncier (brûlantes & chaudes v2) ── */}
      <button data-vue-fonciere
        onClick={() => { setVerdict(true); setView('cartes') }}
        className="mb-5 w-full rounded-2xl border border-mint/40 bg-surface-2 p-5 text-left transition-colors hover:border-mint">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
          <h2 className="font-display text-[15px] font-bold text-txt-hi">Foncier — Brûlantes & chaudes</h2>
          {statsIle.data && (
            <span className="font-mono text-[11px] text-txt-mut">
              <b style={{ color: '#E8695A' }}>{fmtN(statsIle.data.tiers.brulante)}</b> brûlantes ·{' '}
              <b style={{ color: '#E8B44C' }}>{fmtN(statsIle.data.tiers.chaude)}</b> chaudes
            </span>
          )}
        </div>
        <p className="mt-1 max-w-3xl text-xs leading-relaxed text-txt-mut">
          Les parcelles les plus susceptibles de muter à 12 mois (scoring v2) — chaque signal
          sourcé et daté.
        </p>
        <span className="mt-2 inline-block text-[11px] font-medium text-mint">
          Ouvrir sur la carte — liste triée par rang →
        </span>
      </button>

      {home.catnat.communes.length > 0 && (
        <div data-seg-catnat-bandeau className="mb-4 rounded-lg border border-[#E8695A]/40 bg-[#E8695A]/10 px-3 py-2 text-[11px] text-[#f0a29a]">
          Catastrophe naturelle ({home.catnat.fenetre_mois} derniers mois) :{' '}
          <span className="font-medium text-txt-hi">{home.catnat.communes.map((c) => c.commune).join(', ')}</span>
          {' '}— les vues couvreurs/menuiseries proposent le filtre pré-coché.
        </div>
      )}

      {/* ── les presets métiers deviennent des MODÈLES — secondaires, dupliquables ── */}
      <section data-vues-modeles>
        <p className="mb-2 font-mono text-[10.5px] font-medium uppercase tracking-widest text-txt-mut">
          Modèles — des exemples à dupliquer, pas des limites
        </p>
        <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2 xl:grid-cols-3">
          {[...home.presets]
            .sort((a, b) => (CAT_ORDER.indexOf(a.categorie) - CAT_ORDER.indexOf(b.categorie)) || (a.ordre - b.ordre))
            .map((p) => <PresetCard key={p.slug} p={p} home={home} onOpen={() => setSlug(p.slug)} />)}
        </div>
      </section>
    </div>
  )
}
