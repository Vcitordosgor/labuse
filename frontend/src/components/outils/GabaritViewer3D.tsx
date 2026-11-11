// GABARIT-3D-1 (pilote, étape 2) — VISIONNEUSE Three.js, chargée à la demande, réservée aux admins.
//
// Sur la SCÈNE corrigée du serveur (mêmes faces que les coupes) : caméra ORTHOGRAPHIQUE cadrée,
// rotation + zoom (OrbitControls), terrain affiché avec les FACES DU SERVEUR + courbes de niveau,
// volumes schématiques (bâti), contours cadastre/zone posés sur le terrain, coupes + plan-clé à côté.
// Safari : canvas/textures bornés, ressources libérées à la fermeture, repli sur plan + coupes si WebGL
// tombe. AUCUN plafond de hauteur n'est dessiné (hauteurs en pente = mandat suivant).
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useQuery } from '@tanstack/react-query'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { getGabaritScene, gabCoupeSvgUrl, gabPlanSvgUrl, type GabScene, type GabMesh, type GabPoly } from '../../lib/api'
import { Squelette } from '../Loading'

const C_TERRAIN_LOW = new THREE.Color('#3a4a52')
const C_TERRAIN_HIGH = new THREE.Color('#9fb3a8')
const C_NIVEAU = 0x5b6670
const C_CADASTRE = 0xe5e7eb
const C_ZONE = 0x36c99a
const C_BATI = 0x9aa0a6

function webglOK(): boolean {
  try {
    const c = document.createElement('canvas')
    return !!(c.getContext('webgl2') || c.getContext('webgl'))
  } catch { return false }
}

// repère : local (x=est, y=nord, z=altitude) → Three (x, altitude, -nord) ; y-up, nord vers -Z.
function terrainMesh(f: GabMesh): { mesh: THREE.Mesh; zmin: number; zmax: number; box: THREE.Box3 } {
  const g = new THREE.BufferGeometry()
  const pos = new Float32Array(f.vertices.length * 3)
  let zmin = Infinity, zmax = -Infinity
  f.vertices.forEach((p, i) => { pos[i * 3] = p[0]; pos[i * 3 + 1] = p[2]; pos[i * 3 + 2] = -p[1]; zmin = Math.min(zmin, p[2]); zmax = Math.max(zmax, p[2]) })
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3))
  const idx: number[] = []
  f.triangles.forEach((t) => { idx.push(t[0], t[1], t[2]) })
  g.setIndex(idx)
  // couleur par altitude (ramp)
  const col = new Float32Array(f.vertices.length * 3)
  const span = Math.max(zmax - zmin, 1e-6)
  f.vertices.forEach((p, i) => {
    const c = C_TERRAIN_LOW.clone().lerp(C_TERRAIN_HIGH, (p[2] - zmin) / span)
    col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b
  })
  g.setAttribute('color', new THREE.BufferAttribute(col, 3))
  g.computeVertexNormals()
  const mat = new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide, flatShading: true })
  const mesh = new THREE.Mesh(g, mat)
  g.computeBoundingBox()
  return { mesh, zmin, zmax, box: g.boundingBox!.clone() }
}

// courbes de niveau : marching-triangles sur les faces servies, à intervalle « rond »
function courbesNiveau(f: GabMesh, zmin: number, zmax: number): THREE.LineSegments {
  const span = zmax - zmin
  const step = span > 60 ? 10 : span > 20 ? 5 : span > 8 ? 2 : 1
  const segs: number[] = []
  const V = f.vertices
  const interp = (a: number[], b: number[], lv: number) => {
    const t = (lv - a[2]) / (b[2] - a[2])
    return [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]), lv]
  }
  for (const tri of f.triangles) {
    const p = [V[tri[0]], V[tri[1]], V[tri[2]]]
    const lo = Math.min(p[0][2], p[1][2], p[2][2]), hi = Math.max(p[0][2], p[1][2], p[2][2])
    for (let lv = Math.ceil(lo / step) * step; lv <= hi; lv += step) {
      const cross: number[][] = []
      for (let e = 0; e < 3; e++) {
        const a = p[e], b = p[(e + 1) % 3]
        if ((a[2] - lv) * (b[2] - lv) < 0) cross.push(interp(a, b, lv))
      }
      if (cross.length === 2) {
        segs.push(cross[0][0], cross[0][2], -cross[0][1], cross[1][0], cross[1][2], -cross[1][1])
      }
    }
  }
  const g = new THREE.BufferGeometry()
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(segs), 3))
  return new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: C_NIVEAU, transparent: true, opacity: 0.5 }))
}

