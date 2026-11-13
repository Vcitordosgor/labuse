// GABARIT-3D-1 (pilote, étape 2 ter) — VISIONNEUSE Three.js, à la demande, réservée aux admins.
//
// Cible : docs/design/maquettes/nov-2026/16-ecran-cible-astra.png. En-tête (adresse·commune·réf) ;
// 3D en haut à gauche ; à droite le plan-clé + la légende ; en bas la coupe active (pleine largeur),
// sélecteur Coupe A/B. Courbes/contours/axes/marqueurs posés sur les TRIANGLES SERVIS (échantillonneur
// triangulé, pas d'interpolation à part) ; inversion altitude/nord corrigée ; teinte verte qui ne
// comble pas les trous ; boussole qui tourne ; cotes haut/bas sur leurs points ; axe actif orange ;
// changer de coupe NE recrée PAS le contexte WebGL. Safari : ressources libérées, repli si WebGL tombe.
import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useQuery } from '@tanstack/react-query'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { Line2 } from 'three/examples/jsm/lines/Line2.js'
import { LineMaterial } from 'three/examples/jsm/lines/LineMaterial.js'
import { LineGeometry } from 'three/examples/jsm/lines/LineGeometry.js'
import { getGabaritScene, gabCoupeSvgUrl, gabPlanSvgUrl, gabOrthoUrl, type GabScene, type GabMesh, type GabPoly } from '../../lib/api'
import { Squelette } from '../Loading'

function webglOK(): boolean {
  try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')) } catch { return false }
}
// repère : local (x=est, y=nord, z=alt) → Three (x, alt, -nord). MÊME transformation partout.
function inRing(x: number, y: number, r: number[][]): boolean {
  let o = false
  for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
    const [xi, yi] = r[i], [xj, yj] = r[j]
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) o = !o
  }
  return o
}
function inPolys(x: number, y: number, polys: GabPoly[]): boolean {
  for (const p of polys) if (inRing(x, y, p.ext) && !(p.trous || []).some((t) => inRing(x, y, t))) return true
  return false
}

// altitude = RAYCAST du maillage AFFICHÉ → suit EXACTEMENT les triangles servis (même altitude que la
// face visible ; corrige toute reconstruction de diagonale). None hors maillage.
function makeElev(mesh: THREE.Mesh): (x: number, y: number) => number | null {
  const ray = new THREE.Raycaster(), down = new THREE.Vector3(0, -1, 0)
  mesh.geometry.computeBoundingBox(); const top = (mesh.geometry.boundingBox?.max.y ?? 100) + 60
  return (x, y) => { ray.set(new THREE.Vector3(x, top, -y), down); const h = ray.intersectObject(mesh); return h[0] ? h[0].point.y : null }
}

const RAMP_LOW = new THREE.Color('#34403a'), RAMP_HIGH = new THREE.Color('#86a093')

function terrainMesh(f: GabMesh, parcelle: GabPoly[]) {
  const g = new THREE.BufferGeometry()
  const pos = new Float32Array(f.vertices.length * 3), col = new Float32Array(f.vertices.length * 3)
  let zmin = Infinity, zmax = -Infinity
  for (const p of f.vertices) { zmin = Math.min(zmin, p[2]); zmax = Math.max(zmax, p[2]) }
  const span = Math.max(zmax - zmin, 1e-6)
  f.vertices.forEach((p, i) => {   // ramp d'altitude + assombri hors parcelle (la ZONE est un masque par pixel, pas par sommet)
    pos[i * 3] = p[0]; pos[i * 3 + 1] = p[2]; pos[i * 3 + 2] = -p[1]
    const c = RAMP_LOW.clone().lerp(RAMP_HIGH, (p[2] - zmin) / span)
    if (!inPolys(p[0], p[1], parcelle)) c.multiplyScalar(0.6)
    col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b
  })
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3))
  g.setAttribute('color', new THREE.BufferAttribute(col, 3))
  g.setIndex(f.triangles.flat()); g.computeVertexNormals()         // ombrage lissé
  const mesh = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, side: THREE.DoubleSide }))
  g.computeBoundingBox()
  return { mesh, zmin, zmax, box: g.boundingBox!.clone() }
}

// ZONE d'implantation = MASQUE PAR PIXEL : polygone+trous peints sur un canvas, plaqué sur le terrain par
// coordonnées monde (bords francs, transition ~1 px, aucun halo). Remplace la couleur par sommet.
function zoneOverlay(terrain: THREE.Mesh, zone: GabPoly[], cadre: number[]): THREE.Mesh | null {
  if (!zone.length || cadre.length !== 4) return null
  const [minx, miny, maxx, maxy] = cadre, W = maxx - minx, H = maxy - miny, S = 1024
  const cv = document.createElement('canvas'); cv.width = cv.height = S
  const ctx = cv.getContext('2d'); if (!ctx) return null
  ctx.fillStyle = '#2f9e6a'; ctx.beginPath()
  for (const poly of zone) for (const ring of [poly.ext, ...(poly.trous || [])]) {
    ring.forEach(([x, y], i) => { const u = ((x - minx) / W) * S, v = (1 - (y - miny) / H) * S; i ? ctx.lineTo(u, v) : ctx.moveTo(u, v) }); ctx.closePath()
  }
  ctx.fill('evenodd')                                              // trous respectés
  const tex = new THREE.CanvasTexture(cv); tex.minFilter = THREE.LinearFilter
  const geo = (terrain.geometry as THREE.BufferGeometry).clone()
  const p = geo.getAttribute('position'), uv = new Float32Array(p.count * 2)
  for (let i = 0; i < p.count; i++) { uv[i * 2] = (p.getX(i) - minx) / W; uv[i * 2 + 1] = (-p.getZ(i) - miny) / H }
  geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2))
  const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ map: tex, transparent: true, opacity: 0.5, depthWrite: false, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 }))
  m.renderOrder = 1; return m
}

// courbes de niveau par intersection des triangles SERVIS ; émission (x, altitude, -nord) CORRIGÉE.
function contours(f: GabMesh) {
  const V = f.vertices, master: number[] = [], minor: number[] = [], seen = new Set<string>()
  const interp = (a: number[], b: number[], lv: number) => { const t = (lv - a[2]) / (b[2] - a[2]); return [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])] }
  for (const tri of f.triangles) {
    const P = [V[tri[0]], V[tri[1]], V[tri[2]]]
    const lo = Math.min(P[0][2], P[1][2], P[2][2]), hi = Math.max(P[0][2], P[1][2], P[2][2])
    for (let lv = Math.ceil(lo); lv <= hi; lv += 1) {
      const xs: number[][] = []
      for (let e = 0; e < 3; e++) {
        const a = P[e], b = P[(e + 1) % 3]
        if ((a[2] - lv) * (b[2] - lv) < 0) xs.push(interp(a, b, lv))
        else if (a[2] === lv) xs.push([a[0], a[1]])                 // égalité : sommet sur le niveau
      }
      if (xs.length >= 2) {
        const k = `${lv}:${Math.round(xs[0][0] * 4)}:${Math.round(xs[0][1] * 4)}:${Math.round(xs[1][0] * 4)}:${Math.round(xs[1][1] * 4)}`
        if (seen.has(k)) continue
        seen.add(k)
        const arr = lv % 5 === 0 ? master : minor
        arr.push(xs[0][0], lv, -xs[0][1], xs[1][0], lv, -xs[1][1])   // (x, altitude, -nord)
      }
    }
  }
  const mk = (a: number[], color: number, op: number) => {
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(a), 3))
    return new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color, transparent: true, opacity: op }))
  }
  return { master: mk(master, 0xb9c6bd, 0.6), minor: mk(minor, 0x7c8a81, 0.3) }
}

function drapeLine(ring: number[][], elev: (x: number, y: number) => number | null, color: number, px: number, res: THREE.Vector2, dashed = false, closed = false, opaque = false, opacity = 1, depthTest = true, renderOrder = 3) {
  const group = new THREE.Group()
  const mat = new LineMaterial({ color, linewidth: px, transparent: !opaque || !depthTest, opacity, dashed, dashSize: 1.2, gapSize: 1.0 })
  mat.resolution.copy(res); mat.depthTest = depthTest
  let run: number[] = []
  const flush = () => { if (run.length >= 6) { const g = new LineGeometry(); g.setPositions(run); const l = new Line2(g, mat); l.computeLineDistances(); l.renderOrder = renderOrder; group.add(l) } run = [] }
  const r2 = closed && ring.length > 1 ? [...ring, ring[0]] : ring      // FERMÉE (sans trou) pour le cadastre
  const dense: number[][] = []
  for (let i = 0; i < r2.length - 1; i++) {
    const a = r2[i], b = r2[i + 1], d = Math.hypot(b[0] - a[0], b[1] - a[1]), n = Math.max(1, Math.ceil(d))
    for (let k = 0; k < n; k++) dense.push([a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n])
  }
  dense.push(r2[r2.length - 1])
  let lastZ: number | null = null
  for (const [x, y] of dense) {
    const z = elev(x, y)
    if (z != null) { run.push(x, z + 0.4, -y); lastZ = z }
    else if (closed && lastZ != null) run.push(x, lastZ + 0.4, -y)      // continu (sans trou), jamais 0
    else flush()                                                        // sinon : interruption (lacune)
  }
  flush()
  return group
}

