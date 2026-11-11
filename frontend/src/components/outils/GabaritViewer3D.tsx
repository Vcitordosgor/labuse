// GABARIT-3D-1 (pilote, étape 2 bis) — VISIONNEUSE Three.js, à la demande, réservée aux admins.
//
// « D'abord juste, ensuite beau. » Sur la scène corrigée (un seul maillage 1 m servi) : caméra
// orthographique de trois quarts, ombrage lissé (lumière du nord-ouest), courbes de niveau par
// intersection des triangles (maîtresses 5 m / intermédiaires 1 m au zoom), zone d'implantation en
// MASQUE sur le terrain (trous respectés), terrain assombri hors parcelle, contours et axes POSÉS sur
// le relief (parcelle blanc épais, orange réservé à la coupe sélectionnée, jamais d'altitude zéro),
// repères d'altitude (haut/bas + sous le curseur), onglets Plan · Coupe A · Coupe B. Échelle verticale
// ×1, aucune photo aérienne. Safari : ressources libérées, repli plan+coupes si le contexte WebGL tombe.
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
// repère : local (x=est, y=nord, z=alt) → Three (x, alt, -nord). MÊME transformation partout (terrain,
// contours, bâti) pour que l'emprise et le volume coïncident (A4 : l'extrusion n'inverse plus le nord-sud).

// point dans un (multi)polygone à trous
function inRing(x: number, y: number, ring: number[][]): boolean {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j]
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside
  }
  return inside
}
function inPolys(x: number, y: number, polys: GabPoly[]): boolean {
  for (const p of polys) {
    if (inRing(x, y, p.ext) && !(p.trous || []).some((t) => inRing(x, y, t))) return true
  }
  return false
}

const RAMP_LOW = new THREE.Color('#34403a')
const RAMP_HIGH = new THREE.Color('#86a093')
const ZONE_TINT = new THREE.Color('#2f9e6a')

function terrainMesh(f: GabMesh, parcelle: GabPoly[], zone: GabPoly[]) {
  const g = new THREE.BufferGeometry()
  const pos = new Float32Array(f.vertices.length * 3)
  const col = new Float32Array(f.vertices.length * 3)
  let zmin = Infinity, zmax = -Infinity
  f.vertices.forEach((p) => { zmin = Math.min(zmin, p[2]); zmax = Math.max(zmax, p[2]) })
  const span = Math.max(zmax - zmin, 1e-6)
  f.vertices.forEach((p, i) => {
    pos[i * 3] = p[0]; pos[i * 3 + 1] = p[2]; pos[i * 3 + 2] = -p[1]
    const c = RAMP_LOW.clone().lerp(RAMP_HIGH, (p[2] - zmin) / span)
    if (inPolys(p[0], p[1], zone)) c.lerp(ZONE_TINT, 0.5)            // zone au sol (masque, trous respectés)
    if (!inPolys(p[0], p[1], parcelle)) c.multiplyScalar(0.6)       // terrain assombri hors parcelle
    col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b
  })
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3))
  g.setAttribute('color', new THREE.BufferAttribute(col, 3))
  g.setIndex(f.triangles.flat())
  g.computeVertexNormals()                                          // ombrage LISSÉ (pas de facettes)
  const mat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, metalness: 0.0, side: THREE.DoubleSide })
  const mesh = new THREE.Mesh(g, mat)
  mesh.renderOrder = 0
  g.computeBoundingBox()
  return { mesh, zmin, zmax, box: g.boundingBox!.clone() }
}

