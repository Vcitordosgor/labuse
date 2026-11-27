import { cleImplantation, lireImplantation } from '../../lib/implantationLocale'
import { useEffect, useRef, useState } from 'react'
import { useOuvrirDocument } from '../../lib/ouvrirDocument'
import type { GabGeom } from '../../lib/api'
import { createPortal } from 'react-dom'
import { useQuery } from '@tanstack/react-query'

type Pt = [number, number]
type Polys = Pt[][][]
type Plan = { terrain: Polys; zone: Polys; bati: Polys; limites: { nom: string; ligne: Pt[] }[]; solde: number | null }
type Cote = { nom: string; a: Pt; b: Pt; m: number; wgs: Pt[] }
type Bilan = { contour: GabGeom; aire: number; horsZone: number; cotes: Cote[] }
const fmt = (n: number) => n.toLocaleString('fr-FR', { maximumFractionDigits: 2 })
const couches = ['terrain', 'zone', 'bati'] as const
const couleurs = { terrain: '#d5d9d8', zone: '#53b895', bati: '#75838c' }

function exporter(idu: string, plan: Plan, pts: Pt[], bilan: Bilan) {
  const lignes: string[] = []
  function paire(code: number, v: number | string) { lignes.push(String(code), String(v)) }
  function section(nom: string) { paire(0, 'SECTION'); paire(2, nom) }
  function point(code: number, [x, y]: Pt) { paire(code, x); paire(code + 10, y); paire(code + 20, 0) }
  function ligne(calque: string, a: Pt, b: Pt) {
    paire(0, 'LINE'); paire(8, calque); point(10, a); point(11, b)
  }
  function contour(calque: string, ring: Pt[]) {
    paire(0, 'POLYLINE'); paire(8, calque); paire(66, 1); point(10, [0, 0]); paire(70, 1)
    for (const pt of ring) { paire(0, 'VERTEX'); paire(8, calque); point(10, pt) }
    paire(0, 'SEQEND'); paire(8, calque)
  }
  section('HEADER'); paire(9, '$ACADVER'); paire(1, 'AC1009'); paire(0, 'ENDSEC')
  section('ENTITIES')
  for (const k of couches) for (const poly of plan[k]) for (const ring of poly) contour(k.toUpperCase(), ring.slice(0, -1))
  contour('IMPLANTATION', pts)
  for (const [i, limite] of plan.limites.entries()) {
    for (let j = 1; j < limite.ligne.length; j++) ligne('LIMITE_'+(i+1), limite.ligne[j-1], limite.ligne[j])
  }
  for (const c of bilan.cotes) {
    if (c.m > 0) ligne('COTES', c.a, c.b)
    paire(0, 'TEXT'); paire(8, 'COTES'); point(10, [(c.a[0]+c.b[0])/2, (c.a[1]+c.b[1])/2]); paire(40, 0.35)
    paire(1, c.nom.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace('·','-') + '  ' + c.m.toFixed(2) + ' m')
  }
  paire(0, 'ENDSEC'); paire(0, 'EOF')
  const url = URL.createObjectURL(new Blob([lignes.join('\r\n')+'\r\n'], { type: 'application/dxf' }))
  const a = document.createElement('a'); a.href = url; a.download = idu+'-implantation-EPSG2975-metres.dxf'; a.click()
  setTimeout(() => URL.revokeObjectURL(url), 15000)
}

export type ProjetDessine = { idu: string; pts: Pt[]; bilan: Bilan }

export function CotesProjet({projet}: {projet: ProjetDessine}) {
  return <details data-cotes-projet className="text-xs"><summary>Mon implantation · {fmt(projet.bilan.aire)} m² · cotes</summary>
    {projet.bilan.cotes.map(c=><div key={c.nom}>{c.nom} · {fmt(c.m)} m</div>)}</details>
}

export function PdfProjet({idu, pts}: {idu: string; pts: Pt[]}) {
  const {ouvrir,enCours,erreur} = useOuvrirDocument()
  return <><button disabled={!!enCours} className="rounded border border-line p-2" onClick={() => ouvrir(
    '/outils/gabarit/'+encodeURIComponent(idu)+'/implantation/plan.pdf', 'implantation',
    {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(pts)}, idu+'-implantation-cotee.pdf'
  )}>Exporter le plan coté en PDF</button>{erreur && <p role="alert">{erreur}</p>}</>
}