function batiVolume(b: GabScene['batiments'][number], elev: (x: number, y: number) => number | null, res: THREE.Vector2) {
  const grp = new THREE.Group()
  const vol = (b as { volume?: boolean }).volume && b.hauteur_m && b.pied_m != null
  for (const poly of b.empreinte) {
    if (vol) {
      const shape = new THREE.Shape(poly.ext.map(([x, y]) => new THREE.Vector2(x, y)))
      for (const t of poly.trous || []) shape.holes.push(new THREE.Path(t.map(([x, y]) => new THREE.Vector2(x, y))))
      const geo = new THREE.ExtrudeGeometry(shape, { depth: b.hauteur_m!, bevelEnabled: false })
      geo.rotateX(-Math.PI / 2); geo.translate(0, b.pied_m!, 0)
      grp.add(new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: 0xe6eaee, roughness: 0.85 })))   // teinte plus claire
      grp.add(new THREE.LineSegments(new THREE.EdgesGeometry(geo), new THREE.LineBasicMaterial({ color: 0x5a6066 })))   // arêtes nettement visibles
    } else {
      // A4 : sans pied/hauteur → CONTOUR posé sur les faces valides (jamais altitude arbitraire)
      grp.add(drapeLine([...poly.ext], elev, 0xaab0b6, 1.4, res))
    }
  }
  return grp
}