// courbes de niveau par intersection des triangles : arêtes partagées dédupliquées, égalités traitées,
// interruption aux lacunes (les triangles à lacune sont déjà absents des faces servies).
function contours(f: GabMesh, zmin: number, zmax: number) {
  const V = f.vertices
  const master: number[] = [], minor: number[] = []
  const seen = new Set<string>()
  const key = (a: number, b: number) => (a < b ? `${a}|${b}` : `${b}|${a}`)
  const emit = (arr: number[], p: number[], q: number[]) => { arr.push(p[0], p[1], -p[2], q[0], q[1], -q[2]) }
  const interp = (a: number[], b: number[], lv: number): number[] => {
    const t = (lv - a[2]) / (b[2] - a[2]); return [a[0] + t * (b[0] - a[0]), lv, a[1] + t * (b[1] - a[1])]
  }
  for (const tri of f.triangles) {
    const P = [V[tri[0]], V[tri[1]], V[tri[2]]]
    const lo = Math.min(P[0][2], P[1][2], P[2][2]), hi = Math.max(P[0][2], P[1][2], P[2][2])
    for (let lv = Math.ceil(lo); lv <= hi; lv += 1) {
      const pts: number[][] = []
      for (let e = 0; e < 3; e++) {
        const a = P[e], b = P[(e + 1) % 3]
        if ((a[2] - lv) * (b[2] - lv) < 0) pts.push(interp(a, b, lv))
        else if (a[2] === lv) pts.push([a[0], lv, a[1]])             // égalité : sommet sur le niveau
      }
      if (pts.length >= 2) {
        const k = `${lv}:${key(tri[0] + tri[1], tri[1] + tri[2])}:${Math.round(pts[0][0])}:${Math.round(pts[0][2])}`
        if (seen.has(k)) continue
        seen.add(k)
        emit(lv % 5 === 0 ? master : minor, [pts[0][0], pts[0][2], pts[0][1]], [pts[1][0], pts[1][2], pts[1][1]])
      }
    }
  }
  const mk = (arr: number[], color: number, op: number) => {
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(arr), 3))
    return new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color, transparent: true, opacity: op }))
  }
  return { master: mk(master, 0xb9c6bd, 0.55), minor: mk(minor, 0x7c8a81, 0.28), zmin, zmax }
}

// recherche d'altitude O(1) sur la grille des sommets servis (bilinéaire), None hors couverture.
// Remplace le raycast O(n) → le drapage reste rapide (chargement à chaud < 2 s).
function makeElev(f: GabMesh): (x: number, y: number) => number | null {
  let x0 = Infinity, y0 = Infinity
  for (const v of f.vertices) { x0 = Math.min(x0, v[0]); y0 = Math.min(y0, v[1]) }
  const pas = f.pas_m, idx = (i: number, j: number) => i * 100000 + j
  const g = new Map<number, number>()
  for (const [x, y, z] of f.vertices) g.set(idx(Math.round((x - x0) / pas), Math.round((y - y0) / pas)), z)
  return (x, y) => {
    const fx = (x - x0) / pas, fy = (y - y0) / pas, i = Math.floor(fx), j = Math.floor(fy), tx = fx - i, ty = fy - j
    const z00 = g.get(idx(i, j)), z10 = g.get(idx(i + 1, j)), z01 = g.get(idx(i, j + 1)), z11 = g.get(idx(i + 1, j + 1))
    if (z00 == null || z10 == null || z01 == null || z11 == null) return null
    return (z00 * (1 - tx) + z10 * tx) * (1 - ty) + (z01 * (1 - tx) + z11 * tx) * ty
  }
}

// contour/axe POSÉ sur le relief : densifié, altitude relevée sur la grille, INTERROMPU (jamais
// d'altitude zéro) dans une lacune, légèrement soulevé (pas de scintillement).
function drapeLine(ring: number[][], elev: (x: number, y: number) => number | null, color: number, px: number, res: THREE.Vector2, dashed = false) {
  const group = new THREE.Group()
  const mat = new LineMaterial({ color, linewidth: px, transparent: true, dashed, dashSize: 2, gapSize: 1.6 })
  mat.resolution.copy(res)
  let run: number[] = []
  const flush = () => {
    if (run.length >= 6) { const g = new LineGeometry(); g.setPositions(run); const l = new Line2(g, mat); l.computeLineDistances(); l.renderOrder = 3; group.add(l) }
    run = []
  }
  const dense: number[][] = []
  for (let i = 0; i < ring.length - 1; i++) {
    const a = ring[i], b = ring[i + 1]; const d = Math.hypot(b[0] - a[0], b[1] - a[1]); const n = Math.max(1, Math.ceil(d / 1.0))
    for (let k = 0; k < n; k++) dense.push([a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n])
  }
  dense.push(ring[ring.length - 1])
  for (const [x, y] of dense) {
    const z = elev(x, y)
    if (z != null) run.push(x, z + 0.4, -y)                         // soulevé ; jamais 0
    else flush()                                                    // lacune → interruption
  }
  flush()
  return group
}

function batiVolume(b: { empreinte: GabPoly[]; pied_m: number | null; hauteur_m: number | null; volume?: boolean }) {
  const grp = new THREE.Group()
  const vol = b.volume && b.hauteur_m && b.pied_m != null
  for (const poly of b.empreinte) {
    // MÊME transformation que le terrain/contours : forme (x, y) puis rotateX(-90°) → (x, z, -y), donc
    // le volume coïncide avec l'emprise (A4 : plus d'inversion nord-sud).
    const shape = new THREE.Shape(poly.ext.map(([x, y]) => new THREE.Vector2(x, y)))
    for (const t of poly.trous || []) shape.holes.push(new THREE.Path(t.map(([x, y]) => new THREE.Vector2(x, y))))
    if (vol) {
      const geo = new THREE.ExtrudeGeometry(shape, { depth: b.hauteur_m!, bevelEnabled: false })
      geo.rotateX(-Math.PI / 2); geo.translate(0, b.pied_m!, 0)
      grp.add(new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: 0xcdd3d8, roughness: 0.9, flatShading: false })))
    } else {                                                        // emprise seule (pied ou hauteur manquant)
      const pts = poly.ext.map(([x, y]) => new THREE.Vector3(x, (b.pied_m ?? 0) + 0.3, -y))
      grp.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: 0xaab0b6 })))
    }
  }
  return grp
}

