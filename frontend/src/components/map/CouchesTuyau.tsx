// COUCHES-TUYAU-1 lot 2 — le front du tuyau : UNE source vectorielle par couche, style depuis
// la déclaration (couleurs par grade en sous-calques via `niveaux`, légende, popup). Tout allumé
// dès la vue île (aucun bandeau d'attente, aucun « Zoomez »). Un échec de tuile est signalé sur la
// ligne de la couche, jamais muet. ADDITIF : ne touche à aucune couche existante.
import { useEffect, useMemo, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import { useQuery } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'

// ── types du plan servi par /map/tuyau/couches (dérivé de la déclaration) ──
export interface TuyauNiveau {
  id: string; propriete: string; valeur: string; couleur: string; legende: string
  opacite?: number; rayon?: number; geometrie?: string; epaisseur?: number
  tirets?: number[]; trait?: string; anneau?: boolean
}
export interface TuyauStyle {
  couleur?: string; opacite?: number; trait?: string; rayon?: number; epaisseur?: number
  couleurs?: Record<string, string>; couleur_propriete?: string; halo?: number
  tirets?: number[]; contour_seul?: boolean; zoom_rayon?: number[]; zoom_largeur?: number[]
  filtre?: { propriete: string; valeur: string }
}
export interface TuyauPopup { champ: string; libelle: string; lien?: boolean }
export interface TuyauCouche {
  kind: string; nom: string; famille: string; geometrie: string; zoom_min: number
  rang_carte: number; style: TuyauStyle; niveaux: TuyauNiveau[] | null
  popup: TuyauPopup[] | null; legende: string; statut_juridique: string | null; tuiles_url: string
  i?: string | null     // COUCHES-RECETTE-1 A8 : texte du « i » (déclaration, jamais un if kind===)
  subdivise?: boolean   // retour §2 : servie en morceaux ST_Subdivide → pas de contour de morceau
}

// COUCHES-RECETTE-1 A11 : ordre des catégories du panneau (Repères en tête ; « Fond de plan » n'y
// figure plus — le bâti 3D part dans le bouton 3D). Une famille hors liste tombe à la fin.
const ORDRE_FAMILLES = ['reperes', 'urbanisme', 'risques', 'environnement', 'foncier',
  'reseaux', 'transport', 'dispositifs', 'patrimoine', 'equipements', 'marche']
// COUCHES-RECETTE-1 A11 : le bâti 3D (extrusion) est retiré du panneau — activé par le bouton 3D.
const HORS_PANNEAU = (c: TuyauCouche) => c.geometrie === 'extrusion'
// COUCHES-RECETTE-1 A5 : seuls les Repères (limites communes/parcelles) sont cochés par défaut.
const COCHE_DEFAUT = (c: TuyauCouche) => c.famille === 'reperes'

const FALLBACK = '#8892a0'

async function chargerPlan(): Promise<TuyauCouche[]> {
  const r = await fetch('/map/tuyau/couches')
  if (!r.ok) throw new Error(`plan tuyau: ${r.status}`)
  const j = await r.json()
  return (j.couches ?? []) as TuyauCouche[]
}

export function useTuyauPlan() {
  return useQuery({ queryKey: ['tuyau-couches'], queryFn: chargerPlan, staleTime: 3_600_000 })
}

// ── expressions de style : la COULEUR vient de la déclaration (grades = sous-calques) ──
type Expr = maplibregl.ExpressionSpecification
function couleurExpr(c: TuyauCouche): string | Expr {
  const s = c.style || {}
  if (c.niveaux && c.niveaux.length) {
    const prop = c.niveaux[0].propriete
    const cas: unknown[] = ['match', ['get', prop]]
    for (const n of c.niveaux) cas.push(n.valeur, n.couleur)
    cas.push(s.couleur || FALLBACK)
    return cas as unknown as Expr
  }
  if (s.couleur_propriete && s.couleurs) {
    const cas: unknown[] = ['match', ['get', s.couleur_propriete]]
    for (const [k, v] of Object.entries(s.couleurs)) cas.push(k, v)
    cas.push(s.couleur || FALLBACK)
    return cas as unknown as Expr
  }
  return s.couleur || FALLBACK
}

function rampe(paires: number[] | undefined, defaut: number): number | Expr {
  if (!paires || paires.length < 4) return defaut
  return ['interpolate', ['linear'], ['zoom'], ...paires] as unknown as Expr
}

function dimensions(geo: string): Set<'poly' | 'line' | 'point'> {
  if (geo === 'point') return new Set(['point'])
  if (geo === 'ligne') return new Set(['line'])
  if (geo === 'polygone' || geo === 'extrusion') return new Set(['poly'])
  if (geo === 'point_et_polygone') return new Set(['poly', 'point'])
  return new Set(['poly', 'line', 'point'])  // inconnu / multi (tcsp)
}

// les calques MapLibre d'une couche (fond + contour + points selon la géométrie déclarée)
function calques(c: TuyauCouche): maplibregl.AddLayerObject[] {
  const src = `tuyau-${c.kind}`
  const sl = c.kind
  const s = c.style || {}
  const col = couleurExpr(c)
  const dims = dimensions(c.geometrie)
  const base = { source: src, 'source-layer': sl, layout: { visibility: 'none' as const } }
  const out: maplibregl.AddLayerObject[] = []
  if (dims.has('poly')) {
    if (!s.contour_seul) {
      out.push({ ...base, id: `${src}-fill`, type: 'fill',
        paint: { 'fill-color': col, 'fill-opacity': s.opacite ?? 0.4 } as never })
    }
    // retour §2 : une couche servie en MORCEAUX (ST_Subdivide) ne dessine PAS de contour de morceau
    // (les coutures internes apparaîtraient). Le bord visible = l'arête du remplissage = l'origine.
    if (!c.subdivise) {
      out.push({ ...base, id: `${src}-outline`, type: 'line',
        paint: { 'line-color': (s.trait || col) as never, 'line-width': s.epaisseur ?? 1, 'line-opacity': 0.9 } as never })
    }
  }
  if (dims.has('line')) {
    const paint: Record<string, unknown> = {
      'line-color': col, 'line-width': rampe(s.zoom_largeur, s.epaisseur ?? 1.6), 'line-opacity': s.opacite ?? 0.9 }
    if (s.tirets) paint['line-dasharray'] = s.tirets
    out.push({ ...base, id: `${src}-line`, type: 'line', paint: paint as never })
  }
  if (dims.has('point')) {
    out.push({ ...base, id: `${src}-point`, type: 'circle',
      paint: {
        'circle-color': col,
        'circle-radius': rampe(s.zoom_rayon, s.rayon ?? 5),
        'circle-opacity': s.opacite ?? 0.95,
        'circle-stroke-width': s.halo ?? 0,
        'circle-stroke-color': s.trait || '#FFFFFF',
      } as never })
  }
  return out
}

function popupHTML(c: TuyauCouche, props: Record<string, unknown>): string {
  const lignes = (c.popup || []).map((p) => {
    const v = props[p.champ]
    if (v == null || v === '') return ''
    const val = p.lien
      ? `<a href="${String(v)}" target="_blank" rel="noopener" style="color:#7CC5FF">ouvrir</a>`
      : String(v)
    return `<div><span style="color:#9AA7A0">${p.libelle} :</span> ${val}</div>`
  }).filter(Boolean).join('')
  const titre = `<div style="font-weight:600;margin-bottom:2px">${c.nom}</div>`
  return `<div style="font-size:12px;line-height:1.5">${titre}${lignes || '<div style="color:#9AA7A0">—</div>'}</div>`
}

// ── le composant de RENDU (monté dans MapView) : sources + calques + popups + légende ──
export function CouchesTuyauLayers({ map, ready }: {
  map: React.MutableRefObject<maplibregl.Map | null>; ready: boolean
}) {
  const { data: plan } = useTuyauPlan()
  const { tuyauActives, setTuyauActives, setTuyauError } = useApp()
  const monte = useRef(false)

  // COUCHES-RECETTE-1 A5 : à l'initialisation, seuls les Repères (limites) sont cochés ; les autres
  // couches sont décochées par défaut (comme les anciennes). Le bâti 3D (hors panneau) n'est pas monté.
  useEffect(() => {
    if (plan && plan.length && Object.keys(tuyauActives).length === 0) {
      const m: Record<string, boolean> = {}
      for (const c of plan) if (!HORS_PANNEAU(c)) m[c.kind] = COCHE_DEFAUT(c)
      setTuyauActives(m)
    }
  }, [plan, tuyauActives, setTuyauActives])

  // monte les sources + calques + popups (une fois)
  useEffect(() => {
    const m = map.current
    if (!m || !ready || !plan || monte.current) return
    monte.current = true
    const onErr = (e: { sourceId?: string }) => {
      const sid = e.sourceId
      if (sid && sid.startsWith('tuyau-')) setTuyauError(sid.slice(6), true)
    }
    m.on('error', onErr as never)
    for (const c of plan) {
      if (HORS_PANNEAU(c)) continue   // A11 : le bâti 3D est géré par le bouton 3D, pas monté ici
      const src = `tuyau-${c.kind}`
      if (!m.getSource(src)) {
        // retour §5 : minzoom 0 — toutes les couches visibles dès la vue île (safer compris),
        // aucun bornage par zoom_min. maxzoom 16 = surzoom au-delà (pas de re-requête).
        m.addSource(src, { type: 'vector', minzoom: 0, maxzoom: 16,
          tiles: [`${window.location.origin}${c.tuiles_url}`] })
      }
      for (const spec of calques(c)) {
        if (!m.getLayer(spec.id)) m.addLayer(spec)
        if (c.popup && c.popup.length && (spec.id.endsWith('-fill') || spec.id.endsWith('-point') || spec.id.endsWith('-line'))) {
          m.on('click', spec.id, (e) => {
            const f = e.features?.[0]
            if (!f) return
            new maplibregl.Popup({ offset: 10, className: 'labuse-popup', maxWidth: '320px' })
              .setLngLat(e.lngLat).setHTML(popupHTML(c, f.properties as Record<string, unknown>)).addTo(m)
          })
          m.on('mouseenter', spec.id, () => { m.getCanvas().style.cursor = 'pointer' })
          m.on('mouseleave', spec.id, () => { m.getCanvas().style.cursor = '' })
        }
      }
    }
    return () => { m.off('error', onErr as never) }
  }, [ready, plan, map, setTuyauError])

  // visibilité : suit l'état des toggles
  useEffect(() => {
    const m = map.current
    if (!m || !ready || !plan) return
    for (const c of plan) {
      const vis = tuyauActives[c.kind] ? 'visible' : 'none'
      for (const spec of calques(c)) if (m.getLayer(spec.id)) m.setLayoutProperty(spec.id, 'visibility', vis)
    }
  }, [tuyauActives, ready, plan, map])

  return <TuyauLegend plan={plan} />
}

// ── la LÉGENDE bas-droite — COUCHES-RECETTE-1 A10 : titrée « Légende », UN ACCORDÉON PAR COUCHE
// active (titré du nom). La dernière couche allumée est dépliée, les autres repliées ; clic pour
// déplier. Décalée vers le haut pour ne pas chevaucher l'attribution « Cadastre © DGFiP ».
function TuyauLegend({ plan }: { plan: TuyauCouche[] | undefined }) {
  const { tuyauActives } = useApp()
  const actives = useMemo(
    () => (plan || []).filter((c) => tuyauActives[c.kind]).sort((a, b) => (b.rang_carte || 0) - (a.rang_carte || 0)),
    [plan, tuyauActives])
  // suit la DERNIÈRE couche allumée (elle devient l'accordéon déplié) ; clic pour changer.
  const [ouvert, setOuvert] = useState<string | null>(null)
  const prev = useRef<Record<string, boolean>>({})
  useEffect(() => {
    const nouv = Object.keys(tuyauActives).find((k) => tuyauActives[k] && !prev.current[k])
    if (nouv) setOuvert(nouv)
    prev.current = { ...tuyauActives }
  }, [tuyauActives])
  if (!actives.length) return null
  // par défaut (aucun clic encore), la couche active de plus haut rang (dessus) est dépliée.
  const deplie = ouvert && actives.some((c) => c.kind === ouvert) ? ouvert : actives[0].kind
  return (
    <div data-tuyau-legend
      className="floating absolute bottom-10 right-4 hidden max-h-[52vh] w-[244px] overflow-y-auto rounded-xl bg-surface-2/95 p-3 text-txt shadow-elev-2 sm:block">
      <p className="label-caps mb-2">Légende</p>
      <div className="flex flex-col gap-1">
        {actives.map((c) => {
          const isOpen = c.kind === deplie
          return (
            <div key={c.kind} className="rounded-md border border-line">
              <button onClick={() => setOuvert(isOpen ? '' : c.kind)} aria-expanded={isOpen}
                className="flex w-full items-center justify-between gap-2 px-2 py-1.5 text-left text-[11.5px] font-medium">
                <span className="flex min-w-0 items-center gap-2"><Pastille c={c} /><span className="truncate">{c.nom}</span></span>
                <span className={`shrink-0 text-txt-dim transition-transform ${isOpen ? '' : '-rotate-90'}`}>▾</span>
              </button>
              {isOpen && (
                <div className="flex flex-col gap-0.5 px-2 pb-2">
                  {c.niveaux && c.niveaux.length > 0 ? (
                    c.niveaux.map((n) => (
                      <div key={n.id} className="flex items-center gap-2 text-[10.5px] text-txt-mut">
                        <span className="h-2.5 w-3.5 shrink-0 rounded-sm border"
                          style={{ background: n.couleur, opacity: (n.opacite ?? 0.7) + 0.25, borderColor: n.couleur }} />
                        {/* libellé PROPRE de la déclaration (« Extrême », « Moyen »…) — jamais la clé */}
                        {n.legende}
                      </div>
                    ))
                  ) : (
                    <div className="text-[10.5px] text-txt-mut">{c.legende}</div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function Pastille({ c }: { c: TuyauCouche }) {
  const col = c.style?.couleur || c.niveaux?.[0]?.couleur || FALLBACK
  return <span className="h-2.5 w-3.5 shrink-0 rounded-sm border"
    style={{ background: col, opacity: (c.style?.opacite ?? 0.6) + 0.3, borderColor: c.style?.trait || col }} />
}

// ── la SECTION « Nouvelles couches » du panneau « Cartes » (montée dans LeftPanel), par famille ──
const FAMILLE_LABEL: Record<string, string> = {
  reperes: 'Repères', fond_de_plan: 'Fond de plan', urbanisme: 'Urbanisme', risques: 'Risques',
  environnement: 'Environnement', foncier: 'Foncier', reseaux: 'Réseaux',
  transport: 'Transport', dispositifs: 'Dispositifs', patrimoine: 'Patrimoine',
  equipements: 'Équipements', marche: 'Marché',
}

export function NouvellesCouches() {
  const { data: plan } = useTuyauPlan()
  const { tuyauActives, toggleTuyau, tuyauErrors } = useApp()
  const [open, setOpen] = useState(true)
  // COUCHES-RECETTE-1 : familles ORDONNÉES (Repères en tête, A11), le bâti 3D exclu (A11).
  const familles = useMemo(() => {
    const par: Record<string, TuyauCouche[]> = {}
    for (const c of plan || []) { if (HORS_PANNEAU(c)) continue; (par[c.famille] ??= []).push(c) }
    for (const k of Object.keys(par)) par[k].sort((a, b) => (a.rang_carte || 0) - (b.rang_carte || 0))
    return par
  }, [plan])
  if (!plan || !plan.length) return null
  const visibles = plan.filter((c) => !HORS_PANNEAU(c))
  const actifs = visibles.filter((c) => tuyauActives[c.kind]).length
  const ordre = [...ORDRE_FAMILLES.filter((f) => familles[f]),
    ...Object.keys(familles).filter((f) => !ORDRE_FAMILLES.includes(f))]
  return (
    <div data-tuyau-section className="mt-1">
      <button onClick={() => setOpen((v) => !v)} aria-expanded={open}
        className="group flex w-full items-center justify-between gap-2 text-left">
        <span className="label-caps">Couches</span>
        <span className="flex items-center gap-3">
          <span className="rounded-full bg-mint/15 px-1.5 py-0.5 text-[9.5px] font-medium text-mint">
            {actifs}/{visibles.length}
          </span>
          <span className={`text-txt-dim transition-transform ${open ? '' : '-rotate-90'}`}>▾</span>
        </span>
      </button>
      {open && (
        <div className="mt-2 flex flex-col gap-3.5">
          {ordre.map((fam) => (
            <div key={fam}>
              <p className="layer-cat mb-1.5 block">{FAMILLE_LABEL[fam] || fam}</p>
              <div className="gcard">
                {familles[fam].map((c) => {
                  const on = !!tuyauActives[c.kind]
                  const err = !!tuyauErrors[c.kind]
                  return (
                    <label key={c.kind}
                      className="flex cursor-pointer items-center gap-2 border-b border-line px-1 py-1.5 last:border-b-0">
                      {/* COUCHES-RECETTE-1 A9 : DA des anciennes couches — case à cocher + nom, PAS de
                          carré coloré devant le nom (la couleur se lit dans la légende). */}
                      <input type="checkbox" checked={on} onChange={() => toggleTuyau(c.kind)} className="accent-mint" />
                      <span className="min-w-0 flex-1 truncate text-[12px] text-txt">{c.nom}</span>
                      {/* COUCHES-RECETTE-1 A8 : le « i » par couche (texte de la déclaration). */}
                      {c.i && (
                        <span title={c.i}
                          className="grid h-3.5 w-3.5 shrink-0 cursor-help place-items-center rounded-full border border-line-2 text-[9px] font-semibold text-txt-dim">
                          i
                        </span>
                      )}
                      {err && (
                        <span title="Échec de chargement d'une tuile de cette couche"
                          className="shrink-0 text-[10px] font-medium text-danger">tuile en échec</span>
                      )}
                    </label>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
