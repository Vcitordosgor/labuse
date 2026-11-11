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
import { getGabaritScene, gabCoupeSvgUrl, gabPlanSvgUrl, type GabScene, type GabMesh, type GabPoly } from '../../lib/api'
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

// échantillonneur TRIANGULÉ sur les sommets servis (même découpe que le serveur) + les triangles réels.
function makeElev(f: GabMesh): (x: number, y: number) => number | null {
  let x0 = Infinity, y0 = Infinity
  for (const v of f.vertices) { x0 = Math.min(x0, v[0]); y0 = Math.min(y0, v[1]) }
  const pas = f.pas_m, idx = (i: number, j: number) => i * 100000 + j
  const g = new Map<number, number>()
  for (const [x, y, z] of f.vertices) g.set(idx(Math.round((x - x0) / pas), Math.round((y - y0) / pas)), z)
  const at = (i: number, j: number) => { const v = g.get(idx(i, j)); return v == null ? null : v }
  return (x, y) => {
    const cj = (x - x0) / pas, ci = (y - y0) / pas, J = Math.floor(cj), I = Math.floor(ci), tc = cj - J, tr = ci - I
    const z00 = at(I, J), z10 = at(I, J + 1), z01 = at(I + 1, J), z11 = at(I + 1, J + 1)
    // deux triangles par maille, diagonale P00–P11 (même que le serveur)
    if (tc >= tr) return (z00 == null || z10 == null || z11 == null) ? null : z00 * (1 - tc) + z10 * (tc - tr) + z11 * tr
    return (z00 == null || z11 == null || z01 == null) ? null : z00 * (1 - tr) + z11 * tc + z01 * (tr - tc)
  }
}

const RAMP_LOW = new THREE.Color('#34403a'), RAMP_HIGH = new THREE.Color('#86a093'), ZONE_TINT = new THREE.Color('#2f9e6a')

function terrainMesh(f: GabMesh, parcelle: GabPoly[], zone: GabPoly[]) {
  const g = new THREE.BufferGeometry()
  const pos = new Float32Array(f.vertices.length * 3), col = new Float32Array(f.vertices.length * 3)
  let zmin = Infinity, zmax = -Infinity
  for (const p of f.vertices) { zmin = Math.min(zmin, p[2]); zmax = Math.max(zmax, p[2]) }
  const span = Math.max(zmax - zmin, 1e-6)
  f.vertices.forEach((p, i) => {
    pos[i * 3] = p[0]; pos[i * 3 + 1] = p[2]; pos[i * 3 + 2] = -p[1]
    const c = RAMP_LOW.clone().lerp(RAMP_HIGH, (p[2] - zmin) / span)
    if (inPolys(p[0], p[1], zone)) c.lerp(ZONE_TINT, 0.5)           // zone au sol (masque) — sur sommets servis
    if (!inPolys(p[0], p[1], parcelle)) c.multiplyScalar(0.6)       // assombri hors parcelle
    col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b
  })
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3))
  g.setAttribute('color', new THREE.BufferAttribute(col, 3))
  g.setIndex(f.triangles.flat()); g.computeVertexNormals()         // ombrage lissé
  const mesh = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, side: THREE.DoubleSide }))
  g.computeBoundingBox()
  return { mesh, zmin, zmax, box: g.boundingBox!.clone() }
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