function Vue3D({ scene, axeSel, markerApi }: {
  scene: GabScene; axeSel: 'A' | 'B' | null
  markerApi: React.MutableRefObject<((f: number | null) => void) | null>
}) {
  const host = useRef<HTMLDivElement>(null)
  const [cote, setCote] = useState<{ hi: number; lo: number; cur: number | null }>({ hi: 0, lo: 0, cur: null })
  const recentrer = useRef<() => void>(() => {})
  const [perdu, setPerdu] = useState(false)

  useEffect(() => {
    const el = host.current; const faces = scene.terrain?.faces_parcelle
    if (!el || !faces || !faces.vertices.length) return
    const W = el.clientWidth || el.parentElement?.clientWidth || window.innerWidth
    const H = el.clientHeight || el.parentElement?.clientHeight || window.innerHeight
    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'low-power' })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); renderer.setSize(W, H)
    el.appendChild(renderer.domElement)
    const res = new THREE.Vector2(W * renderer.getPixelRatio(), H * renderer.getPixelRatio())
    const sc = new THREE.Scene(); sc.background = new THREE.Color('#0d0f12')

    const { mesh, zmin, zmax, box } = terrainMesh(faces, scene.contour_cadastral, scene.zone_implantation)
    sc.add(mesh)
    const elev = makeElev(faces)
    const ct = contours(faces, zmin, zmax); sc.add(ct.master); sc.add(ct.minor)
    // contours posés : parcelle BLANC ÉPAIS ; axe sélectionné ORANGE ; zone verte ; bâti
    for (const poly of scene.contour_cadastral) sc.add(drapeLine(poly.ext, elev, 0xffffff, 3.0, res))
    for (const poly of scene.zone_implantation) sc.add(drapeLine(poly.ext, elev, 0x36c99a, 1.6, res))
    for (const [lab, a] of Object.entries(scene.axes_plan || {})) {
      const sel = axeSel === lab
      sc.add(drapeLine([a.p0, a.p1], elev, sel ? 0xe0a44a : 0x6b7682, sel ? 2.6 : 1.4, res, true))
    }
    for (const b of scene.batiments) sc.add(batiVolume(b))

    sc.add(new THREE.AmbientLight(0xffffff, 0.55))                  // ambiance modérée
    const sun = new THREE.DirectionalLight(0xffffff, 0.85); sun.position.set(-1, 1.4, 1); sc.add(sun)   // nord-ouest

    const ctr = box.getCenter(new THREE.Vector3()), size = box.getSize(new THREE.Vector3())
    const r = Math.max(size.x, size.z) * 0.62 + 4
    const aspect = W / H
    const cam = new THREE.OrthographicCamera(-r * aspect, r * aspect, r, -r, 0.1, r * 30)
    const place = () => {   // trois quarts
      cam.position.set(ctr.x + r * 1.1, ctr.y + r * 1.25, ctr.z + r * 1.1); cam.lookAt(ctr)
      cam.left = -r * (el.clientWidth / el.clientHeight || aspect); cam.right = -cam.left; cam.top = r; cam.bottom = -r
      cam.updateProjectionMatrix()
    }
    place()
    const controls = new OrbitControls(cam, renderer.domElement); controls.target.copy(ctr); controls.update()
    recentrer.current = () => { place(); controls.target.copy(ctr); controls.update() }

    // repères d'altitude parcelle (haut/bas) à l'ouverture
    let hi = -Infinity, lo = Infinity
    for (const p of faces.vertices) if (inPolys(p[0], p[1], scene.contour_cadastral)) { hi = Math.max(hi, p[2]); lo = Math.min(lo, p[2]) }
    setCote({ hi: Math.round(hi * 10) / 10, lo: Math.round(lo * 10) / 10, cur: null })

    // altitude sous le curseur + marqueur depuis le survol d'une coupe
    const ray = new THREE.Raycaster(); const ndc = new THREE.Vector2()
    const marker = new THREE.Mesh(new THREE.SphereGeometry(1.1, 16, 12), new THREE.MeshBasicMaterial({ color: 0xffd36a }))
    marker.visible = false; marker.renderOrder = 4; sc.add(marker)
    const onMove = (ev: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect()
      ndc.set(((ev.clientX - rect.left) / rect.width) * 2 - 1, -((ev.clientY - rect.top) / rect.height) * 2 + 1)
      ray.setFromCamera(ndc, cam); const h = ray.intersectObject(mesh)
      setCote((c) => ({ ...c, cur: h[0] ? Math.round(h[0].point.y * 10) / 10 : null }))
    }
    renderer.domElement.addEventListener('mousemove', onMove)
    markerApi.current = (frac) => {
      const a = axeSel ? scene.axes_plan?.[axeSel] : null
      if (frac == null || !a) { marker.visible = false; return }
      const x = a.p0[0] + (a.p1[0] - a.p0[0]) * frac, y = a.p0[1] + (a.p1[1] - a.p0[1]) * frac
      const z = elev(x, y)
      if (z != null) { marker.position.set(x, z + 0.6, -y); marker.visible = true } else marker.visible = false
    }

    let raf = 0, stop = false
    const loop = () => { if (stop) return; controls.update(); renderer.render(sc, cam); raf = requestAnimationFrame(loop) }
    loop()
    const onResize = () => { const w = el.clientWidth, h = el.clientHeight; if (w < 2 || h < 2) return; renderer.setSize(w, h); res.set(w * renderer.getPixelRatio(), h * renderer.getPixelRatio()); place() }
    window.addEventListener('resize', onResize); const ro = new ResizeObserver(onResize); ro.observe(el)
    // C13 — perte de contexte WebGL EN COURS D'USAGE → repli plan + coupes
    const onLost = (e: Event) => { e.preventDefault(); stop = true; cancelAnimationFrame(raf); setPerdu(true) }
    renderer.domElement.addEventListener('webglcontextlost', onLost)

    return () => {
      stop = true; cancelAnimationFrame(raf); window.removeEventListener('resize', onResize); ro.disconnect()
      renderer.domElement.removeEventListener('mousemove', onMove); renderer.domElement.removeEventListener('webglcontextlost', onLost)
      markerApi.current = null; controls.dispose()
      sc.traverse((o) => { const m = o as THREE.Mesh; if (m.geometry) m.geometry.dispose(); const mt = m.material as THREE.Material | THREE.Material[] | undefined; if (Array.isArray(mt)) mt.forEach((x) => x.dispose()); else mt?.dispose() })
      renderer.dispose(); renderer.forceContextLoss(); if (renderer.domElement.parentElement === el) el.removeChild(renderer.domElement)
    }
  }, [scene, axeSel, markerApi])

  return (
    <div className="relative h-full w-full">
      <div ref={host} className="h-full w-full" data-gab3d-canvas />
      {perdu && <div data-gab3d-fallback className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/80 p-6 text-center text-[12px] text-txt-mut">
        <p>Contexte WebGL perdu — repli sur le plan et les coupes.</p>
        <img src={gabPlanSvgUrl(scene.idu, 'sombre')} alt="Plan-clé" className="max-w-[360px]" />
      </div>}
      <button data-gab3d-recentrer onClick={() => recentrer.current()}
        className="absolute left-3 top-3 rounded border border-line bg-black/50 px-2 py-1 text-[11px] text-txt-mut hover:text-txt">◎ Recentrer</button>
      <div className="absolute right-3 top-3 text-right text-[10px] text-txt-dim">
        <div>N ↑ · altitudes (m, IGN 1989)</div>
        <div>haut {cote.hi} · bas {cote.lo}{cote.cur != null ? ` · curseur ${cote.cur}` : ''}</div>
      </div>
    </div>
  )
}