// contour (cadastre/zone) POSÉ sur le terrain : on relève l'altitude par raycast vertical sur le mesh
function contourDrape(polys: GabPoly[], terrain: THREE.Mesh, color: number, zmax: number): THREE.Group {
  const grp = new THREE.Group()
  const ray = new THREE.Raycaster()
  const down = new THREE.Vector3(0, -1, 0)
  const mat = new THREE.LineBasicMaterial({ color })
  for (const poly of polys) {
    for (const ring of [poly.ext, ...(poly.trous || [])]) {
      const pts: THREE.Vector3[] = []
      for (const [x, y] of ring) {
        ray.set(new THREE.Vector3(x, zmax + 50, -y), down)
        const hit = ray.intersectObject(terrain)
        pts.push(new THREE.Vector3(x, (hit[0] ? hit[0].point.y : 0) + 0.3, -y))
      }
      if (pts.length > 1) grp.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), mat))
    }
  }
  return grp
}

// volume schématique de bâti : empreinte extrudée du pied au faîtage (dessus horizontal), sans toiture cotée
function batiVolume(empreinte: GabPoly[], pied: number, hauteur: number | null): THREE.Group {
  const grp = new THREE.Group()
  const h = hauteur && hauteur > 0 ? hauteur : 0
  for (const poly of empreinte) {
    const shape = new THREE.Shape(poly.ext.map(([x, y]) => new THREE.Vector2(x, -y)))
    if (h > 0) {
      const geo = new THREE.ExtrudeGeometry(shape, { depth: h, bevelEnabled: false })
      geo.rotateX(-Math.PI / 2)              // extrude +Z → +Y (vertical)
      geo.translate(0, pied, 0)
      grp.add(new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ color: C_BATI, transparent: true, opacity: 0.55, flatShading: true })))
    } else {                                 // hauteur non attribuée → empreinte posée au sol
      const pts = poly.ext.map(([x, y]) => new THREE.Vector3(x, pied + 0.2, -y))
      grp.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: C_BATI })))
    }
  }
  return grp
}

function Vue3D({ scene }: { scene: GabScene }) {
  const host = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const el = host.current
    const faces = scene.terrain?.faces_parcelle
    if (!el || !faces || !faces.vertices.length) return
    // le conteneur peut n'avoir pas encore sa taille au montage → repli + ResizeObserver
    const W = el.clientWidth || el.parentElement?.clientWidth || window.innerWidth
    const H = el.clientHeight || el.parentElement?.clientHeight || window.innerHeight
    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'low-power' })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))   // Safari : borne la taille
    renderer.setSize(W, H)
    el.appendChild(renderer.domElement)
    const sc = new THREE.Scene()
    sc.background = new THREE.Color('#0f1115')

    const { mesh, zmin, zmax, box } = terrainMesh(faces)
    sc.add(mesh)
    sc.add(courbesNiveau(faces, zmin, zmax))
    if (scene.terrain?.faces_voisinage?.vertices?.length) sc.add(terrainMesh(scene.terrain.faces_voisinage).mesh)
    sc.add(contourDrape(scene.contour_cadastral, mesh, C_CADASTRE, zmax))
    sc.add(contourDrape(scene.zone_implantation, mesh, C_ZONE, zmax))
    for (const b of scene.batiments) sc.add(batiVolume(b.empreinte, b.pied_m ?? zmin, b.hauteur_m))

    sc.add(new THREE.AmbientLight(0xffffff, 0.75))
    const sun = new THREE.DirectionalLight(0xffffff, 0.8); sun.position.set(-1, 2, 1); sc.add(sun)

    const ctr = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())
    const r = Math.max(size.x, size.z, size.y) * 0.75 + 5
    const aspect = W / H
    const cam = new THREE.OrthographicCamera(-r * aspect, r * aspect, r, -r, 0.1, r * 20)
    cam.position.set(ctr.x + r, ctr.y + r * 1.1, ctr.z + r)
    cam.lookAt(ctr)
    const controls = new OrbitControls(cam, renderer.domElement)
    controls.target.copy(ctr); controls.enablePan = true; controls.update()

    let raf = 0, stop = false
    const loop = () => { if (stop) return; controls.update(); renderer.render(sc, cam); raf = requestAnimationFrame(loop) }
    loop()
    const onResize = () => {
      const w = el.clientWidth || W, h = el.clientHeight || H
      if (w < 2 || h < 2) return
      renderer.setSize(w, h); cam.left = -r * (w / h); cam.right = r * (w / h); cam.top = r; cam.bottom = -r
      cam.updateProjectionMatrix()
    }
    window.addEventListener('resize', onResize)
    const ro = new ResizeObserver(onResize); ro.observe(el)   // ajuste dès que le conteneur a sa taille
    // libère TOUT à la fermeture (Safari : pas de fuite après 10 ouvertures)
    return () => {
      stop = true; cancelAnimationFrame(raf); window.removeEventListener('resize', onResize); ro.disconnect()
      controls.dispose()
      sc.traverse((o) => {
        const m = o as THREE.Mesh
        if (m.geometry) m.geometry.dispose()
        const mat = m.material as THREE.Material | THREE.Material[] | undefined
        if (Array.isArray(mat)) mat.forEach((x) => x.dispose()); else mat?.dispose()
      })
      renderer.dispose()
      renderer.forceContextLoss()
      el.removeChild(renderer.domElement)
    }
  }, [scene])
  return <div ref={host} className="h-full w-full" data-gab3d-canvas />
}