function Vue3D({ scene, axeSel, markerApi, onCote }: {
  scene: GabScene; axeSel: 'A' | 'B' | null
  markerApi: React.MutableRefObject<((f: number | null) => void) | null>
  onCote: (c: { hi: number; lo: number; cur: number | null; cap: number }) => void
}) {
  const host = useRef<HTMLDivElement>(null)
  const recentrer = useRef<() => void>(() => {})
  const toggleCn = useRef<() => void>(() => {})
  const photoApi = useRef<{ load: () => void; clear: () => void }>({ load: () => {}, clear: () => {} })
  const [photoStat, setPhotoStat] = useState<'off' | 'loading' | 'ok' | 'echec'>('off')
  const [photoCredit, setPhotoCredit] = useState('')
  const axeSelRef = useRef(axeSel); axeSelRef.current = axeSel
  const axisObjs = useRef<Record<string, THREE.Group>>({})
  const majLettresAxe = useRef<(lab: 'A' | 'B' | null) => void>(() => {})
  const [perdu, setPerdu] = useState(false)

  // changer de coupe ne recrée PAS le contexte : on recolore seulement l'axe (B9)
  useEffect(() => {
    for (const [lab, grp] of Object.entries(axisObjs.current)) {
      const sel = lab === axeSel
      grp.visible = sel                                  // seul l'axe sélectionné est affiché (2 quater)
      for (const o of grp.children) { const m = (o as Line2).material as LineMaterial; if (m) { m.color.set(0xe0a44a); m.linewidth = 2.6; m.needsUpdate = true } ;(o as Line2).renderOrder = 5 }
    }
    majLettresAxe.current(axeSel)                         // lettres B/B′ (ou A/A′) sur l'axe actif
  }, [axeSel])

  useEffect(() => {
    const el = host.current, faces = scene.terrain?.faces_parcelle
    if (!el || !faces || !faces.vertices.length) return
    const W = el.clientWidth || el.parentElement?.clientWidth || 800
    const H = el.clientHeight || el.parentElement?.clientHeight || 500
    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'low-power' })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); renderer.setSize(W, H)
    el.appendChild(renderer.domElement)
    const res = new THREE.Vector2(W * renderer.getPixelRatio(), H * renderer.getPixelRatio())
    const sc = new THREE.Scene(); sc.background = new THREE.Color('#0d0f12')
    // SONDES de mesure (lues par le test WebKit) : largeur projetée de la parcelle, périmètre cadastral,
    // point du marqueur (survol).
    const probe = { pf: 0, perim: 0, mx: 0, my: 0, mz: 0, mon: false, cadre: true, contourPct: 0 }
    for (const poly of scene.contour_cadastral) { const r = poly.ext; for (let i = 0; i < r.length - 1; i++) probe.perim += Math.hypot(r[i + 1][0] - r[i][0], r[i + 1][1] - r[i][1]) }

    const { mesh, box } = terrainMesh(faces, scene.contour_cadastral)
    sc.add(mesh)
    const elev = makeElev(mesh)                                   // raycast du maillage affiché (suit les faces)
    const zo = zoneOverlay(mesh, scene.zone_implantation, scene.terrain?.cadre || []); if (zo) sc.add(zo)   // masque par pixel
    const cn = contours(faces); const cnGroup = new THREE.Group(); cnGroup.add(cn.master); cnGroup.add(cn.minor); sc.add(cnGroup)
    toggleCn.current = () => { cnGroup.visible = !cnGroup.visible }
    // CONTOUR cadastral : POINTILLÉ discret derrière (depthTest off, tout le périmètre) + PLEIN blanc
    // dessus (depthTest on) → plein où VISIBLE, pointillé où le relief le CACHE.
    for (const poly of scene.contour_cadastral) {
      sc.add(drapeLine(poly.ext, elev, 0xcfd6dd, 1.4, res, true, true, false, 0.5, false, 2))   // caché (pointillé)
      sc.add(drapeLine(poly.ext, elev, 0xffffff, 3.2, res, false, true, true, 1, true, 4))       // visible (plein)
    }
    axisObjs.current = {}
    for (const [lab, a] of Object.entries(scene.axes_plan || {})) {
      const grp = drapeLine([a.p0, a.p1], elev, 0xe0a44a, 2.6, res, true)
      grp.visible = lab === axeSel; sc.add(grp); axisObjs.current[lab] = grp
    }
    for (const b of scene.batiments) sc.add(batiVolume(b, elev, res))

    sc.add(new THREE.AmbientLight(0xffffff, 0.55))
    const sun = new THREE.DirectionalLight(0xffffff, 0.85); sun.position.set(-1, 1.4, 1); sc.add(sun)   // nord-ouest

    // CADRAGE : tout le CONTOUR cadastral + les extrémités des axes (B/B′, A/A′) tiennent dans la vue, centrés
    // sur leur UNION → la pointe de la parcelle côté voie n'est plus coupée quand la coupe réduit la hauteur,
    // et les deux repères restent visibles (ouverture + Recentrer). probe.pf = largeur projetée de la parcelle.
    const bc = box.getCenter(new THREE.Vector3()), zmid = bc.y
    const framePts: THREE.Vector3[] = []
    let pminx = Infinity, pminy = Infinity, pmaxx = -Infinity, pmaxy = -Infinity
    for (const poly of scene.contour_cadastral) for (const [x, y] of poly.ext) {
      pminx = Math.min(pminx, x); pminy = Math.min(pminy, y); pmaxx = Math.max(pmaxx, x); pmaxy = Math.max(pmaxy, y)
      framePts.push(new THREE.Vector3(x, elev(x, y) ?? zmid, -y))
    }
    for (const a of Object.values(scene.axes_plan || {})) for (const p of [a.p0, a.p1]) framePts.push(new THREE.Vector3(p[0], elev(p[0], p[1]) ?? zmid, -p[1]))
    let uminx = Infinity, uminz = Infinity, umaxx = -Infinity, umaxz = -Infinity
    for (const v of framePts) { uminx = Math.min(uminx, v.x); umaxx = Math.max(umaxx, v.x); uminz = Math.min(uminz, v.z); umaxz = Math.max(umaxz, v.z) }
    const ctr = new THREE.Vector3((uminx + umaxx) / 2, zmid, (uminz + umaxz) / 2)
    const corners = [[pminx, pminy], [pmaxx, pminy], [pmaxx, pmaxy], [pminx, pmaxy]].map(([x, y]) => new THREE.Vector3(x, zmid, -y))
    let r = Math.max(umaxx - uminx, umaxz - uminz) * 0.8 + 3
    const cam = new THREE.OrthographicCamera(-r, r, r, -r, 0.1, 5000)
    const frustum = () => { const w = el.clientWidth || W, h = el.clientHeight || H, ar = w / h; cam.left = -r * ar; cam.right = r * ar; cam.top = r; cam.bottom = -r; cam.far = r * 50; cam.updateProjectionMatrix() }
    const place = () => {
      cam.position.set(ctr.x + r * 1.1, ctr.y + r * 1.25, ctr.z + r * 1.1); cam.lookAt(ctr); frustum()
      // ETUDE/B1 — CADRAGE RESSERRÉ : le point le plus ÉLOIGNÉ du cadrage (contour + B/B′) atteint ±0,92
      // (au lieu de 0,85) → la parcelle occupe plus de la vue, tout en gardant une marge de 8 % pour que
      // le contour entier, la voie et les repères B/B′ restent visibles (cadre testé à ±0,995 plus bas).
      const FIT = 0.92
      for (let it = 0; it < 6; it++) {
        let reach = 0                     // (sur la coordonnée NDC max → tient dans la vue même décentré par la 3/4)
        for (const c of framePts) { const p = c.clone().project(cam); reach = Math.max(reach, Math.abs(p.x), Math.abs(p.y)) }
        if (!isFinite(reach) || reach <= 0) break
        r *= reach / FIT; cam.position.set(ctr.x + r * 1.1, ctr.y + r * 1.25, ctr.z + r * 1.1); cam.lookAt(ctr); frustum()
        if (Math.abs(reach - FIT) < 0.03) break
      }
      // sonde : largeur projetée de la PARCELLE (contour) + tout le cadrage dans la vue (pt 2)
      let u0 = Infinity, u1 = -Infinity, dans = true
      for (const c of corners) { const v = c.clone().project(cam); u0 = Math.min(u0, v.x); u1 = Math.max(u1, v.x) }
      for (const c of framePts) { const p = c.clone().project(cam); if (Math.abs(p.x) > 0.995 || Math.abs(p.y) > 0.995) { dans = false; break } }
      probe.pf = (u1 - u0) / 2; probe.cadre = dans
      // B1 — PART DE LA VUE occupée par le CONTOUR cadastral (bbox écran du contour ÷ vue), mesurée au
      // cadrage (ouverture ET Recentrer appellent place()). Doit augmenter quand on resserre.
      let cx0 = Infinity, cx1 = -Infinity, cy0 = Infinity, cy1 = -Infinity
      for (const poly of scene.contour_cadastral) for (const [x, y] of poly.ext) {
        const v = new THREE.Vector3(x, elev(x, y) ?? zmid, -y).project(cam)
        cx0 = Math.min(cx0, v.x); cx1 = Math.max(cx1, v.x); cy0 = Math.min(cy0, v.y); cy1 = Math.max(cy1, v.y)
      }
      probe.contourPct = Math.round(((cx1 - cx0) / 2) * ((cy1 - cy0) / 2) * 1000) / 10   // % de l'aire de la vue
    }
    place()
    const controls = new OrbitControls(cam, renderer.domElement); controls.target.copy(ctr); controls.update()
    recentrer.current = () => { place(); controls.target.copy(ctr); controls.update() }

    // repères haut/bas SUR leurs points (3D→écran) + boussole
    let hiP = new THREE.Vector3(), loP = new THREE.Vector3(), hi = -Infinity, lo = Infinity
    for (const p of faces.vertices) if (inPolys(p[0], p[1], scene.contour_cadastral)) {
      if (p[2] > hi) { hi = p[2]; hiP.set(p[0], p[2], -p[1]) }
      if (p[2] < lo) { lo = p[2]; loP.set(p[0], p[2], -p[1]) }
    }
    onCote({ hi: Math.round(hi * 10) / 10, lo: Math.round(lo * 10) / 10, cur: null, cap: Math.round(hi * 10) / 10 })

    const ray = new THREE.Raycaster(), ndc = new THREE.Vector2()
    const marker = new THREE.Mesh(new THREE.SphereGeometry(1.0, 14, 10), new THREE.MeshBasicMaterial({ color: 0xffd36a }))
    marker.visible = false; marker.renderOrder = 6; sc.add(marker)
    const onMove = (ev: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect()
      ndc.set(((ev.clientX - rect.left) / rect.width) * 2 - 1, -((ev.clientY - rect.top) / rect.height) * 2 + 1)
      ray.setFromCamera(ndc, cam); const h = ray.intersectObject(mesh)
      onCote({ hi: Math.round(hi * 10) / 10, lo: Math.round(lo * 10) / 10, cur: h[0] ? Math.round(h[0].point.y * 10) / 10 : null, cap: Math.round(hi * 10) / 10 })
    }
    renderer.domElement.addEventListener('mousemove', onMove)
    markerApi.current = (frac) => {
      const a = axeSelRef.current ? scene.axes_plan?.[axeSelRef.current] : null
      if (frac == null || !a) { marker.visible = false; return }
      const x = a.p0[0] + (a.p1[0] - a.p0[0]) * frac, y = a.p0[1] + (a.p1[1] - a.p0[1]) * frac, z = elev(x, y)
      if (z != null) { marker.position.set(x, z + 0.6, -y); marker.visible = true; probe.mx = x; probe.my = y; probe.mz = z; probe.mon = true }
      else { marker.visible = false; probe.mon = false }
    }

    // A1 — AUDIT de la zone d'implantation (lu par le test WebKit) : on projette le polygone de la zone
    // à l'écran, on relit le framebuffer, et on compte les pixels VERTS dedans (teinte #2f9e6a, nettement
    // plus saturée que la rampe du terrain) vs dehors. Rendu immédiat avant lecture (buffer frais).
    ;(window as unknown as Record<string, unknown>).__gab3dZoneAudit = () => {
      const zpolys = scene.zone_implantation || []
      if (!zpolys.length) return { zone: false }
      renderer.render(sc, cam)
      const gl = renderer.getContext(), Wc = renderer.domElement.width, Hc = renderer.domElement.height
      const buf = new Uint8Array(Wc * Hc * 4); gl.readPixels(0, 0, Wc, Hc, gl.RGBA, gl.UNSIGNED_BYTE, buf)
      const projRing = (ring: number[][], dz: number) => ring.map(([x, y]) => { const z = elev(x, y); if (z == null) return null; const v = new THREE.Vector3(x, z + dz, -y).project(cam); return [(v.x * 0.5 + 0.5) * Wc, (v.y * 0.5 + 0.5) * Hc] as [number, number] }).filter(Boolean) as [number, number][]
      const polyScreens = zpolys.map((poly) => [poly.ext, ...(poly.trous || [])].map((ring) => projRing(ring, 0)).filter((r) => r.length >= 3))
      // bâti OPAQUE dans la zone : SILHOUETTE complète (enveloppe convexe de l'empreinte au pied ET au
      // faîtage → couvre aussi les MURS du volume) EXCLUE du dénominateur. Le critère porte sur la surface
      // de la zone VISIBLE, pas sur le bâti qui s'y pose et la masque légitimement.
      const hull = (pts: [number, number][]): [number, number][] => { if (pts.length < 3) return pts; const p = [...pts].sort((a, b) => a[0] - b[0] || a[1] - b[1]); const cr = (o: number[], a: number[], b: number[]) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]); const lo: [number, number][] = [], up: [number, number][] = []; for (const q of p) { while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], q) <= 0) lo.pop(); lo.push(q) } for (let i = p.length - 1; i >= 0; i--) { const q = p[i]; while (up.length >= 2 && cr(up[up.length - 2], up[up.length - 1], q) <= 0) up.pop(); up.push(q) } return lo.slice(0, -1).concat(up.slice(0, -1)) }
      const batiScreens: [number, number][][] = []
      for (const bt of scene.batiments || []) { const hh = (bt as { volume?: boolean }).volume && bt.hauteur_m ? bt.hauteur_m : 0; const pts: [number, number][] = []; for (const poly of bt.empreinte || []) for (const dz of hh ? [0, hh] : [0]) pts.push(...projRing(poly.ext, dz)); const h = hull(pts); if (h.length >= 3) batiScreens.push(h) }
      const inRings = (rings: [number, number][][], px: number, py: number) => { let c = false; for (const r of rings) for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const [xi, yi] = r[i], [xj, yj] = r[j]; if ((yi > py) !== (yj > py) && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) c = !c } return c }
      const inZone = (px: number, py: number) => polyScreens.some((rings) => inRings(rings, px, py))
      const inBati = (px: number, py: number) => batiScreens.some((r) => inRings([r], px, py))
      // « dehors » = CLAIREMENT hors zone : au-delà d'une bande de garde de 5 px (le masque est peint au
      // pixel sur la surface courbe ; mon polygone-écran est une approximation des sommets → bord flou).
      const G = 5
      const clairDehors = (px: number, py: number) => !inZone(px, py) && !inZone(px + G, py) && !inZone(px - G, py) && !inZone(px, py + G) && !inZone(px, py - G)
      let inTot = 0, inGreen = 0, outGreen = 0, inBatiN = 0
      for (let py = 0; py < Hc; py += 4) for (let px = 0; px < Wc; px += 4) {
        const o = (py * Wc + px) * 4, r = buf[o], g = buf[o + 1], b = buf[o + 2]
        const green = g - r > 34 && g - b > 15 && g > 85
        if (inZone(px, py)) { if (inBati(px, py)) { inBatiN++; continue } inTot++; if (green) inGreen++ } else if (green && clairDehors(px, py)) outGreen++
      }
      return { zone: true, inside_green_pct: inTot ? Math.round((inGreen / inTot) * 1000) / 10 : 0, inside_tot: inTot, bati_exclu: inBatiN, outside_green: outGreen }
    }

    // étiquettes HTML posées (hi/bas + boussole) mises à jour dans la boucle
    const lay = document.createElement('div'); lay.style.cssText = 'position:absolute;inset:0;pointer-events:none;font:600 10px Inter,sans-serif'
    el.appendChild(lay)
    const mkLab = (txt: string, col: string) => { const d = document.createElement('div'); d.textContent = txt; d.style.cssText = `position:absolute;color:${col};transform:translate(-50%,-50%);text-shadow:0 1px 2px #000` ; lay.appendChild(d); return d }
    const lHi = mkLab(`${hi.toFixed(1).replace('.', ',')} m`, '#e8edf2')      // une décimale (409,8 m)
    const lLo = mkLab(`${lo.toFixed(1).replace('.', ',')} m`, '#e8edf2')
    // B2 (point conservé) — chaque cote garde son POINT : une PASTILLE au point mesuré + un FILET fin vers
    // l'étiquette (SVG derrière les libellés). L'étiquette reste à ≤ 40 px du point, sur le terrain.
    const _svgns = 'http://www.w3.org/2000/svg'
    const guide = document.createElementNS(_svgns, 'svg')
    guide.setAttribute('style', 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;overflow:visible')
    lay.insertBefore(guide, lay.firstChild)
    const mkGuide = () => {
      const line = document.createElementNS(_svgns, 'line'); line.setAttribute('stroke', '#cdd4db'); line.setAttribute('stroke-width', '1'); line.setAttribute('opacity', '0.9'); line.style.display = 'none'
      const ring = document.createElementNS(_svgns, 'circle'); ring.setAttribute('r', '3.4'); ring.setAttribute('fill', '#ffd36a'); ring.setAttribute('stroke', '#14171a'); ring.setAttribute('stroke-width', '1.2')
      guide.appendChild(line); guide.appendChild(ring); return { line, ring }
    }
    const gHi = mkGuide(), gLo = mkGuide()
    const _segHitsBox = (a: [number, number], b: [number, number], x0: number, y0: number, x1: number, y1: number) => {
      const inside = (px: number, py: number) => px >= x0 && px <= x1 && py >= y0 && py <= y1
      if (inside(a[0], a[1]) || inside(b[0], b[1])) return true
      const cross = (p1: number[], p2: number[], p3: number[], p4: number[]) => {
        const dn = (p4[0] - p3[0]) * (p2[1] - p1[1]) - (p4[1] - p3[1]) * (p2[0] - p1[0]); if (!dn) return false
        const u = ((p4[0] - p3[0]) * (p1[1] - p3[1]) - (p4[1] - p3[1]) * (p1[0] - p3[0])) / dn
        const w = ((p2[0] - p1[0]) * (p1[1] - p3[1]) - (p2[1] - p1[1]) * (p1[0] - p3[0])) / dn
        return u >= 0 && u <= 1 && w >= 0 && w <= 1
      }
      return cross(a, b, [x0, y0], [x1, y0]) || cross(a, b, [x1, y0], [x1, y1]) || cross(a, b, [x1, y1], [x0, y1]) || cross(a, b, [x0, y1], [x0, y0])
    }
    // B2 (corrigé) — contour DRAPÉ (suit le relief, ~1,5 m) + SILHOUETTES du bâti (empreinte au pied ET au
    // faîtage → couvre les murs), précalculés en MONDE une fois (makeElev = raycast, coûteux), reprojetés
    // par frame. Le placement les évite ; l'audit teste le contour AU PIXEL (trait réel) + le bâti en géométrie.
    const _contourDrapedW: THREE.Vector3[][] = []
    for (const poly of scene.contour_cadastral) {
      const pts: THREE.Vector3[] = [], rr = poly.ext
      for (let i = 0; i < rr.length - 1; i++) {
        const [x0, y0] = rr[i], [x1, y1] = rr[i + 1], n = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0) / 0.5))
        for (let k = 0; k < n; k++) { const t = k / n, x = x0 + (x1 - x0) * t, y = y0 + (y1 - y0) * t; pts.push(new THREE.Vector3(x, elev(x, y) ?? zmid, -y)) }
      }
      if (rr.length) { const [x, y] = rr[rr.length - 1]; pts.push(new THREE.Vector3(x, elev(x, y) ?? zmid, -y)) }
      _contourDrapedW.push(pts)
    }
    // silhouettes bâti = anneaux RÉELS de l'empreinte au pied ET au faîtage (pas l'enveloppe convexe, qui
    // sur-couvrait les bâtis en L et bloquait trop d'espace) → test plus serré, plus de place pour les cotes.
    const _batiHullW: THREE.Vector3[][] = []
    for (const bt of scene.batiments || []) {
      const bh = (bt as { volume?: boolean }).volume && bt.hauteur_m ? bt.hauteur_m : 0
      for (const poly of bt.empreinte || []) {
        const pied = poly.ext.map(([x, y]) => new THREE.Vector3(x, elev(x, y) ?? zmid, -y))
        if (pied.length >= 3) _batiHullW.push(pied)
        if (bh) { const toit = poly.ext.map(([x, y]) => new THREE.Vector3(x, (elev(x, y) ?? zmid) + bh, -y)); if (toit.length >= 3) _batiHullW.push(toit) }
      }
    }
    const _px = (v: THREE.Vector3): [number, number] => { const p = v.clone().project(cam); return [(p.x * 0.5 + 0.5) * el.clientWidth, (-p.y * 0.5 + 0.5) * el.clientHeight] }
    const _contourSegsDraped = (): [[number, number], [number, number]][] => { const s: [[number, number], [number, number]][] = []; for (const pts of _contourDrapedW) { const pr = pts.map(_px); for (let i = 0; i < pr.length - 1; i++) s.push([pr[i], pr[i + 1]]) } return s }
    const _batiPolysPx = (): [number, number][][] => _batiHullW.map((pts) => pts.map(_px)).filter((p) => p.length >= 3)
    // EMPRISE RÉELLE du maillage (pas le cadre serré) projetée → quad écran : « sur le terrain » = à
    // l'intérieur. Le maillage déborde la parcelle (~25 m) → une étiquette peut se poser JUSTE à l'extérieur
    // du contour, sur le terrain alentour, sans le toucher. (L'audit vérifie au pixel que le fond n'est pas noir.)
    const _terrW = [[box.min.x, box.min.z], [box.max.x, box.min.z], [box.max.x, box.max.z], [box.min.x, box.max.z]]
      .map(([x, z]) => new THREE.Vector3(x, zmid, z))
    const _cadreQuadPx = (): [number, number][] => _terrW.map(_px)
    const _ptInPoly = (px: number, py: number, poly: [number, number][]) => { let c = false; for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) { const [xi, yi] = poly[i], [xj, yj] = poly[j]; if ((yi > py) !== (yj > py) && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) c = !c } return c }
    // boîte ↔ polygone. MONOTONE sous agrandissement (le centre reste le même, pas de test « coin DANS le
    // polygone » qui sortait quand on inflate) : sommet du polygone dans la boîte, OU centre de la boîte dans
    // le polygone, OU une arête du polygone traverse la boîte.
    const _polyHitsBox = (poly: [number, number][], x0: number, y0: number, x1: number, y1: number) => {
      for (const [px, py] of poly) if (px >= x0 && px <= x1 && py >= y0 && py <= y1) return true
      if (_ptInPoly((x0 + x1) / 2, (y0 + y1) / 2, poly)) return true
      for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) if (_segHitsBox(poly[j], poly[i], x0, y0, x1, y1)) return true
      return false
    }
    const _BMARGE = 3   // petite marge autour du bâti (anti-alias du volume) ; appliquée au placement ET à l'audit
    const _HALO = 4, _LINE = 3   // halo du texte (text-shadow) + demi-épaisseur du trait du contour à l'écran
    // AUDIT (harnais) — PREUVE au PIXEL : on lit le rendu sous la boîte RÉELLE du texte (halo compris) et on
    // compte les pixels du CONTOUR BLANC (trait à son épaisseur réelle) ; la SILHOUETTE du bâti est testée
    // géométriquement (toutes ses faces, quel que soit l'ombrage). `traverse` = contour OU bâti.
    ;(window as unknown as Record<string, unknown>).__gab3dCotesAudit = () => {
      renderer.render(sc, cam)
      const gl = renderer.getContext(), Wc = renderer.domElement.width, Hc = renderer.domElement.height
      const buf = new Uint8Array(Wc * Hc * 4); gl.readPixels(0, 0, Wc, Hc, gl.RGBA, gl.UNSIGNED_BYTE, buf)
      const dpr = renderer.getPixelRatio(), polys = _batiPolysPx(), elR = el.getBoundingClientRect()
      const nonNoir = (lx: number, ly: number) => { const fx = Math.round(lx * dpr), fy = Math.round(ly * dpr); if (fx < 0 || fx >= Wc || fy < 0 || fy >= Hc) return false; const o = ((Hc - 1 - fy) * Wc + fx) * 4; return Math.max(buf[o], buf[o + 1], buf[o + 2]) >= 16 }
      const test = (d: HTMLDivElement, g: { ring: SVGCircleElement }) => {
        if (d.style.display === 'none') return { contour: false, bati: false, dist: 0, sur_terrain: true, ok: true }
        const r = d.getBoundingClientRect()
        const x0 = r.left - elR.left - _HALO, y0 = r.top - elR.top - _HALO, x1 = r.right - elR.left + _HALO, y1 = r.bottom - elR.top + _HALO
        const bati = polys.some((p) => _polyHitsBox(p, x0 - _BMARGE, y0 - _BMARGE, x1 + _BMARGE, y1 + _BMARGE))
        let white = 0
        const fx0 = Math.max(0, Math.floor(x0 * dpr)), fx1 = Math.min(Wc - 1, Math.ceil(x1 * dpr))
        const fy0 = Math.max(0, Math.floor(y0 * dpr)), fy1 = Math.min(Hc - 1, Math.ceil(y1 * dpr))
        for (let yy = fy0; yy <= fy1; yy++) for (let xx = fx0; xx <= fx1; xx++) {
          const o = ((Hc - 1 - yy) * Wc + xx) * 4, R = buf[o], G = buf[o + 1], B = buf[o + 2]
          const mn = Math.min(R, G, B), mx = Math.max(R, G, B)
          if (mn >= 215 && mx - mn <= 30) white++
        }
        const lx = (x0 + x1) / 2, ly = (y0 + y1) / 2
        const pxp = parseFloat(g.ring.getAttribute('cx') || 'NaN'), pyp = parseFloat(g.ring.getAttribute('cy') || 'NaN')
        // distance = du point au BORD le plus proche de l'étiquette (le filet), pas au centre
        const ex = Math.min(Math.max(pxp, x0), x1), ey = Math.min(Math.max(pyp, y0), y1)
        const dist = Math.round(Math.hypot(ex - pxp, ey - pyp))
        const contour = white >= 2, sur = nonNoir(lx, ly)
        // les TROIS règles : ni contour/bâti traversés, ≤ 40 px du point, étiquette sur le terrain
        return { contour, bati, dist, sur_terrain: sur, ok: !contour && !bati && dist <= 80 && sur }
      }
      const H = test(lHi, gHi), L = test(lLo, gLo)
      return { hi: lHi.textContent, lo: lLo.textContent, hi_traverse: H.contour || H.bati, lo_traverse: L.contour || L.bati, hi_detail: H, lo_detail: L, ok: H.ok && L.ok }
    }
    // lettres de l'axe actif (B et B′, A et A′) posées aux EXTRÉMITÉS VISIBLES du trait orange
    const lAx0 = mkLab('', '#f0b24a'); const lAx1 = mkLab('', '#f0b24a')
    lAx0.style.font = lAx1.style.font = '700 13px Inter,sans-serif'
    // échantillons DRAPÉS de l'axe (ordre p0→p1) ; la lettre est posée au dernier point VISIBLE (dans la vue)
    const axEnd: { pts: THREE.Vector3[]; on: boolean } = { pts: [], on: false }
    majLettresAxe.current = (lab) => {
      const a = lab ? scene.axes_plan?.[lab] : null
      axEnd.pts = []
      if (!a) { axEnd.on = false; lAx0.style.display = lAx1.style.display = 'none'; return }
      for (let i = 0; i <= 64; i++) { const t = i / 64, x = a.p0[0] + (a.p1[0] - a.p0[0]) * t, y = a.p0[1] + (a.p1[1] - a.p0[1]) * t, z = elev(x, y); if (z != null) axEnd.pts.push(new THREE.Vector3(x, z + 0.6, -y)) }
      if (axEnd.pts.length >= 2) { axEnd.on = true; lAx0.textContent = lab; lAx1.textContent = `${lab}′` }
      else { axEnd.on = false; lAx0.style.display = lAx1.style.display = 'none' }
    }
    majLettresAxe.current(axeSelRef.current)
    // pose une lettre au 1ᵉʳ point visible depuis `from` (balayage vers `to`) — dans le cadre, jamais hors vue
    const poseLettre = (el2: HTMLDivElement, from: number, to: number) => {
      const step = from < to ? 1 : -1
      for (let i = from; step > 0 ? i <= to : i >= to; i += step) {
        const v = axEnd.pts[i].clone().project(cam)
        if (v.z < 1 && Math.abs(v.x) <= 0.98 && Math.abs(v.y) <= 0.98) {
          el2.style.display = 'block'; el2.style.left = `${(v.x * 0.5 + 0.5) * el.clientWidth}px`; el2.style.top = `${(-v.y * 0.5 + 0.5) * el.clientHeight}px`; return
        }
      }
      el2.style.display = 'none'
    }
    const compass = document.createElement('div')
    compass.innerHTML = '<svg width="34" height="34" viewBox="0 0 34 34"><circle cx="17" cy="17" r="15" fill="rgba(0,0,0,.4)" stroke="#5b6670"/><g id="nd"><path d="M17 4 L20 17 L17 15 L14 17 Z" fill="#e0a44a"/><text x="17" y="30" text-anchor="middle" font-size="8" fill="#cbd5e1">N</text></g></svg>'
    compass.style.cssText = 'position:absolute;right:8px;top:8px'; lay.appendChild(compass)
    const nd = compass.querySelector('#nd') as SVGGElement
    // B2 — centre (monde) du contour, pour DÉCALER les cotes vers l'INTÉRIEUR, HORS du contour ET du bâti.
    let _ccx = 0, _ccy = 0, _ccn = 0
    for (const poly of scene.contour_cadastral) for (const [x, y] of poly.ext) { _ccx += x; _ccy += y; _ccn++ }
    const coteCtrW = new THREE.Vector3(_ccn ? _ccx / _ccn : bc.x, zmid, _ccn ? -_ccy / _ccn : bc.z)
    // boîte (texte réel + halo) BLOQUÉE par le contour drapé OU une silhouette de bâti ? La boîte de test
    // est la boîte de l'AUDIT (texte + _HALO) + une petite marge `_PMARGE` = demi-épaisseur du trait à
    // l'écran + anti-alias : juste assez pour épouser le trait RÉEL, sans sur-bloquer (sinon aucune position
    // ne tiendrait dans les 40 px près d'un sommet de bord).
    // marge CONTOUR du placement = halo + épaisseur du trait + anti-alias : SUR-COUVRE la portée réelle du
    // trait blanc vue par l'audit (pixels blancs ±3 px autour de la ligne) → si le placement dégage, l'audit
    // dégage aussi (plus de « placement se croit clair, audit voit le trait » à courte distance).
    const _CMARGE = _LINE + 3
    const _blocked = (sx: number, sy: number, w: number, h: number, segs: [[number, number], [number, number]][], polys: [number, number][][]) => {
      const x0 = sx - w / 2, y0 = sy - h / 2, x1 = sx + w / 2, y1 = sy + h / 2
      // CONTOUR (trait fin) : on épaissit la boîte de _CMARGE pour épouser le trait à l'écran.
      if (segs.some((s) => _segHitsBox(s[0], s[1], x0 - _CMARGE, y0 - _CMARGE, x1 + _CMARGE, y1 + _CMARGE))) return true
      // BÂTI (polygone plein) : petite marge _BMARGE (anti-alias), test monotone → identique à l'audit.
      return polys.some((p) => _polyHitsBox(p, x0 - _BMARGE, y0 - _BMARGE, x1 + _BMARGE, y1 + _BMARGE))
    }
    // L'étiquette reste ATTACHÉE à son point : pastille au point, étiquette à ≤ 40 px (préférence intérieur
    // + sur le terrain), filet fin si écart. On essaie 8 directions × distances CROISSANTES bornées à 40 px,
    // on retient la plus PROCHE qui dégage le contour + le bâti ET reste sur le terrain. Si rien ne tient en
    // 40 px, on place au mieux (le plus proche dégagé) — l'audit SIGNALERA la taille en échec (pas de forçage).
    // Drapeau debug `__gab3dRawCotes` : pose l'étiquette AU POINT BRUT (sert à prouver que l'audit détecte).
    const _MAXD = 80   // le DÉGAGEMENT prime sur la distance : on écarte jusqu'à 80 px pour ne rien toucher
    const proj = (p: THREE.Vector3, d: HTMLDivElement, g: { line: SVGLineElement; ring: SVGCircleElement }, segs: [[number, number], [number, number]][], polys: [number, number][][], quad: [number, number][] | null) => {
      const v = p.clone().project(cam); const vis = v.z < 1
      d.style.display = vis ? 'block' : 'none'; g.ring.style.display = vis ? 'block' : 'none'
      if (!vis) { g.line.style.display = 'none'; return }
      const px = (v.x * 0.5 + 0.5) * el.clientWidth, py = (-v.y * 0.5 + 0.5) * el.clientHeight
      g.ring.setAttribute('cx', `${px}`); g.ring.setAttribute('cy', `${py}`)
      if ((window as unknown as Record<string, unknown>).__gab3dRawCotes) { d.style.left = `${px}px`; d.style.top = `${py}px`; g.line.style.display = 'none'; return }
      const c = coteCtrW.clone().project(cam); const cx = (c.x * 0.5 + 0.5) * el.clientWidth, cy = (-c.y * 0.5 + 0.5) * el.clientHeight
      const dx = cx - px, dy = cy - py, nn = Math.hypot(dx, dy) || 1, ux = dx / nn, uy = dy / nn
      const w = (d.offsetWidth || 44) + _HALO * 2, h = (d.offsetHeight || 14) + _HALO * 2
      const onTerr = (sx: number, sy: number) => !quad || _ptInPoly(sx, sy, quad)
      // « ≤ 40 px » porte sur le FILET = distance du point au BORD le plus proche de l'étiquette (pas au
      // centre) : la boîte peut donc s'écarter assez pour dégager le contour tout en restant RELIÉE de près.
      const nearEdge = (sx: number, sy: number) => { const ex = Math.min(Math.max(px, sx - w / 2), sx + w / 2), ey = Math.min(Math.max(py, sy - h / 2), sy + h / 2); return Math.hypot(ex - px, ey - py) }
      const dirs: [number, number][] = [[ux, uy]]
      for (let k = 0; k < 24; k++) { const a = (k * Math.PI) / 12; dirs.push([Math.cos(a), Math.sin(a)]) }
      // on SCORE chaque candidat : dégagé + sur-terrain + filet court + intérieur gagnent ; contour/bâti et
      // hors-terrain sont de GROSSES pénalités → on prend le MOINS mauvais (si aucun n'est parfait, l'audit
      // le signale, on ne force pas une fausse réussite). Le centre va jusqu'à 40 + demi-boîte ; le filet ≤ 40.
      let sx = px + ux * (h / 2 + _CMARGE + 2), sy = py + uy * (h / 2 + _CMARGE + 2), bestCost = Infinity
      for (let dist = 10; dist <= _MAXD + Math.max(w, h) / 2 + 4; dist += 2) for (const [dux, duy] of dirs) {
        const tx = px + dux * dist, ty = py + duy * dist
        const ne = nearEdge(tx, ty)
        if (ne < 1 || ne > _MAXD) continue   // ni sur la pastille, ni au-delà de 80 px (filet)
        // contour, bâti ET fond noir sont INTERDITS à égalité → une position dégagée gagne toujours sur une
        // position courte mais en collision ; parmi les dégagées, la plus PROCHE (puis intérieure) gagne.
        const pen = (_blocked(tx, ty, w, h, segs, polys) ? 1000 : 0) + (onTerr(tx, ty) ? 0 : 1000)
        const cost = pen + ne + (1 - (dux * ux + duy * uy)) * 10
        if (cost < bestCost) { bestCost = cost; sx = tx; sy = ty }
      }
      d.style.left = `${sx}px`; d.style.top = `${sy}px`
      // filet : du point jusqu'au BORD de la boîte, seulement s'il y a un écart visible
      const ax = Math.min(Math.max(px, sx - w / 2), sx + w / 2), ay = Math.min(Math.max(py, sy - h / 2), sy + h / 2)
      if (Math.hypot(ax - px, ay - py) > 3) {
        g.line.setAttribute('x1', `${px}`); g.line.setAttribute('y1', `${py}`); g.line.setAttribute('x2', `${ax}`); g.line.setAttribute('y2', `${ay}`); g.line.style.display = 'block'
      } else g.line.style.display = 'none'
    }

    // B — PHOTO AÉRIENNE : fond facultatif, chargé AU CLIC (jamais à l'ouverture), demandé AU SERVEUR
    // (le navigateur ne contacte pas l'IGN), drapé sur la géométrie du terrain SOUS les calques (contour,
    // zone, bâti, axe, repères restent au-dessus et lisibles). Délai > 3 s ou échec → on reste en relief.
    // On DRAPE la photo en remplaçant le matériau du terrain (surface exacte, sans z-fight). Le relief reste
    // porté par la géométrie ; les calculs (relief, marqueur) continuent de viser le même maillage.
    let photoMat: THREE.MeshBasicMaterial | null = null, photoFlag = ''
    const tmesh = mesh as unknown as { material: THREE.Material }   // matériau permutable (photo ↔ relief)
    const origMat = tmesh.material
    const cadrePhoto = scene.terrain?.cadre
    photoApi.current = {
      load: async () => {
        if (photoMat || !cadrePhoto) return
        setPhotoStat('loading')
        const ctrl = new AbortController(); const to = setTimeout(() => ctrl.abort(), 3000)
        try {
          const resp = await fetch(gabOrthoUrl(scene.idu, scene.scene_id), { signal: ctrl.signal })
          clearTimeout(to)
          if (!resp.ok) throw new Error('indisponible')
          const mil = resp.headers.get('X-Ortho-Millesime') || '', src = resp.headers.get('X-Ortho-Source') || 'IGN'
          const url = URL.createObjectURL(await resp.blob())
          const tex = await new Promise<THREE.Texture>((ok, ko) => new THREE.TextureLoader().load(url, (t) => { URL.revokeObjectURL(url); ok(t) }, undefined, () => { URL.revokeObjectURL(url); ko(new Error('texture')) }))
          tex.colorSpace = THREE.SRGBColorSpace
          const geo = mesh.geometry as THREE.BufferGeometry
          if (!geo.getAttribute('uv')) {   // UV MONDE sur le cadre (une seule fois)
            const [minx, miny, maxx, maxy] = cadrePhoto, W = maxx - minx, H = maxy - miny
            const p = geo.getAttribute('position'), uv = new Float32Array(p.count * 2)
            for (let i = 0; i < p.count; i++) { uv[i * 2] = (p.getX(i) - minx) / W; uv[i * 2 + 1] = (-p.getZ(i) - miny) / H }
            geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2))
          }
          photoMat = new THREE.MeshBasicMaterial({ map: tex, side: THREE.DoubleSide })
          tmesh.material = photoMat
          photoFlag = 'ok'; setPhotoCredit(`${src}${mil ? ` · ${mil}` : ''}`); setPhotoStat('ok')
        } catch { clearTimeout(to); photoFlag = 'echec'; setPhotoStat('echec') }
      },
      clear: () => {
        if (photoMat) { tmesh.material = origMat; photoMat.map?.dispose(); photoMat.dispose(); photoMat = null }
        photoFlag = ''; setPhotoStat('off')
      },
    }

    let raf = 0, stop = false, first = 0, info = { geometries: 0, textures: 0 }
    const loop = () => {
      if (stop) return
      controls.update(); renderer.render(sc, cam)
      if (!first) first = performance.now()
      const coteSegs = _contourSegsDraped(), cotePolys = _batiPolysPx(), coteQuad = _cadreQuadPx(); proj(hiP, lHi, gHi, coteSegs, cotePolys, coteQuad); proj(loP, lLo, gLo, coteSegs, cotePolys, coteQuad)
      // lettres de l'axe : 1ʳᵉ posée au 1ᵉʳ point visible côté p0, 2ᵉ au dernier point visible côté p1
      if (axEnd.on) { const n = axEnd.pts.length - 1; poseLettre(lAx0, 0, n); poseLettre(lAx1, n, 0) }
      const az = controls.getAzimuthalAngle(); nd.setAttribute('transform', `rotate(${(-az * 180 / Math.PI).toFixed(1)} 17 17)`)
      info = { geometries: renderer.info.memory.geometries, textures: renderer.info.memory.textures }
      ;(window as unknown as Record<string, unknown>).__gab3d = { first, info, fps: renderer.info.render.frame, probe, photo: photoFlag }
      raf = requestAnimationFrame(loop)
    }
    loop()
    const onResize = () => { const w = el.clientWidth, h = el.clientHeight; if (w < 2 || h < 2) return; renderer.setSize(w, h); res.set(w * renderer.getPixelRatio(), h * renderer.getPixelRatio()); place() }
    window.addEventListener('resize', onResize); const ro = new ResizeObserver(onResize); ro.observe(el)
    const onLost = (e: Event) => { e.preventDefault(); stop = true; cancelAnimationFrame(raf); setPerdu(true) }
    renderer.domElement.addEventListener('webglcontextlost', onLost)

    return () => {
      stop = true; cancelAnimationFrame(raf); window.removeEventListener('resize', onResize); ro.disconnect()
      renderer.domElement.removeEventListener('mousemove', onMove); renderer.domElement.removeEventListener('webglcontextlost', onLost)
      markerApi.current = null; majLettresAxe.current = () => {}; controls.dispose(); el.removeChild(lay)
      photoApi.current = { load: () => {}, clear: () => {} }
      if (photoMat) origMat.dispose()                 // matériau d'origine détaché pendant la photo → libéré
      sc.traverse((o) => { const m = o as THREE.Mesh; if (m.geometry) m.geometry.dispose(); const mt = m.material as (THREE.Material & { map?: THREE.Texture }) | (THREE.Material & { map?: THREE.Texture })[] | undefined; const dm = (x: THREE.Material & { map?: THREE.Texture }) => { x.map?.dispose(); x.dispose() }; if (Array.isArray(mt)) mt.forEach(dm); else if (mt) dm(mt) })
      renderer.dispose(); renderer.forceContextLoss(); if (renderer.domElement.parentElement === el) el.removeChild(renderer.domElement)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scene])

  return (
    <div className="relative h-full w-full">
      <div ref={host} className="h-full w-full" data-gab3d-canvas />
      {perdu && <div data-gab3d-fallback className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/85 p-6 text-center text-[12px] text-txt-mut">
        <p>Contexte WebGL perdu — repli sur le plan et les coupes.</p>
        <img src={gabPlanSvgUrl(scene.idu, 'sombre', scene.scene_id)} alt="Plan-clé" className="max-w-[360px]" />
      </div>}
      <div className="absolute left-3 top-3 flex gap-2">
        <button data-gab3d-recentrer onClick={() => recentrer.current()} className="rounded border border-line bg-black/50 px-2 py-1 text-[11px] text-txt-mut hover:text-txt">◎ Recentrer</button>
        <button data-gab3d-courbes onClick={() => toggleCn.current()} className="rounded border border-line bg-black/50 px-2 py-1 text-[11px] text-txt-mut hover:text-txt">Courbes de niveau</button>
        <button data-gab3d-photo
          onClick={() => (photoStat === 'ok' ? photoApi.current.clear() : photoApi.current.load())}
          className={`rounded border px-2 py-1 text-[11px] ${photoStat === 'ok' ? 'border-mint/50 bg-mint/20 text-mint' : 'border-line bg-black/50 text-txt-mut hover:text-txt'}`}>
          {photoStat === 'loading' ? 'Photo…' : photoStat === 'ok' ? 'Photo aérienne ✓' : 'Photo aérienne'}
        </button>
      </div>
      {photoStat === 'ok' && photoCredit && (
        <div data-gab3d-credit className="absolute bottom-2 left-3 rounded bg-black/55 px-2 py-0.5 text-[10px] text-txt-mut">© {photoCredit}</div>
      )}
      {photoStat === 'echec' && (
        <div data-gab3d-photo-echec className="absolute bottom-2 left-3 rounded bg-black/55 px-2 py-0.5 text-[10px] text-txt-ghost">Photo aérienne indisponible — vue en relief conservée.</div>
      )}
    </div>
  )
}