export function GabaritViewer3D({ idu, onClose }: { idu: string; onClose: () => void }) {
  const q = useQuery({ queryKey: ['gabarit-scene', idu], queryFn: () => getGabaritScene(idu), retry: false })
  const scene = q.data
  const [webgl] = useState(webglOK)
  const [tab, setTab] = useState<'plan' | 'A' | 'B'>('plan')
  const [agrandi, setAgrandi] = useState(false)
  const markerApi = useRef<((f: number | null) => void) | null>(null)
  const dispo = scene?.disponible && !!scene.terrain?.faces_parcelle?.vertices?.length
  const coupes = useMemo(() => (scene?.coupes || []).map((c) => String((c as { label?: string }).label ?? '')), [scene])
  const axeSel: 'A' | 'B' | null = tab === 'A' || tab === 'B' ? tab : null

  const onCoupeHover = (ev: React.MouseEvent<HTMLImageElement>) => {
    const r = ev.currentTarget.getBoundingClientRect()
    markerApi.current?.(Math.min(1, Math.max(0, (ev.clientX - r.left) / r.width)))
  }
  const onCoupeLeave = () => markerApi.current?.(null)
  const acq = scene?.meta?.acquisition_date ? String(scene.meta.acquisition_date) : '—'

  return createPortal(
    <div data-gab3d-overlay className="fixed inset-0 z-[60] flex flex-col bg-[#0b0d10]">
      <div className="flex items-center justify-between border-b border-line px-4 py-2">
        <div className="text-[13px] text-txt">
          <b className="text-mint">Vue 3D · terrain réel</b>
          {scene?.adresse && <span className="text-txt-dim"> · {scene.adresse}</span>}
          {scene?.idu && <span className="text-txt-dim"> — {scene.idu}</span>}
        </div>
        <button data-gab3d-close onClick={onClose} className="rounded px-2 py-1 text-[13px] text-txt-mut hover:text-txt">✕ Fermer</button>
      </div>
      {q.isLoading && <div className="p-6"><Squelette lignes={6} /></div>}
      {q.isError && <div className="p-6 text-[13px] text-coral">Scène indisponible.</div>}
      {scene && (
        <div className="flex min-h-0 flex-1">
          <div className="relative min-h-0 flex-1 border-r border-line">
            {webgl && dispo
              ? <Vue3D scene={scene} axeSel={axeSel} markerApi={markerApi} />
              : <div data-gab3d-fallback className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center text-[12px] text-txt-mut">
                  <p>{webgl ? 'Terrain non couvert ici.' : 'WebGL indisponible — repli sur le plan et les coupes.'}</p>
                  <img src={gabPlanSvgUrl(idu, 'sombre')} alt="Plan-clé" className="max-w-[380px]" />
                </div>}
            <p className="pointer-events-none absolute inset-x-0 bottom-0 bg-black/55 px-3 py-1.5 text-[10px] leading-snug text-txt-dim">
              Courbes de niveau tous les mètres (trait fort tous les 5 m) · hauteurs = longueurs, sans exagération.
              Cotes indicatives issues du MNT IGN. Pas de grille 1 m. Référentiel IGN 1989. Acquisition {acq}. Précision locale à établir.
            </p>
          </div>
          {/* panneau : onglets Plan · Coupe A · Coupe B */}
          <div className="flex w-[440px] shrink-0 flex-col bg-[#0f1216]">
            <div className="flex gap-1 border-b border-line px-2 py-1.5 text-[11px]">
              {([['plan', 'Plan'], ...coupes.map((l) => [l, `Coupe ${l}`] as [string, string])] as [string, string][]).map(([k, lab]) => (
                <button key={k} onClick={() => setTab(k as 'plan' | 'A' | 'B')}
                  className={`rounded px-2 py-1 ${tab === k ? 'bg-mint/20 text-mint' : 'text-txt-mut hover:text-txt'}`}>{lab}</button>
              ))}
              <button onClick={() => setAgrandi(true)} className="ml-auto rounded px-2 py-1 text-txt-mut hover:text-txt">⤢ Agrandir</button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-3">
              {tab === 'plan'
                ? <img src={gabPlanSvgUrl(idu, 'sombre')} alt="Plan-clé" className="w-full rounded border border-line" />
                : <img src={gabCoupeSvgUrl(idu, tab, 'sombre')} alt={`Coupe ${tab}`} onMouseMove={onCoupeHover} onMouseLeave={onCoupeLeave}
                       className="w-full cursor-crosshair rounded border border-line" />}
              <p className="mt-2 text-[9px] leading-snug text-txt-ghost">
                Détails techniques — scène {scene.scene_id} · couverture parcelle {Math.round((scene.etat?.terrain_couverture ?? 0) * 100)} %
                {axeSel ? ' · survolez la coupe pour repérer le point en 3D' : ''}
              </p>
            </div>
          </div>
        </div>
      )}
      {/* coupe agrandie */}
      {agrandi && scene && (
        <div className="absolute inset-0 z-[70] flex items-center justify-center bg-black/80 p-6" onClick={() => setAgrandi(false)}>
          <img src={tab === 'plan' ? gabPlanSvgUrl(idu, 'sombre') : gabCoupeSvgUrl(idu, tab, 'sombre')}
               alt="Agrandie" className="max-h-full max-w-full rounded border border-line" onClick={(e) => e.stopPropagation()} />
        </div>
      )}
    </div>,
    document.body)
}