export function GabaritViewer3D({ idu, onClose }: { idu: string; onClose: () => void }) {
  const q = useQuery({ queryKey: ['gabarit-scene', idu], queryFn: () => getGabaritScene(idu), retry: false })
  const scene = q.data
  const [webgl] = useState(webglOK)
  const dispo = scene?.disponible && !!scene.terrain?.faces_parcelle?.vertices?.length

  // PORTAL vers document.body : un ancêtre (panneau outils) a un `transform`, qui capturerait un
  // `position:fixed`. Le portal garantit un overlay plein VIEWPORT.
  return createPortal(
    <div data-gab3d-overlay className="fixed inset-0 z-[60] flex flex-col bg-black/95">
      <div className="flex items-center justify-between border-b border-line px-4 py-2">
        <div className="text-[13px] text-txt">
          <b className="text-mint">Vue 3D pilote</b> — terrain réel (admin)
          {scene?.adresse && <span className="text-txt-dim"> · {scene.adresse}</span>}
          {scene?.scene_id && <span className="text-txt-ghost"> · scène {scene.scene_id}</span>}
        </div>
        <button data-gab3d-close onClick={onClose} className="rounded px-2 py-1 text-[13px] text-txt-mut hover:text-txt">✕ Fermer</button>
      </div>
      {q.isLoading && <div className="p-6"><Squelette lignes={6} /></div>}
      {q.isError && <div className="p-6 text-[13px] text-coral">Scène indisponible.</div>}
      {scene && (
        <div className="flex min-h-0 flex-1">
          {/* vue 3D (repli plan + coupes si WebGL tombe ou terrain absent) */}
          <div className="relative min-h-0 flex-1 border-r border-line">
            {webgl && dispo
              ? <Vue3D scene={scene} />
              : <div data-gab3d-fallback className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center text-[12px] text-txt-mut">
                  <p>{webgl ? 'Terrain non couvert ici.' : 'WebGL indisponible — repli sur le plan et les coupes.'}</p>
                  <img src={gabPlanSvgUrl(idu, 'sombre')} alt="Plan-clé" className="max-w-[360px]" />
                </div>}
            <p className="pointer-events-none absolute inset-x-0 bottom-0 bg-black/60 px-3 py-1.5 text-[10px] leading-snug text-txt-dim">
              Cotes indicatives issues du MNT IGN. Pas de grille 1 m. Référentiel IGN 1989.
              {scene.meta?.acquisition_date ? ` Acquisition ${String(scene.meta.acquisition_date)}.` : ' Acquisition —.'} Précision locale à établir.
            </p>
          </div>
          {/* coupes + plan-clé à côté */}
          <div className="w-[420px] shrink-0 overflow-y-auto bg-surface-1 p-3">
            <img src={gabPlanSvgUrl(idu, 'sombre')} alt="Plan-clé" className="mb-2 w-full rounded border border-line" />
            {(scene.coupes || []).map((c) => (
              <img key={String((c as { label?: string }).label)} src={gabCoupeSvgUrl(idu, String((c as { label?: string }).label ?? 'A'), 'sombre')}
                   alt="Coupe" className="mb-2 w-full rounded border border-line" />
            ))}
          </div>
        </div>
      )}
    </div>,
    document.body)
}