function drapeLine(ring: number[][], elev: (x: number, y: number) => number | null, color: number, px: number, res: THREE.Vector2, dashed = false) {
  const group = new THREE.Group()
  const mat = new LineMaterial({ color, linewidth: px, transparent: true, dashed, dashSize: 2, gapSize: 1.6 })
  mat.resolution.copy(res)
  let run: number[] = []
  const flush = () => { if (run.length >= 6) { const g = new LineGeometry(); g.setPositions(run); const l = new Line2(g, mat); l.computeLineDistances(); l.renderOrder = 3; group.add(l) } run = [] }
  const dense: number[][] = []
  for (let i = 0; i < ring.length - 1; i++) {
    const a = ring[i], b = ring[i + 1], d = Math.hypot(b[0] - a[0], b[1] - a[1]), n = Math.max(1, Math.ceil(d))
    for (let k = 0; k < n; k++) dense.push([a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n])
  }
  dense.push(ring[ring.length - 1])
  for (const [x, y] of dense) { const z = elev(x, y); if (z != null) run.push(x, z + 0.4, -y); else flush() }   // jamais 0
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
      grp.add(new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: 0xcdd3d8, roughness: 0.9 })))
      grp.add(new THREE.LineSegments(new THREE.EdgesGeometry(geo), new THREE.LineBasicMaterial({ color: 0x8a9096 })))   // arêtes fines
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
  const axeSelRef = useRef(axeSel); axeSelRef.current = axeSel
  const axisObjs = useRef<Record<string, THREE.Object3D[]>>({})
  const [perdu, setPerdu] = useState(false)

  // changer de coupe ne recrée PAS le contexte : on recolore seulement l'axe (B9)
  useEffect(() => {
    for (const [lab, objs] of Object.entries(axisObjs.current)) {
      const sel = lab === axeSel
      for (const o of objs) {
        const l = o as Line2
        const m = l.material as LineMaterial
        if (m) { m.color.set(sel ? 0xe0a44a : 0x6b7682); m.linewidth = sel ? 2.6 : 1.4; m.needsUpdate = true }
        l.renderOrder = sel ? 5 : 3
      }
    }
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

    const { mesh, box } = terrainMesh(faces, scene.contour_cadastral, scene.zone_implantation)
    sc.add(mesh)
    const elev = makeElev(faces)
    const cn = contours(faces); const cnGroup = new THREE.Group(); cnGroup.add(cn.master); cnGroup.add(cn.minor); sc.add(cnGroup)
    toggleCn.current = () => { cnGroup.visible = !cnGroup.visible }
    for (const poly of scene.contour_cadastral) sc.add(drapeLine(poly.ext, elev, 0xffffff, 3.0, res))
    for (const poly of scene.zone_implantation) sc.add(drapeLine(poly.ext, elev, 0x36c99a, 1.6, res))
    axisObjs.current = {}
    for (const [lab, a] of Object.entries(scene.axes_plan || {})) {
      const grp = drapeLine([a.p0, a.p1], elev, lab === axeSel ? 0xe0a44a : 0x6b7682, lab === axeSel ? 2.6 : 1.4, res, true)
      sc.add(grp); axisObjs.current[lab] = grp.children as THREE.Object3D[]
    }
    for (const b of scene.batiments) sc.add(batiVolume(b, elev, res))

    sc.add(new THREE.AmbientLight(0xffffff, 0.55))
    const sun = new THREE.DirectionalLight(0xffffff, 0.85); sun.position.set(-1, 1.4, 1); sc.add(sun)   // nord-ouest

    const ctr = box.getCenter(new THREE.Vector3()), size = box.getSize(new THREE.Vector3())
    const r = Math.max(size.x, size.z) * 0.6 + 4
    const cam = new THREE.OrthographicCamera(-r, r, r, -r, 0.1, r * 40)
    const place = () => {
      const w = el.clientWidth || W, h = el.clientHeight || H
      cam.position.set(ctr.x + r * 1.1, ctr.y + r * 1.25, ctr.z + r * 1.1); cam.lookAt(ctr)
      cam.left = -r * (w / h); cam.right = r * (w / h); cam.top = r; cam.bottom = -r; cam.updateProjectionMatrix()
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
      if (z != null) { marker.position.set(x, z + 0.6, -y); marker.visible = true } else marker.visible = false
    }

    // étiquettes HTML posées (hi/bas + boussole) mises à jour dans la boucle
    const lay = document.createElement('div'); lay.style.cssText = 'position:absolute;inset:0;pointer-events:none;font:600 10px Inter,sans-serif'
    el.appendChild(lay)
    const mkLab = (txt: string, col: string) => { const d = document.createElement('div'); d.textContent = txt; d.style.cssText = `position:absolute;color:${col};transform:translate(-50%,-50%);text-shadow:0 1px 2px #000` ; lay.appendChild(d); return d }
    const lHi = mkLab(`${String(Math.round(hi * 10) / 10).replace('.', ',')} m`, '#e8edf2')
    const lLo = mkLab(`${String(Math.round(lo * 10) / 10).replace('.', ',')} m`, '#e8edf2')
    const compass = document.createElement('div')
    compass.innerHTML = '<svg width="34" height="34" viewBox="0 0 34 34"><circle cx="17" cy="17" r="15" fill="rgba(0,0,0,.4)" stroke="#5b6670"/><g id="nd"><path d="M17 4 L20 17 L17 15 L14 17 Z" fill="#e0a44a"/><text x="17" y="30" text-anchor="middle" font-size="8" fill="#cbd5e1">N</text></g></svg>'
    compass.style.cssText = 'position:absolute;right:8px;top:8px'; lay.appendChild(compass)
    const nd = compass.querySelector('#nd') as SVGGElement
    const proj = (p: THREE.Vector3, d: HTMLDivElement) => { const v = p.clone().project(cam); const vis = v.z < 1; d.style.display = vis ? 'block' : 'none'; d.style.left = `${(v.x * 0.5 + 0.5) * el.clientWidth}px`; d.style.top = `${(-v.y * 0.5 + 0.5) * el.clientHeight}px` }

    let raf = 0, stop = false, first = 0, info = { geometries: 0, textures: 0 }
    const loop = () => {
      if (stop) return
      controls.update(); renderer.render(sc, cam)
      if (!first) first = performance.now()
      proj(hiP, lHi); proj(loP, lLo)
      const az = controls.getAzimuthalAngle(); nd.setAttribute('transform', `rotate(${(-az * 180 / Math.PI).toFixed(1)} 17 17)`)
      info = { geometries: renderer.info.memory.geometries, textures: renderer.info.memory.textures }
      ;(window as unknown as Record<string, unknown>).__gab3d = { first, info, fps: renderer.info.render.frame }
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
      markerApi.current = null; controls.dispose(); el.removeChild(lay)
      sc.traverse((o) => { const m = o as THREE.Mesh; if (m.geometry) m.geometry.dispose(); const mt = m.material as THREE.Material | THREE.Material[] | undefined; if (Array.isArray(mt)) mt.forEach((x) => x.dispose()); else mt?.dispose() })
      renderer.dispose(); renderer.forceContextLoss(); if (renderer.domElement.parentElement === el) el.removeChild(renderer.domElement)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scene])

  return (
    <div className="relative h-full w-full">
      <div ref={host} className="h-full w-full" data-gab3d-canvas />
      {perdu && <div data-gab3d-fallback className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/85 p-6 text-center text-[12px] text-txt-mut">
        <p>Contexte WebGL perdu — repli sur le plan et les coupes.</p>
        <img src={gabPlanSvgUrl(scene.idu, 'sombre')} alt="Plan-clé" className="max-w-[360px]" />
      </div>}
      <div className="absolute left-3 top-3 flex gap-2">
        <button data-gab3d-recentrer onClick={() => recentrer.current()} className="rounded border border-line bg-black/50 px-2 py-1 text-[11px] text-txt-mut hover:text-txt">◎ Recentrer</button>
        <button data-gab3d-courbes onClick={() => toggleCn.current()} className="rounded border border-line bg-black/50 px-2 py-1 text-[11px] text-txt-mut hover:text-txt">Courbes de niveau</button>
      </div>
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
  const coupes = useMemo(() => (scene?.coupes || []).map((c) => String((c as { label?: string }).label ?? '')), [scene])
  const acq = scene?.meta?.acquisition_date ? String(scene.meta.acquisition_date) : '—'
  const axeSel = coupes.includes(axe) ? axe : (coupes[0] as 'A' | 'B' | undefined) ?? null

  // survol de la coupe CALÉ sur le rectangle du tracé (data-plot-x0/x1 portés par le SVG) — B8
  const onCoupeHover = (ev: React.MouseEvent<HTMLImageElement>) => {
    const img = ev.currentTarget, r = img.getBoundingClientRect()
    const vb = img.naturalWidth || 960
    const x0 = Number(img.dataset.plotX0 ?? 64), x1 = Number(img.dataset.plotX1 ?? vb - 20)
    const sx = ((ev.clientX - r.left) / r.width) * vb
    markerApi.current?.(Math.min(1, Math.max(0, (sx - x0) / (x1 - x0))))
  }
  // lit les bornes du tracé depuis le SVG chargé (pour caler le survol)
  const onImgLoad = async (ev: React.SyntheticEvent<HTMLImageElement>) => {
    try {
      const txt = await (await fetch(ev.currentTarget.src)).text()
      const m0 = txt.match(/data-plot-x0="([\d.]+)"/), m1 = txt.match(/data-plot-x1="([\d.]+)"/)
      if (m0) ev.currentTarget.dataset.plotX0 = m0[1]; if (m1) ev.currentTarget.dataset.plotX1 = m1[1]
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
                    <img src={gabPlanSvgUrl(idu, 'sombre')} alt="Plan-clé" className="max-w-[380px]" />
                  </div>}
              {dispo && <div className="pointer-events-none absolute left-3 bottom-8 text-[10px] text-txt-dim">
                haut {String(cote.hi).replace('.', ',')} m · bas {String(cote.lo).replace('.', ',')} m{cote.cur != null ? ` · curseur ${String(cote.cur).replace('.', ',')} m` : ''}</div>}
            </div>
            {/* à droite : plan-clé (nord en haut, échelle) + légende */}
            <div className="flex w-[360px] shrink-0 flex-col gap-2 overflow-y-auto bg-[#0f1216] p-3">
              <div className="text-[11px] text-txt-mut">Plan-clé <span className="text-txt-ghost">— nord en haut</span></div>
              <img src={gabPlanSvgUrl(idu, 'sombre')} alt="Plan-clé" className="w-full rounded border border-line" />
              <div className="mt-1 flex flex-col gap-1 text-[10px] text-txt-mut">
                {LEG.map(([c, lab]) => (
                  <div key={lab} className="flex items-center gap-2"><span className="inline-block h-2 w-4 rounded-sm" style={{ background: c }} />{lab}</div>
                ))}
              </div>
              <p className="mt-1 text-[9px] leading-snug text-txt-ghost">Détails techniques — scène {scene.scene_id}</p>
            </div>
          </div>
          {/* en bas : la coupe active, pleine largeur */}
          <div className="min-h-0 flex-1 overflow-auto border-t border-line bg-[#0f1216] p-3">
            {axeSel
              ? <img key={axeSel} src={gabCoupeSvgUrl(idu, axeSel, 'sombre')} alt={`Coupe ${axeSel}`}
                     onLoad={onImgLoad} onMouseMove={onCoupeHover} onMouseLeave={() => markerApi.current?.(null)}
                     onClick={() => setAgrandi(true)} className="w-full cursor-crosshair rounded border border-line" />
              : <p className="text-[12px] text-txt-mut">Aucune coupe disponible.</p>}
          </div>
          <p className="border-t border-line px-3 py-1.5 text-[10px] text-txt-dim">
            MNT LiDAR HD IGN · maille de 1 m · acquisition {acq} · cotes indicatives · courbes tous les mètres, trait fort tous les 5 m · H = V.
          </p>
        </div>
      )}
      {/* agrandissement : fond OPAQUE, toute la largeur, H = V conservé (C12) */}
      {agrandi && scene && axeSel && (
        <div className="absolute inset-0 z-[70] flex items-center justify-center bg-[#0b0d10] p-4" onClick={() => setAgrandi(false)}>
          <img src={gabCoupeSvgUrl(idu, axeSel, 'sombre')} alt="Agrandie" className="w-full rounded border border-line" onClick={(e) => e.stopPropagation()} />
        </div>
      )}
    </div>,
    document.body)
}
