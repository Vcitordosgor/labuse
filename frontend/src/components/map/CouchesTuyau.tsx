// COUCHES-TUYAU-1 lot 2 — le front du tuyau : UNE source vectorielle par couche, style depuis
// la déclaration (couleurs par grade en sous-calques via `niveaux`, légende, popup). Tout allumé
// dès la vue île (aucun bandeau d'attente, aucun « Zoomez »). Un échec de tuile est signalé sur la
// ligne de la couche, jamais muet. ADDITIF : ne touche à aucune couche existante.
import { useEffect, useMemo, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import { useQuery } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { LayerRowUI } from '../panel/LayerRowUI'   // COUCHES-RECETTE-2 B2 : composant de ligne partagé
import { ChevronSection } from '../panel/ChevronSection'   // FINITIONS-1 (P7) — flèche repli/dépli partagée
import { Chevron } from '../ui/Chevron'   // DA-FIX-3 Lot 5 (DA-031) — chevron d'accordéon partagé

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
  zoom_opacite?: number[]   // COUCHES-STYLE-1 : opacité de trait interpolée par zoom (défaut inchangé)
  trait_opacite?: number    // COUCHES-STYLE-2 : opacité CONSTANTE du contour (défaut 0.9 = inchangé pour les autres)
  filtre?: { propriete: string; valeur: string }
  point_opacite?: number   // opacité PROPRE des points (indépendante du fond translucide d'un polygone)
}
export interface TuyauPopup { champ: string; libelle: string; lien?: boolean }
export interface TuyauEtiquette { propriete: string; zoom_min?: number }
export interface TuyauCouche {
  kind: string; nom: string; famille: string; geometrie: string; zoom_min: number
  rang_carte: number; style: TuyauStyle; niveaux: TuyauNiveau[] | null
  popup: TuyauPopup[] | null; legende: string; statut_juridique: string | null; tuiles_url: string
  i?: string | null     // COUCHES-RECETTE-1 A8 : texte du « i » (déclaration, jamais un if kind===)
  subdivise?: boolean   // retour §2 : servie en morceaux ST_Subdivide → pas de contour de morceau
  centroide?: boolean   // A2 : polygone minuscule → un point (symbole) à son centroïde, visible dès l'île
  groupe?: string | null // fusion de couches en un seul toggle (ex. transport_public)
  etiquette?: TuyauEtiquette | null // calque symbole d'étiquettes (ex. zonage parcelle : zone_lib)
  note?: string | null  // A12 : note de couverture en légende (« pas de donnée publiée pour : … »)
  icones?: Record<string, string> | null // Lot B : {subtype: emoji} — icône par type (aménités OSM)
  // COUCHES-RECETTE-2 (retour) : clic précis sur une couche affichée dissoute (SUP) → interroge
  // /map/couche-detail/{detail_kind} au point cliqué (table d'origine) et affiche popup_detail.
  detail_kind?: string | null
  popup_detail?: TuyauPopup[] | null
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

// RETOURS-13 P5 — COURBES DE NIVEAU : couche RASTER (overlay de lignes transparent) servie par le
// proxy /map/tiles/contours (IGN Géoplateforme WMTS ELEVATION.CONTOUR.LINE, couverture 974 vérifiée).
// Déclarée CÔTÉ FRONT (le tuyau back ne sert que du vecteur) et fusionnée au plan : elle apparaît dans
// le panneau « Couches » (famille Environnement) et la légende comme n'importe quelle couche. Off par
// défaut (famille ≠ reperes). Le montage (source/calque) est spécialisé pour geometrie === 'raster'.
export const COURBES_NIVEAU_KIND = 'courbes_niveau'
const COURBES_NIVEAU_COUCHE: TuyauCouche = {
  kind: COURBES_NIVEAU_KIND,
  nom: 'Courbes de niveau',
  famille: 'environnement',
  geometrie: 'raster',
  zoom_min: 11,   // contours denses : gated jusqu'à z11 (« Zoomez pour voir » sinon), lisible en approche
  rang_carte: 5,
  style: {},
  // une pastille de légende (la teinte bistre mesurée des lignes IGN) — pas de gradation.
  niveaux: [{ id: 'ligne', propriete: 'x', valeur: 'x', couleur: '#CC8066', legende: 'Ligne de niveau', geometrie: 'ligne' }],
  popup: null,
  legende: 'Courbes de niveau (équidistance variable selon l’échelle)',
  statut_juridique: null,
  tuiles_url: '/map/tiles/contours/{z}/{x}/{y}',
  i: 'Courbes de niveau — IGN Géoplateforme, couche WMTS ELEVATION.CONTOUR.LINE (dérivée du RGE ALTI, millésime 2025). Équidistance variable selon l’échelle. Overlay raster superposable à tous les fonds.',
}

async function chargerPlan(): Promise<TuyauCouche[]> {
  const r = await fetch('/map/tuyau/couches')
  if (!r.ok) throw new Error(`plan tuyau: ${r.status}`)
  const j = await r.json()
  // RETOURS-13 P5 — le contour (raster) rejoint le plan vecteur servi par le back : un seul plan,
  // un seul panneau, une seule légende.
  return [...((j.couches ?? []) as TuyauCouche[]), COURBES_NIVEAU_COUCHE]
}

export function useTuyauPlan() {
  return useQuery({ queryKey: ['tuyau-couches'], queryFn: chargerPlan, staleTime: 3_600_000 })
}

// COUCHES-REGISTRE-2 lot 2 — le « i » dit d'où vient la couche (endpoint /map/couches-info, clé = kind).
// PAGE-SOURCES-1 (lot 1) — le MILLÉSIME est retiré du « i » : il ne reste que la SOURCE + la prose
// descriptive YAML. (Le millésime et la date de contrôle restent servis par l'endpoint — lus côté admin,
// fiche du réservoir — mais ne sont plus rendus ici.)
type CoucheInfo = { source: string; millesime: string | null; date_controle: string | null; fabrication: string | null }
async function chargerCouchesInfo(): Promise<Record<string, CoucheInfo>> {
  const r = await fetch('/map/couches-info')
  if (!r.ok) return {}
  return (await r.json()) as Record<string, CoucheInfo>
}
function useCouchesInfo() {
  return useQuery({ queryKey: ['couches-info'], queryFn: chargerCouchesInfo, staleTime: 3_600_000 })
}
// le contenu du « i » : la source (registre) + la prose YAML séparée en dessous.
function InfoTuyau({ meta, prose }: { meta?: CoucheInfo; prose?: string | null }) {
  return (
    <span className="block">
      {meta && (
        <span className="block">
          <span className="font-medium text-txt">{meta.source}</span>
        </span>
      )}
      {prose && (
        <span className="mt-1.5 block border-t border-line-2 pt-1.5 text-txt-dim">{prose}</span>
      )}
    </span>
  )
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

// COUCHES-RECETTE-2 Lot A — filtres par TYPE de géométrie. Un calque `circle` de MapLibre dessine un
// cercle à CHAQUE SOMMET de toute géométrie (y compris les anneaux d'un polygone / les nœuds d'une
// ligne) → « un rond par sommet ». Règle : un polygone = remplissage + contour ; une ligne = trait ;
// SEULS les vrais points portent un cercle. On restreint donc chaque calque à sa dimension réelle
// (Point / LineString / Polygon — MultiX renvoie le même type de base côté MapLibre).
const F_POINT = ['==', ['geometry-type'], 'Point'] as unknown
const F_LINE = ['==', ['geometry-type'], 'LineString'] as unknown
const F_POLY = ['==', ['geometry-type'], 'Polygon'] as unknown

// les calques MapLibre d'une couche (fond + contour + points selon la géométrie déclarée)
function calques(c: TuyauCouche): maplibregl.AddLayerObject[] {
  const src = `tuyau-${c.kind}`
  const sl = c.kind
  const s = c.style || {}
  const col = couleurExpr(c)
  const dims = dimensions(c.geometrie)
  const base = { source: src, 'source-layer': sl, layout: { visibility: 'none' as const } }
  const out: maplibregl.AddLayerObject[] = []
  // COUCHES-RECETTE-2 (retour SUP) : niveaux SURFACIQUES (géométrie polygone ou non précisée) → UN
  // calque `fill` PAR FAMILLE, filtré par sous-type, dans l'ORDRE de déclaration (grande famille au
  // fond, petite au-dessus). Chaque famille garde sa TEINTE constante à tous les zooms, aucune n'est
  // masquée par une autre, et l'ordre de superposition ne dépend plus de l'ordre des features dans la
  // tuile (qui variait au zoom → « la couleur change »).
  const nivPolys = (c.niveaux || []).filter((n) => !n.geometrie || n.geometrie === 'polygone')
  const propN = c.niveaux?.[0]?.propriete || 'subtype'
  if (dims.has('poly')) {
    if (!s.contour_seul) {
      if (nivPolys.length) {
        for (const n of nivPolys) {
          out.push({ ...base, id: `${src}-fill-${n.id}`, type: 'fill',
            filter: ['all', F_POLY, ['==', ['get', propN], n.valeur]] as never,
            paint: { 'fill-color': n.couleur, 'fill-opacity': n.opacite ?? s.opacite ?? 0.4 } as never })
        }
      } else {
        out.push({ ...base, id: `${src}-fill`, type: 'fill', filter: F_POLY as never,
          paint: { 'fill-color': col, 'fill-opacity': s.opacite ?? 0.4 } as never })
      }
    }
    // retour §2 : une couche servie en MORCEAUX (ST_Subdivide) ne dessine PAS de contour de morceau
    // (les coutures internes apparaîtraient). Le bord visible = l'arête du remplissage = l'origine.
    // Lot A : le contour ne dessine QUE les anneaux de polygone (jamais les sommets comme des ronds).
    if (!c.subdivise) {
      // COUCHES-STYLE-1 : largeur ET opacité du contour interpolables par zoom (via rampe) — pour que
      // le maillage parcellaire ne se ferme pas en surface aux petits zooms. Sans zoom_largeur /
      // zoom_opacite déclarés, `rampe` renvoie le défaut → rendu IDENTIQUE pour les 55 autres couches.
      out.push({ ...base, id: `${src}-outline`, type: 'line', filter: F_POLY as never,
        paint: { 'line-color': (s.trait || col) as never,
          'line-width': rampe(s.zoom_largeur, s.epaisseur ?? 1),
          // COUCHES-STYLE-2 : défaut du contour = `trait_opacite ?? 0.9` (constant). Sans zoom_opacite ni
          // trait_opacite déclarés → 0.9, exactement l'ancien rendu des 55 autres couches.
          'line-opacity': rampe(s.zoom_opacite, s.trait_opacite ?? 0.9) } as never })
    }
  }
  // COUCHES-RECETTE-2 Lot D : quand des NIVEAUX portent une géométrie propre (ligne/point), on rend UN
  // calque PAR NIVEAU avec SON style (tiret, largeur, rayon, anneau) — sinon un seul style écrasait tout
  // (ex. Papang plein vs Payanké pointillé ; TCSP rayon tireté / tronçon rampé / station anneau).
  const nivLignes = (c.niveaux || []).filter((n) => n.geometrie === 'ligne')
  const nivPoints = (c.niveaux || []).filter((n) => n.geometrie === 'point')
  const prop = c.niveaux?.[0]?.propriete || 'subtype'
  if (dims.has('line')) {
    if (nivLignes.length) {
      for (const n of nivLignes) {
        const paint: Record<string, unknown> = {
          'line-color': n.couleur, 'line-width': rampe((n as { zoom_largeur?: number[] }).zoom_largeur, n.epaisseur ?? 1.6),
          'line-opacity': n.opacite ?? 0.9 }
        if (n.tirets) paint['line-dasharray'] = n.tirets
        out.push({ ...base, id: `${src}-line-${n.id}`, type: 'line',
          filter: ['all', F_LINE, ['==', ['get', prop], n.valeur]] as never, paint: paint as never })
      }
    } else {
      const paint: Record<string, unknown> = {
        'line-color': col, 'line-width': rampe(s.zoom_largeur, s.epaisseur ?? 1.6), 'line-opacity': s.opacite ?? 0.9 }
      if (s.tirets) paint['line-dasharray'] = s.tirets
      // Lot A : le trait ne dessine QUE les lignes (pas les anneaux de polygone — c'est le rôle du contour).
      out.push({ ...base, id: `${src}-line`, type: 'line', filter: F_LINE as never, paint: paint as never })
    }
  }
  if (dims.has('point')) {
    if (nivPoints.length) {
      for (const n of nivPoints) {
        const anneau = (n as { anneau?: boolean }).anneau
        out.push({ ...base, id: `${src}-point-${n.id}`, type: 'circle',
          filter: ['all', F_POINT, ['==', ['get', prop], n.valeur]] as never,
          paint: {
            'circle-color': anneau ? 'rgba(0,0,0,0)' : n.couleur,
            'circle-radius': rampe((n as { zoom_rayon?: number[] }).zoom_rayon, n.rayon ?? 5),
            'circle-opacity': n.opacite ?? 0.95,
            'circle-stroke-width': anneau ? (n.epaisseur ?? 2) : 0,
            'circle-stroke-color': anneau ? n.couleur : (n.trait || '#FFFFFF'),
          } as never })
      }
    } else {
      // Lot A : le cercle ne dessine QUE les vrais points (plus de rond par sommet de polygone/ligne).
      out.push({ ...base, id: `${src}-point`, type: 'circle', filter: F_POINT as never,
        paint: {
          'circle-color': col,
          'circle-radius': rampe(s.zoom_rayon, s.rayon ?? 5),
          // point_et_polygone : les POINTS gardent leur opacité propre (le polygone reste translucide).
          'circle-opacity': s.point_opacite ?? s.opacite ?? 0.95,
          'circle-stroke-width': s.halo ?? 0,
          'circle-stroke-color': s.trait || '#FFFFFF',
        } as never })
    }
  }
  // COUCHES-RECETTE-1 A2 : couche `centroide` — un SYMBOLE (pastille) posé au centroïde de chaque
  // polygone (symbol-placement 'point' → un par polygone), visible DÈS L'ÎLE là où le polygone est
  // sous le pixel. La géométrie SERVIE reste le polygone (verrou V7a intact) ; c'est un rendu de plus.
  if (c.centroide && dims.has('poly')) {
    out.push({ id: `${src}-centro`, source: src, 'source-layer': sl, type: 'symbol',
      layout: { visibility: 'none', 'icon-image': `tuyau-dot-${c.kind}`, 'icon-allow-overlap': true,
        'icon-size': ['interpolate', ['linear'], ['zoom'], 8, 0.55, 12, 0.85, 16, 1] as never } as never,
      paint: {} as never })
  }
  // COUCHES-RECETTE-1 (Lot B) : ICÔNE PAR TYPE (aménités OSM) — un calque symbole au-dessus du rond,
  // icon-image choisie par sous-type (image emoji générée au montage). Comme l'ancienne couche.
  if (c.icones && Object.keys(c.icones).length) {
    const cas: unknown[] = ['match', ['get', 'subtype']]
    for (const sub of Object.keys(c.icones)) cas.push(sub, `tuyau-ic-${c.kind}-${sub}`)
    cas.push('')  // sous-type sans icône → pas d'image (le rond coloré reste)
    // COUCHES-RECETTE-2 Lot D : icônes LISIBLES dès le zoom commune (z12), plus seulement au zoom rue.
    out.push({ id: `${src}-icone`, source: src, 'source-layer': sl, type: 'symbol',
      minzoom: c.zoom_min ?? 12,
      layout: { visibility: 'none', 'icon-image': cas as never, 'icon-allow-overlap': true,
        'icon-size': ['interpolate', ['linear'], ['zoom'], 12, 0.8, 15, 1.0, 20, 1.3] as never,
        'icon-anchor': 'center' } as never,
      paint: {} as never })
  }
  // COUCHES-RECETTE-1 : étiquettes (ex. zonage parcelle → zone_lib) — un calque symbole, dès son zoom.
  if (c.etiquette && c.etiquette.propriete) {
    const e = c.etiquette
    out.push({ id: `${src}-label`, source: src, 'source-layer': sl, type: 'symbol',
      minzoom: e.zoom_min ?? 12,
      layout: { visibility: 'none', 'text-field': ['coalesce', ['get', e.propriete], ''] as never,
        'text-font': ['Open Sans Regular'], 'text-size': 11, 'symbol-placement': 'point',
        'text-allow-overlap': false } as never,
      paint: { 'text-color': '#EAF2EE', 'text-halo-color': '#0b0f14', 'text-halo-width': 1.4 } as never })
  }
  return out
}

// COUCHES-RECETTE-1 A2 : génère une pastille circulaire (couleur de la couche) et l'enregistre comme
// image de sprite `tuyau-dot-{kind}` — pour le calque `centroide` (symbole au centroïde du polygone).
function ajouterPastilleIcone(m: maplibregl.Map, kind: string, couleur: string, trait: string) {
  const id = `tuyau-dot-${kind}`
  if (m.hasImage(id)) return
  const D = 22, r = D / 2
  const cv = document.createElement('canvas'); cv.width = D; cv.height = D
  const ctx = cv.getContext('2d'); if (!ctx) return
  ctx.beginPath(); ctx.arc(r, r, r - 3, 0, Math.PI * 2)
  ctx.fillStyle = couleur; ctx.fill()
  ctx.lineWidth = 2; ctx.strokeStyle = trait; ctx.stroke()
  const img = ctx.getImageData(0, 0, D, D)
  m.addImage(id, { width: D, height: D, data: new Uint8Array(img.data.buffer) }, { pixelRatio: 2 })
}

// COUCHES-RECETTE-1 (Lot B) : image d'icône = un EMOJI rendu au canvas (robuste — la police système
// porte les emoji, contrairement au text-field du style qui n'a pas ces glyphes) → `tuyau-ic-{kind}-{sub}`.
function ajouterEmojiIcone(m: maplibregl.Map, id: string, emoji: string) {
  if (m.hasImage(id)) return
  const D = 34
  const cv = document.createElement('canvas'); cv.width = D; cv.height = D
  const ctx = cv.getContext('2d'); if (!ctx) return
  ctx.font = '24px "Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif'
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
  ctx.fillText(emoji, D / 2, D / 2 + 1)
  const img = ctx.getImageData(0, 0, D, D)
  m.addImage(id, { width: D, height: D, data: new Uint8Array(img.data.buffer) }, { pixelRatio: 2 })
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
  // COUCHES-RECETTE-2 Lot D : boîte OPAQUE (comme l'ancienne popup) — le conteneur MapLibre est
  // transparent (cf. .labuse-popup), donc l'opacité vient d'ici.
  return `<div style="font-size:12px;line-height:1.5;background:rgba(14,18,16,0.97);color:#E6EDE8;`
    + `border:1px solid rgba(120,140,128,0.28);border-radius:8px;padding:8px 10px;max-width:280px">`
    + `${titre}${lignes || '<div style="color:#9AA7A0">—</div>'}</div>`
}

// COUCHES-RECETTE-2 (retour) — popup PRÉCIS d'une couche dissoute (SUP) : chaque servitude concernée
// (renvoyée par l'endpoint de détail, table d'origine) rend ses champs déclarés (popup_detail).
function popupDetailHTML(c: TuyauCouche, servitudes: Record<string, unknown>[]): string {
  const champs = c.popup_detail || []
  const titre = `<div style="font-weight:600;margin-bottom:3px">${c.nom}</div>`
  const corps = servitudes.length
    ? servitudes.map((sv, i) => {
        const lignes = champs.map((p) => {
          const v = sv[p.champ]
          if (v == null || v === '') return ''
          const val = p.lien
            ? `<a href="${String(v)}" target="_blank" rel="noopener" style="color:#7CC5FF">ouvrir</a>`
            : String(v)
          return `<div><span style="color:#9AA7A0">${p.libelle} :</span> ${val}</div>`
        }).filter(Boolean).join('')
        const sep = i > 0 ? 'border-top:1px solid rgba(120,140,128,0.22);margin-top:5px;padding-top:5px;' : ''
        return `<div style="${sep}">${lignes}</div>`
      }).join('')
    : '<div style="color:#9AA7A0">Aucune servitude à ce point.</div>'
  return `<div style="font-size:12px;line-height:1.5;background:rgba(14,18,16,0.97);color:#E6EDE8;`
    + `border:1px solid rgba(120,140,128,0.28);border-radius:8px;padding:8px 10px;max-width:300px">`
    + `${titre}${corps}</div>`
}

// COUCHES-STYLE-5 — la couche parcelles du tuyau (contour cadastral) suit le FOND actif, exactement
// comme V1 (MapView.applyBasemapStyle + variant photo RETOURS-11 C4). Le gris-vert #8FA69A/0,3/0,4 est
// illisible sur Ortho ; on reporte les VALEURS DE V1 telles quelles, par fond :
//  - Sombre (dark) : INCHANGÉ — #8FA69A, largeur 0,3, opacité 0,4 (constantes STYLE-2, témoin) ;
//  - Ortho : contour #0A0F0C, largeur/opacité interpolées au zoom (variant photo — se renforce au zoom) ;
//  - Plan IGN : contour #000000 avec la rampe photo (couleur du bloc clair||plan, rampes du variant photo).
// Ces expressions sont copiées VERBATIM de applyBasemapStyle (aucun recalibrage). Le seul calque touché
// est le contour des parcelles du tuyau (`tuyau-limites_parcelles-outline`).
// COUCHES-STYLE-6 : le fond « Clair » est retiré du sélecteur → sa branche est retirée ici aussi.
const PARCELLES_OUTLINE = 'tuyau-limites_parcelles-outline'
type PaintParcelles = { color: string; width: unknown; opacity: unknown }
function paintParcellesParFond(basemap: string): PaintParcelles {
  if (basemap === 'ortho')
    return { color: '#0A0F0C',
      width: ['interpolate', ['linear'], ['zoom'], 13, 0.4, 15, 1.0, 17, 1.8, 19, 2.2],
      opacity: ['interpolate', ['linear'], ['zoom'], 13, 0, 14, 0.25, 16, 0.7, 18, 0.9] }
  if (basemap === 'plan')   // couleur du bloc clair||plan (#000000) + rampe du variant photo
    return { color: '#000000',
      width: ['interpolate', ['linear'], ['zoom'], 13, 0.4, 15, 1.0, 17, 1.8, 19, 2.2],
      opacity: ['interpolate', ['linear'], ['zoom'], 13, 0, 14, 0.25, 16, 0.7, 18, 0.9] }
  // Sombre (dark) et tout autre fond = témoin : valeurs STYLE-2 constantes, rien ne bouge.
  return { color: '#8FA69A', width: 0.3, opacity: 0.4 }
}

// ── le composant de RENDU (monté dans MapView) : sources + calques + popups + légende ──
export function CouchesTuyauLayers({ map, ready }: {
  map: React.MutableRefObject<maplibregl.Map | null>; ready: boolean
}) {
  const { data: plan } = useTuyauPlan()
  const { tuyauActives, setTuyauActives, setTuyauError, basemap } = useApp()
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
    // COUCHES-STYLE-4 : le voile de mise en avant (calque `background` couche-veil, RECETTE-2 C1) est
    // RETIRÉ. Le fond n'est plus atténué quand une couche thématique est cochée — les couches du tuyau
    // se posent directement au-dessus du fond, sans calque intermédiaire.
    for (const c of plan) {
      if (HORS_PANNEAU(c)) continue   // A11 : le bâti 3D est géré par le bouton 3D, pas monté ici
      // RETOURS-13 P5 — une couche RASTER (courbes de niveau) : source + calque `raster`, pas de
      // vecteur, pas de popup. Overlay de lignes transparent posé au-dessus du fond et des couches.
      if (c.geometrie === 'raster') {
        const rsrc = `tuyau-${c.kind}`
        if (!m.getSource(rsrc)) {
          m.addSource(rsrc, { type: 'raster', tileSize: 256, minzoom: 6, maxzoom: 18,
            tiles: [`${window.location.origin}${c.tuiles_url}`] })
        }
        const rid = `tuyau-${c.kind}-raster`
        if (!m.getLayer(rid)) m.addLayer({ id: rid, type: 'raster', source: rsrc,
          layout: { visibility: 'none' }, paint: { 'raster-opacity': 0.85 } })
        continue
      }
      const src = `tuyau-${c.kind}`
      if (!m.getSource(src)) {
        // COUCHES-RECETTE-1 (A7 / lenteur) : la source n'est demandée qu'à partir de son zoom_min —
        // une couche par-parcelle (zonage_parcelle, 431 k) ou un semis de points ne charge plus la
        // tuile ÎLE géante qui n'a aucun sens à cette échelle. Les couches d'aperçu (risques, zonages
        // GPU) gardent zoom_min 0 → visibles dès l'île. Géométrie inchangée (LOD, pas de dégradation).
        m.addSource(src, { type: 'vector', minzoom: c.zoom_min ?? 0, maxzoom: 16,
          tiles: [`${window.location.origin}${c.tuiles_url}`] })
      }
      if (c.centroide) {
        const dc = c.style?.couleur || c.niveaux?.[0]?.couleur || FALLBACK
        ajouterPastilleIcone(m, c.kind, dc, c.style?.trait || '#0b0f14')
      }
      if (c.icones) for (const [sub, emoji] of Object.entries(c.icones)) ajouterEmojiIcone(m, `tuyau-ic-${c.kind}-${sub}`, emoji)
      for (const spec of calques(c)) {
        if (!m.getLayer(spec.id)) m.addLayer(spec)
        // popup sur les calques de DONNÉE (fill / point / line, y compris par-niveau « -point-xxx »),
        // jamais sur le contour, l'icône, l'étiquette ou le centroïde.
        const estData = /-(fill|point|line)(-|$)/.test(spec.id) && !spec.id.includes('-outline')
        if (((c.popup && c.popup.length) || c.detail_kind) && estData) {
          const estPoint = spec.id.includes('-point')
          m.on('click', spec.id, (e) => {
            const f = e.features?.[0]
            if (!f) return
            const pop = new maplibregl.Popup({ offset: estPoint ? 14 : 10, className: 'labuse-popup', maxWidth: '320px',
              ...(estPoint ? { anchor: 'bottom' as const } : {}) })
              .setLngLat(estPoint ? (f.geometry as GeoJSON.Point).coordinates as [number, number] : e.lngLat)
            // COUCHES-RECETTE-2 (retour) : couche affichée DISSOUTE (SUP) → clic PRÉCIS via l'endpoint
            // de détail (table d'origine, assiettes non dissoutes) ; sinon popup depuis la tuile.
            if (c.detail_kind) {
              pop.setHTML('<div style="font-size:12px;background:rgba(14,18,16,0.97);color:#9AA7A0;border-radius:8px;padding:8px 10px">…</div>').addTo(m)
              fetch(`/map/couche-detail/${c.detail_kind}?lon=${e.lngLat.lng}&lat=${e.lngLat.lat}`)
                .then((r) => r.ok ? r.json() : { servitudes: [] })
                .then((j) => pop.setHTML(popupDetailHTML(c, (j.servitudes || []) as Record<string, unknown>[])))
                .catch(() => pop.setHTML(popupDetailHTML(c, [])))
            } else {
              pop.setHTML(popupHTML(c, f.properties as Record<string, unknown>)).addTo(m)
            }
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
      if (c.geometrie === 'raster') {   // RETOURS-13 P5 — le calque raster (courbes de niveau) suit son toggle
        const rid = `tuyau-${c.kind}-raster`
        if (m.getLayer(rid)) m.setLayoutProperty(rid, 'visibility', vis)
        continue
      }
      for (const spec of calques(c)) if (m.getLayer(spec.id)) m.setLayoutProperty(spec.id, 'visibility', vis)
    }
  }, [tuyauActives, ready, plan, map])

  // COUCHES-STYLE-5 : le contour des parcelles du tuyau suit le FOND actif (comme V1). Réappliqué à
  // chaque bascule de fond ET au montage (dép. plan) ; en Sombre les valeurs STYLE-2 sont ré-posées
  // à l'identique → le témoin ne bouge pas. Seul `tuyau-limites_parcelles-outline` est touché.
  useEffect(() => {
    const m = map.current
    if (!m || !ready || !plan) return
    if (!m.getLayer(PARCELLES_OUTLINE)) return
    const p = paintParcellesParFond(basemap)
    m.setPaintProperty(PARCELLES_OUTLINE, 'line-color', p.color as never)
    m.setPaintProperty(PARCELLES_OUTLINE, 'line-width', p.width as never)
    m.setPaintProperty(PARCELLES_OUTLINE, 'line-opacity', p.opacity as never)
  }, [basemap, ready, plan, map])

  // COUCHES-STYLE-4 : plus de pilotage d'opacité du voile — le mécanisme couche-veil a été retiré.

  // COUCHES-RECETTE-2 B5 : suit le zoom courant pour dire « Zoomez pour voir … » quand une couche
  // active n'apparaît qu'à partir d'un zoom minimum.
  const [zoom, setZoom] = useState(0)
  useEffect(() => {
    const m = map.current
    if (!m || !ready) return
    const upd = () => setZoom(m.getZoom())
    upd(); m.on('zoom', upd)
    return () => { m.off('zoom', upd) }
  }, [map, ready])

  // couches actives dont le zoom_min n'est pas atteint (jamais un silence : dit en légende ET sur la carte).
  const gatees = (plan || []).filter((c) => tuyauActives[c.kind] && (c.zoom_min ?? 0) > zoom + 0.001)

  return (
    <>
      <TuyauLegend plan={plan} zoom={zoom} />
      {gatees.length > 0 && (
        <div data-tuyau-zoom-hint
          className="pointer-events-none absolute left-1/2 top-16 z-10 -translate-x-1/2 rounded-full border border-mint/40 bg-surface-2/95 px-3.5 py-1.5 text-[11.5px] text-txt shadow-elev-2">
          Zoomez pour voir : {gatees.map((c) => c.nom).join(', ')}
        </div>
      )}
    </>
  )
}

// ── la LÉGENDE bas-droite — COUCHES-RECETTE-1 A10 : titrée « Légende », UN ACCORDÉON PAR COUCHE
// active (titré du nom). La dernière couche allumée est dépliée, les autres repliées ; clic pour
// déplier. Décalée vers le haut pour ne pas chevaucher l'attribution « Cadastre © DGFiP ».
function TuyauLegend({ plan, zoom }: { plan: TuyauCouche[] | undefined; zoom: number }) {
  const { tuyauActives } = useApp()
  const actives = useMemo(
    () => (plan || []).filter((c) => tuyauActives[c.kind]).sort((a, b) => (b.rang_carte || 0) - (a.rang_carte || 0)),
    [plan, tuyauActives])
  // DA-FIX-5b — chaque rangée a son PROPRE état déplié/replié (indépendant) : PLUSIEURS rangées
  // peuvent être ouvertes en même temps (l'exclusivité posée en FIX-5 P2 est annulée). Une couche
  // fraîchement allumée déplie SA rangée, sans toucher aux autres.
  const [ouverts, setOuverts] = useState<Record<string, boolean>>({})
  // FINITIONS-1 (P7) — la légende des couches se replie/déplie par une petite flèche (accordéon DA :
  // ouverte = pointe en bas, repliée = pointe à droite).
  // OUTILS-S2 Lot D (D.2) — FERMÉE par défaut tant que seules les couches par défaut (Repères :
  // limites parcelles/communes) sont actives ; elle s'ouvre d'elle-même dès qu'une 3e couche est
  // activée. Une fois ouverte/fermée à la main, le choix de l'utilisateur PRIME pour la session
  // (`ouvertManuel` non nul l'emporte sur l'auto-ouverture). `null` = pas encore touchée.
  const nonDefautActif = actives.some((c) => !COCHE_DEFAUT(c))
  const [ouvertManuel, setOuvertManuel] = useState<boolean | null>(null)
  const ouvert = ouvertManuel ?? nonDefautActif
  const prev = useRef<Record<string, boolean>>({})
  useEffect(() => {
    const nouv = Object.keys(tuyauActives).find((k) => tuyauActives[k] && !prev.current[k])
    if (nouv) setOuverts((o) => ({ ...o, [nouv]: true }))
    prev.current = { ...tuyauActives }
  }, [tuyauActives])
  if (!actives.length) return null
  // par défaut (aucun clic encore), la couche active de plus haut rang (dessus) est dépliée.
  // COUCHES-RECETTE-1 : les couches FUSIONNÉES (transport public) forment UN accordéon (haut de pile
  // d'abord). Chaque entrée montre ses grades (niveaux) OU ses teintes data-driven (par réseau /
  // catégorie via style.couleurs) + une note de couverture (A12).
  const entrees = grouper(actives).reverse()
  const defautCle = entrees[0]?.cle ?? null
  // état déplié PROPRE à la rangée : sa clé (ou une de ses membres, si l'ouverture vient d'une
  // activation par kind) ; à défaut, seule la couche du dessus est dépliée.
  const estDeplie = (e: Entree) => {
    const k = (e.cle in ouverts) ? e.cle : (e.membres.find((m) => m.kind in ouverts)?.kind ?? null)
    return k != null ? ouverts[k] : (e.cle === defautCle)
  }
  return (
    <div data-tuyau-legend
      className="floating absolute bottom-10 right-4 hidden max-h-[52vh] w-[244px] overflow-y-auto rounded-xl bg-surface-2/95 p-3 text-txt shadow-elev-2 sm:block">
      {/* FINITIONS-1 (P7) — en-tête cliquable avec la flèche de repli/dépli (ChevronSection, DA). */}
      <button data-tuyau-legend-toggle onClick={() => setOuvertManuel(!ouvert)} aria-expanded={ouvert}
        className="flex w-full items-center gap-2 text-left">
        <span className="label-caps flex-1">Légende</span>
        <ChevronSection open={ouvert} />
      </button>
      {ouvert && (
      <div className="mt-2 flex flex-col gap-1">
        {entrees.map((e) => {
          const isOpen = estDeplie(e)
          const sw = pastillesLegende(e)
          const note = e.membres.map((m) => m.note).find(Boolean)
          // COUCHES-RECETTE-2 B5 : couche à zoom minimum non atteint → « Zoomez pour voir … ».
          const zmin = Math.max(...e.membres.map((m) => m.zoom_min ?? 0))
          const gated = zmin > zoom + 0.001
          return (
            <div key={e.cle} className="rounded-md border border-line">
              {/* COUCHES-RECETTE-2 B4 : PAS de pastille à côté du titre (les pastilles sont DANS
                  l'accordéon, une par niveau) ; le titre passe sur deux lignes, jamais tronqué. */}
              <button onClick={() => setOuverts((o) => ({ ...o, [e.cle]: !isOpen }))} aria-expanded={isOpen}
                className="flex w-full items-start justify-between gap-2 px-2 py-1.5 text-left text-[11.5px] font-medium">
                <span className="min-w-0 flex-1 leading-tight">{e.nom}</span>
                {/* DA-FIX-3 Lot 5 (DA-031) — chevron partagé (fermé ▶ / ouvert ▼) : plus de ▾ figé dans les deux états. */}
                <Chevron open={isOpen} />
              </button>
              {isOpen && (
                <div className="flex flex-col gap-0.5 px-2 pb-2">
                  {gated ? (
                    <div className="text-[10.5px] font-medium text-mint">Zoomez pour voir {e.nom}</div>
                  ) : sw.length > 0 ? (
                    sw.map((n) => (
                      <div key={n.k} className="flex items-start gap-2 text-[10.5px] leading-tight text-txt-mut">
                        <span className="mt-0.5 h-2.5 w-3.5 shrink-0 rounded-sm border"
                          style={{ background: n.couleur, opacity: (n.opacite ?? 0.7) + 0.25, borderColor: n.couleur }} />
                        {/* libellé PROPRE de la déclaration — jamais la clé technique, jamais tronqué */}
                        <span className="min-w-0 flex-1">{n.legende}</span>
                      </div>
                    ))
                  ) : (
                    // B4 : une SEULE pastille quand il n'y a qu'un niveau. COUCHES-STYLE-1 : une couche
                    // `contour_seul` se rend en TRAIT → la pastille est une BARRE (trait), pas un carré plein.
                    <div className="flex items-start gap-2 text-[10.5px] leading-tight text-txt-mut">
                      {e.membres[0].style?.contour_seul ? (
                        <span className="mt-1.5 h-0.5 w-3.5 shrink-0 rounded-full"
                          style={{ background: e.membres[0].style?.trait || e.membres[0].style?.couleur || FALLBACK }} />
                      ) : (
                        <span className="mt-0.5 h-2.5 w-3.5 shrink-0 rounded-sm border"
                          style={{ background: e.membres[0].style?.couleur || FALLBACK,
                            opacity: (e.membres[0].style?.opacite ?? 0.6) + 0.3,
                            borderColor: e.membres[0].style?.trait || e.membres[0].style?.couleur || FALLBACK }} />
                      )}
                      <span className="min-w-0 flex-1">{e.membres[0].legende}</span>
                    </div>
                  )}
                  {/* A12 : couverture partielle dite en clair */}
                  {note && <div className="mt-1 text-[10px] italic text-txt-dim">{note}</div>}
                </div>
              )}
            </div>
          )
        })}
      </div>
      )}
    </div>
  )
}


// ── la SECTION « Nouvelles couches » du panneau « Cartes » (montée dans LeftPanel), par famille ──
const FAMILLE_LABEL: Record<string, string> = {
  reperes: 'Repères', fond_de_plan: 'Fond de plan', urbanisme: 'Urbanisme', risques: 'Risques',
  environnement: 'Environnement', foncier: 'Foncier', reseaux: 'Réseaux',
  transport: 'Transport', dispositifs: 'Dispositifs', patrimoine: 'Patrimoine',
  equipements: 'Équipements', marche: 'Marché',
}
// COUCHES-RECETTE-1 (Lot B) : couches FUSIONNÉES en une seule entrée de panneau (un toggle, plusieurs
// sous-calques). Le libellé du groupe et son « i ».
const GROUPE_LABEL: Record<string, string> = { transport_public: 'Transport public' }
const GROUPE_I: Record<string, string> = {
  transport_public: 'Réseau de transport en commun (bus + téléphérique) : lignes et arrêts GTFS des 6 réseaux, couleur par réseau. Deux sous-calques (lignes / arrêts) sous un seul interrupteur.',
}
// Une entrée du panneau = une couche seule, ou un groupe de couches (membres = plusieurs kinds).
interface Entree { cle: string; nom: string; i?: string | null; membres: TuyauCouche[]; groupe: boolean }
function grouper(couches: TuyauCouche[]): Entree[] {
  const out: Entree[] = []
  const parGroupe: Record<string, TuyauCouche[]> = {}
  for (const c of couches) {
    if (c.groupe) { (parGroupe[c.groupe] ??= []).push(c); continue }
    out.push({ cle: c.kind, nom: c.nom, i: c.i, membres: [c], groupe: false })
  }
  for (const [g, membres] of Object.entries(parGroupe)) {
    out.push({ cle: `g:${g}`, nom: GROUPE_LABEL[g] || g, i: GROUPE_I[g] || membres[0]?.i,
      membres, groupe: true })
  }
  return out.sort((a, b) => (a.membres[0].rang_carte || 0) - (b.membres[0].rang_carte || 0))
}

// pastilles de légende d'une entrée : ses grades (niveaux) OU ses teintes data-driven (par réseau /
// catégorie via style.couleurs). Dédupliqué par libellé (transport : lignes + arrêts = mêmes réseaux).
interface SwLeg { k: string; couleur: string; opacite?: number; legende: string }
function pastillesLegende(e: Entree): SwLeg[] {
  const out: SwLeg[] = []; const vus = new Set<string>()
  for (const c of e.membres) {
    if (c.niveaux && c.niveaux.length) {
      for (const n of c.niveaux) {
        if (vus.has(n.legende)) continue; vus.add(n.legende)
        out.push({ k: `${c.kind}:${n.id}`, couleur: n.couleur, opacite: n.opacite, legende: n.legende })
      }
    } else if (c.style?.couleur_propriete && c.style?.couleurs) {
      for (const [key, val] of Object.entries(c.style.couleurs)) {
        if (vus.has(key)) continue; vus.add(key)
        out.push({ k: `${c.kind}:${key}`, couleur: val, opacite: c.style.opacite, legende: key })
      }
    }
  }
  return out
}

// COUCHES-RECETTE-2 B1/B2 : plus d'en-tête « Couches » propre (celui de LayersSection suffit — le
// double en-tête est supprimé) ; les couches du tuyau utilisent LE MÊME composant que l'ancienne
// liste (LayerRowUI) → DA indiscernable, « i » au survol immédiat (Tip). Familles ordonnées, bâti exclu.
export function NouvellesCouches() {
  const { data: plan } = useTuyauPlan()
  const { data: couchesInfo } = useCouchesInfo()   // COUCHES-REGISTRE-2 lot 2 — source/millésime/contrôle
  const { tuyauActives, toggleTuyau, tuyauErrors } = useApp()
  const familles = useMemo(() => {
    const par: Record<string, TuyauCouche[]> = {}
    for (const c of plan || []) { if (HORS_PANNEAU(c)) continue; (par[c.famille] ??= []).push(c) }
    for (const k of Object.keys(par)) par[k].sort((a, b) => (a.rang_carte || 0) - (b.rang_carte || 0))
    return par
  }, [plan])
  if (!plan || !plan.length) return null
  const ordre = [...ORDRE_FAMILLES.filter((f) => familles[f]),
    ...Object.keys(familles).filter((f) => !ORDRE_FAMILLES.includes(f))]
  return (
    <>
      {ordre.map((fam) => (
        <div key={fam}>
          <p className="layer-cat mb-1.5 block">{FAMILLE_LABEL[fam] || fam}</p>
          <div className="gcard">
            {grouper(familles[fam]).map((e) => {
              // un groupe est allumé si l'un de ses membres l'est ; le toggle bascule TOUS les membres.
              const on = e.membres.some((m) => tuyauActives[m.kind])
              const err = e.membres.some((m) => tuyauErrors[m.kind])
              const bascule = () => { for (const m of e.membres) if (!!tuyauActives[m.kind] === on) toggleTuyau(m.kind) }
              return (
                <div key={e.cle} className="border-b border-line last:border-b-0">
                  <LayerRowUI on={on} label={e.nom}
                    info={<InfoTuyau meta={couchesInfo?.[e.membres[0]?.kind ?? '']} prose={e.i} />}
                    onToggle={bascule} dataKey={e.membres[0]?.kind} err={err} />
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </>
  )
}