const LEG = [['#ffffff', 'Limite cadastrale'], ['#2f9e6a', 'Zone d\'implantation au sol'], ['#cdd3d8', 'Bâti schématique · BD TOPO'], ['#e0a44a', 'Axe de la coupe active']] as const

export function GabaritViewer3D({ idu, onClose }: { idu: string; onClose: () => void }) {
  const q = useQuery({ queryKey: ['gabarit-scene', idu], queryFn: () => getGabaritScene(idu), retry: false })
  const scene = q.data
  const [webgl] = useState(webglOK)
  const [axe, setAxe] = useState<'A' | 'B'>('B')
  const [agrandi, setAgrandi] = useState(false)
  const [cote, setCote] = useState({ hi: 0, lo: 0, cur: null as number | null, cap: 0 })
  const markerApi = useRef<((f: number | null) => void) | null>(null)
  const dispo = scene?.disponible && !!scene.terrain?.faces_parcelle?.vertices?.length
  // L'aperçu REMPLIT son bandeau : on demande le SVG à (taille du bandeau ÷ 1,3) et on l'affiche en
  // remplissant (object-contain) → zoom ×1,3, donc les polices 9 px du SVG atteignent ≥ 11 px à l'écran,
  // à toutes les tailles de fenêtre, en gardant H = V.
  const coupeBand = useRef<HTMLDivElement>(null)
  const [coupeDim, setCoupeDim] = useState<{ w: number; h: number }>({ w: 0, h: 0 })
  useEffect(() => {
    const el = coupeBand.current; if (!el) return
    let raf = 0
    const mesure = () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(() => {
      const aw = el.clientWidth - 16, ah = el.clientHeight - 16   // p-2 (8 px de chaque côté)
      if (aw > 4 && ah > 4) setCoupeDim({ w: Math.round(aw / 1.3), h: Math.round(ah / 1.3) })
    }) }
    mesure(); const ro = new ResizeObserver(mesure); ro.observe(el)
    return () => { cancelAnimationFrame(raf); ro.disconnect() }
  }, [axe, dispo])
  const sid = scene?.scene_id   // transmis au plan/coupes (parité : même version que le terrain et le PDF)
  const coupes = useMemo(() => (scene?.coupes || []).map((c) => String((c as { label?: string }).label ?? '')), [scene])
  const acq = scene?.meta?.acquisition_date ? String(scene.meta.acquisition_date) : '—'
  const acqFr = acq.replace(/^(\d{4})-(\d{2})-(\d{2})$/, '$3/$2/$1')   // 2023-08-12 → 12/08/2023 (pt 6)
  // LOT 2 — le pied annonce CE QUI EST RÉELLEMENT SERVI : maille lue dans la donnée (0,5 m LiDAR HD, ou
  // 1 m en repli) + message clair si repli (relief fin indisponible).
  const mailleM = Number(scene?.meta?.maille_m ?? 1)
  const mailleFr = mailleM === 0.5 ? '0,5 m' : `${String(mailleM).replace('.', ',')} m`
  const solRepli = Boolean(scene?.meta?.sol_repli)
  const solMsg = scene?.meta?.sol_message ? String(scene.meta.sol_message) : ''
  const axeSel = coupes.includes(axe) ? axe : (coupes[0] as 'A' | 'B' | undefined) ?? null
  const coupeTitre = useMemo(() => { const c = (scene?.coupes || []).find((c) => String((c as { label?: string }).label ?? '') === axeSel); return c ? String((c as { titre?: string }).titre ?? '') : '' }, [scene, axeSel])

  // survol de la coupe CALÉ sur le rectangle du tracé (data-plot-x0/x1 portés par le SVG) — B8
  const onCoupeHover = (ev: React.MouseEvent<HTMLImageElement>) => {
    const img = ev.currentTarget, r = img.getBoundingClientRect()
    // object-contain : l'image est LETTERBOXÉE dans l'élément → on retrouve le rectangle RÉELLEMENT dessiné.
    // On prend les dimensions du viewBox (WebKit renvoie une naturalWidth déjà mise à l'échelle pour un SVG).
    const nw = Number(img.dataset.vbw) || 960, nh = Number(img.dataset.vbh) || 1
    const sc = Math.min(r.width / nw, r.height / nh), drawnW = nw * sc, offX = (r.width - drawnW) / 2
    const x0 = Number(img.dataset.plotX0 ?? 64), x1 = Number(img.dataset.plotX1 ?? nw - 20)
    const sx = ((ev.clientX - r.left - offX) / drawnW) * nw
    markerApi.current?.(Math.min(1, Math.max(0, (sx - x0) / (x1 - x0))))
  }
  // lit les bornes du tracé depuis le SVG chargé (pour caler le survol). On CAPTURE l'élément AVANT l'await :
  // `ev.currentTarget` est annulé par React après le premier await → sinon le dataset (viewBox/plot) n'est
  // JAMAIS posé et le survol retombe sur une largeur par défaut (960) fausse dès que la coupe est responsive.
  const onImgLoad = async (ev: React.SyntheticEvent<HTMLImageElement>) => {
    const img = ev.currentTarget
    try {
      const txt = await (await fetch(img.src)).text()
      const m0 = txt.match(/data-plot-x0="([\d.]+)"/), m1 = txt.match(/data-plot-x1="([\d.]+)"/)
      const vb = txt.match(/viewBox="0 0 ([\d.]+) ([\d.]+)"/)
      if (m0) img.dataset.plotX0 = m0[1]; if (m1) img.dataset.plotX1 = m1[1]
      if (vb) { img.dataset.vbw = vb[1]; img.dataset.vbh = vb[2] }
    } catch { /* noop */ }
  }

  return createPortal(
    <div data-gab3d-overlay className="fixed inset-0 z-[60] flex flex-col bg-[#0b0d10] text-txt">
      {/* en-tête (B6) : adresse · commune · référence cadastrale + sélecteur */}
      <div className="flex items-center justify-between border-b border-line px-4 py-2">
        <div>
          <div className="text-[9px] uppercase tracking-wide text-txt-ghost">LABUSE · Gabarit réglementaire — Vue 3D pilote (admin)</div>
          <div className="text-[15px] font-semibold text-txt">{scene?.adresse ?? idu}</div>
          <div className="text-[10px] text-txt-dim">{scene?.meta?.commune ? `${String(scene.meta.commune)} · ` : ''}{idu}</div>
        </div>
        <div className="flex items-center gap-1 text-[11px]">
          {coupes.map((l) => (
            <button key={l} onClick={() => setAxe(l as 'A' | 'B')}
              className={`rounded px-2.5 py-1 ${axe === l ? 'bg-mint/20 text-mint' : 'text-txt-mut hover:text-txt'}`}>Coupe {l}</button>
          ))}
          <button data-gab3d-close onClick={onClose} className="ml-2 rounded px-2 py-1 text-txt-mut hover:text-txt">✕ Fermer</button>
        </div>
      </div>
      {q.isLoading && <div className="p-6"><Squelette lignes={6} /></div>}
      {q.isError && <div className="p-6 text-[13px] text-coral">Scène indisponible.</div>}
      {scene && (
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="flex min-h-0 flex-[3]">
            {/* 3D en haut à gauche */}
            <div className="relative min-h-0 flex-[1.6] border-r border-line">
              {webgl && dispo
                ? <Vue3D scene={scene} axeSel={axeSel} markerApi={markerApi} onCote={setCote} />
                : <div data-gab3d-fallback className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center text-[12px] text-txt-mut">
                    <p>{webgl ? 'Terrain non couvert ici.' : 'WebGL indisponible — repli sur le plan et les coupes.'}</p>
                    <img src={gabPlanSvgUrl(idu, 'sombre', sid)} alt="Plan-clé" className="max-w-[380px]" />
                  </div>}
              {dispo && cote.cur != null && <div className="pointer-events-none absolute left-3 bottom-8 text-[10px] text-txt-dim">{cote.cur.toFixed(1).replace('.', ',')} m</div>}
            </div>
            {/* à droite : plan-clé COMPACT (un seul titre) + légende. LOT 4 — le plan-clé RÉTRÉCIT (flex-1,
                object-contain) pour laisser la légende ENTIÈREMENT visible à toute hauteur ; la légende et
                les titres ne rétrécissent pas (shrink-0) → jamais coupés par le panneau de la coupe. */}
            <div className="flex w-[320px] min-h-0 shrink-0 flex-col gap-2 bg-[#0f1216] p-3">
              <div className="shrink-0 text-[11px] text-txt-mut">Plan-clé <span className="text-txt-ghost">— nord en haut</span></div>
              <div className="flex min-h-0 flex-1 items-start justify-center">
                <img data-gab3d-plan src={gabPlanSvgUrl(idu, 'sombre', sid, 210, 176)} alt="Plan-clé" className="h-full w-full rounded border border-line object-contain object-top" />
              </div>
              <div data-gab3d-legende className="mt-1 flex shrink-0 flex-col gap-1 text-[11px] text-txt-mut">
                {LEG.map(([c, lab]) => (
                  <div key={lab} className="flex items-center gap-2"><span className="inline-block h-2 w-4 rounded-sm" style={{ background: c }} />{lab}</div>
                ))}
              </div>
              <p className="mt-1 shrink-0 text-[9px] leading-snug text-txt-ghost">Détails techniques — scène {scene.scene_id}</p>
            </div>
          </div>
          {/* en bas : en-tête (titre + datum + Agrandir, pt 1) puis l'aperçu qui REMPLIT son cadre (H = V, ≥ 11 px) */}
          <div data-gab3d-coupe-panneau className="flex min-h-[300px] flex-1 flex-col overflow-hidden border-t border-line bg-[#0f1216]">
            <div className="flex items-center justify-between gap-2 border-b border-line/60 px-3 py-1">
              <div data-gab3d-coupe-titre className="truncate text-[12px] font-semibold text-txt">{coupeTitre}</div>
              <div className="flex shrink-0 items-center gap-3">
                <span data-gab3d-coupe-datum className="hidden text-[11px] text-txt-dim lg:inline">Altitudes en m · IGN 1989 · H = V</span>
                {axeSel && <button data-gab3d-agrandir onClick={() => setAgrandi(true)}
                  className="rounded border border-line bg-black/50 px-2 py-1 text-[11px] text-txt-mut hover:text-txt">⤢ Agrandir la coupe</button>}
              </div>
            </div>
            <div ref={coupeBand} data-gab3d-coupe-band className="relative flex flex-1 items-center justify-center overflow-hidden p-2">
              {axeSel
                ? <img key={axeSel} src={gabCoupeSvgUrl(idu, axeSel, 'sombre', sid, false, coupeDim.w || undefined, coupeDim.h || undefined, false)} alt={`Coupe ${axeSel}`}
                       onLoad={onImgLoad} onMouseMove={onCoupeHover} onMouseLeave={() => markerApi.current?.(null)}
                       className="h-full w-full cursor-crosshair rounded border border-line object-contain" />
                : <p className="text-[12px] text-txt-mut">Aucune coupe disponible.</p>}
            </div>
          </div>
          <p data-gab3d-pied className="border-t border-line px-3 py-1.5 text-[10px] text-txt-dim">
            MNT LiDAR HD IGN · maille de {mailleFr} · acquisition {acqFr}{solRepli ? <span className="text-amber"> · {solMsg}</span> : ''} · cotes indicatives · courbes tous les mètres, trait fort tous les 5 m · H = V.
          </p>
        </div>
      )}
      {/* agrandissement : fond OPAQUE, pleine largeur, H = V conservé (profil+bandes+résumé en entier) */}
      {agrandi && scene && axeSel && (
        <div className="absolute inset-0 z-[70] flex flex-col items-center justify-center gap-2 bg-[#0b0d10] p-4" onClick={() => setAgrandi(false)}>
          <button onClick={() => setAgrandi(false)} className="self-end rounded px-2 py-1 text-[12px] text-txt-mut hover:text-txt">✕ Revenir au terrain</button>
          <img src={gabCoupeSvgUrl(idu, axeSel, 'sombre', sid, true)} alt="Agrandie"
               onMouseMove={onCoupeHover} onMouseLeave={() => markerApi.current?.(null)}
               className="max-h-full w-full rounded border border-line object-contain" onClick={(e) => e.stopPropagation()} />
        </div>
      )}
    </div>,
    document.body)
}