export function Implantation({idu, onProjet}: {idu: string; onProjet: (p: ProjetDessine | null)=>void}) {
  const [ouvert, ouvrir] = useState(false)
  const cle = cleImplantation(idu)
  const [initial] = useState(() => lireImplantation(idu))
  const [pts, tracer] = useState<Pt[]>(initial.pts)
  const [ferme, fermer] = useState(initial.ferme)
  useEffect(() => {
    if (!ouvert) return
    try { localStorage.setItem(cle, JSON.stringify({pts, ferme})) } catch { /* stockage facultatif */ }
  }, [cle, ouvert, pts, ferme])
  const [sel, choisir] = useState(0)
  const drag = useRef<number | null>(null)
  const svg = useRef<SVGSVGElement>(null)
  const base = '/outils/gabarit/'+encodeURIComponent(idu)+'/implantation'
  const plan = useQuery<Plan>({ queryKey: ['plan-implantation',idu], enabled: ouvert, queryFn: async () => {
    const r = await fetch(base); if (!r.ok) throw Error('Plan inaccessible.'); return r.json()
  }})
  const [fixes, fixer] = useState<Pt[]>([])
  useEffect(() => { const t = setTimeout(()=>fixer(pts), 250); return ()=>clearTimeout(t) }, [pts])
  const mesures = useQuery<Bilan>({ queryKey:['cotes-implantation',idu,fixes], enabled: ferme && fixes===pts, retry:false,
    queryFn: async ({signal}) => {
      const r = await fetch(base+'/cotes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(fixes),signal})
      if (!r.ok) throw Error(r.status===422 ? 'Contour invalide. Déplacez les sommets ou reprenez le tracé.' : 'Calcul des cotes indisponible.')
      return r.json()
    }})
  useEffect(()=>{if (!ouvert) return; const esc=(e:KeyboardEvent)=>{if(e.key==='Escape') ouvrir(false)}
    window.addEventListener('keydown',esc);return ()=>window.removeEventListener('keydown',esc)},[ouvert])
  const bilan = ferme && fixes===pts ? mesures.data : undefined
  useEffect(() => { onProjet(bilan ? {idu, pts, bilan} : null) }, [idu, pts, bilan, onProjet])
  const p = plan.data
  const coins = p?.terrain.flat(2) ?? []
  const xs=coins.map(pt=>pt[0]), ys=coins.map(pt=>pt[1])
  const x0=Math.min(...xs), y1=Math.max(...ys)
  const scale=Math.min(680/(Math.max(...xs)-x0||1),460/(y1-Math.min(...ys)||1))
  const xy=([x,y]:Pt):Pt=>[20+(x-x0)*scale,20+(y1-y)*scale]
  function position(e:React.PointerEvent):Pt {
    const pt=new DOMPoint(e.clientX,e.clientY).matrixTransform(svg.current!.getScreenCTM()!.inverse())
    return [x0+(pt.x-20)/scale,y1-(pt.y-20)/scale]
  }
  const path=(line:Pt[])=>line.map((pt,i)=>(i?'L':'M')+xy(pt).join(' ')).join(' ')
  const cote=bilan?.cotes[sel]
  return <><button className="hidden md:block rounded border border-line p-2 text-mint" onClick={()=>ouvrir(true)}>Dessiner mon implantation</button>
    {ouvert && createPortal(<div role="dialog" aria-modal="true" aria-label="Implantation" className="fixed inset-0 z-[100] overflow-auto bg-surface p-5 text-txt" style={{background:'#101719'}}>
      <header className="mb-4 flex justify-between"><h2>Implantation · {idu}</h2><button onClick={()=>ouvrir(false)}>Fermer</button></header>
      {plan.isError && <p>Plan inaccessible.</p>}{!p && plan.isLoading && <p>Chargement du plan…</p>}
      {p && <div className="grid gap-5 md:grid-cols-[minmax(0,2fr)_minmax(250px,1fr)]"><section>
        <p>{ferme?'Déplacez un sommet pour modifier le contour.':'Cliquez sur le plan pour placer les sommets, puis fermez le contour.'}</p>
        <svg ref={svg} aria-label="Plan de dessin" viewBox="0 0 720 500" className="w-full rounded border border-line" style={{background:'#172123',touchAction:'none'}}
          onPointerDown={e=>{if(!ferme && e.button===0 && pts.length<256)tracer([...pts,position(e)])}}
          onPointerMove={e=>{if(drag.current!==null){const q=position(e);tracer(pts.map((v,i)=>i===drag.current?q:v))}}}
          onPointerUp={()=>{drag.current=null}} onPointerCancel={()=>{drag.current=null}}>
          {couches.map(k=>p[k].map((poly,i)=><path key={k+i} d={poly.map(r=>path(r)+'Z').join(' ')} fill={couleurs[k]} fillOpacity={k==='terrain'?0.1:0.55} stroke={couleurs[k]} fillRule="evenodd"/>))}
          {p.limites[sel] && <path d={path(p.limites[sel].ligne)} fill="none" stroke="#ffbd67" strokeWidth="3"/>}
          <path d={path(pts)+(ferme?'Z':'')} fill={ferme?'#669cff':'none'} fillOpacity=".35" stroke="#89b4ff" strokeWidth="2"/>
          {cote && <path d={path([cote.a,cote.b])} fill="none" stroke="#ffbd67" strokeWidth="2" strokeDasharray="5 3"/>}
          {cote && <text x={(xy(cote.a)[0]+xy(cote.b)[0])/2} y={(xy(cote.a)[1]+xy(cote.b)[1])/2-6}
            fill="#ffdc8f" stroke="#172123" strokeWidth="3" paintOrder="stroke" textAnchor="middle" fontSize="14">{fmt(cote.m)} m</text>}
          {pts.map((pt,i)=>{const [x,y]=xy(pt);return <circle key={i} cx={x} cy={y} r="5" fill="#a8caff" style={{cursor:'move'}}
            onPointerDown={e=>{e.stopPropagation();drag.current=i;e.currentTarget.setPointerCapture(e.pointerId)}}/>})}
        </svg><small>Nord en haut · zone disponible en vert · bâti en gris · projet en bleu</small>
        <div className="mt-3 flex gap-4">{ferme?<button onClick={()=>fermer(false)}>Reprendre le tracé</button>:<button disabled={pts.length<3} onClick={()=>fermer(true)}>Fermer le contour</button>}
          <button disabled={!pts.length} onClick={()=>{fermer(false);tracer(pts.slice(0,-1))}}>Retirer le dernier sommet</button></div>
      </section><section><h3>Distances aux limites</h3><small>Distance horizontale minimale jusqu’au bord de la parcelle côté voie ou jusqu’à la limite sélectionnée.</small>
        {ferme && !bilan && <p role="status">{mesures.isError && fixes===pts ? mesures.error.message : 'Calcul des cotes…'}</p>}
        {bilan && <><p className="my-3">Emprise dessinée · {fmt(bilan.aire)} m²</p>
          {bilan.horsZone>0.005 && <p className="text-amber">{fmt(bilan.horsZone)} m² hors zone disponible</p>}
          {p.solde!=null && bilan.aire>p.solde+0.05 && <p className="text-amber">Emprise supérieure au solde estimé de {fmt(p.solde)} m².</p>}</>}
        {p.limites.map((l,i)=><button key={i} onClick={()=>choisir(i)} aria-pressed={sel===i} className={'flex w-full justify-between border-b border-line py-1 '+(sel===i?'text-amber':'')}><span>{l.nom}</span><span>{bilan?fmt(bilan.cotes[i].m)+' m':'—'}</span></button>)}
        <button disabled={!bilan} className="mt-4 rounded border border-line p-2 disabled:opacity-40" onClick={()=>bilan && exporter(idu,p,pts,bilan)}>Exporter le plan coté en DXF</button>
        {bilan && <PdfProjet idu={idu} pts={pts} />}
        <p className="mt-2 text-xs">Coordonnées RGR92 / UTM 40S · unité du dessin : mètre.</p>
      </section></div>}
    </div>,document.body)}</>
}
