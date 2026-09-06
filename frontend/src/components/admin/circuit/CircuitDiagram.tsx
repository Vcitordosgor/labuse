// CIRCUIT-P (lot 3) — LE CIRCUIT PAR FAMILLES. Neuf+ blocs de réservoirs à gauche (les familles),
// douze blocs de robinets à droite (les catégories), la pompe au milieu. Un bloc porte une pastille
// par élément (colorée hors « ça coule ») et « n à regarder » / « tout va bien ». Un clic déplie un
// bloc (un seul par colonne). Par défaut, seuls les éléments à regarder sont listés ; l'interrupteur
// « Ne montrer que ce qui cloche » montre tout. Survoler une ligne allume son chemin (famille →
// pompe → catégories). Tuyaux SVG au niveau des blocs (familles + catégories + 2). Aucun nom tronqué
// (deux lignes par élément). Redessin sur redimensionnement, dépliage, défilement.
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'

import { cheminsAllumes, construireMaps, koTank, koTap } from './diagram'
import type { CircuitData, Reservoir, Robinet } from './types'

type Hover = { type: 'reservoir'; id: number } | { type: 'robinet'; id: string } | null
type Ouvrir = (type: 'reservoir' | 'robinet' | 'pompe', id: number | string) => void

export function CircuitDiagram({ data, groupe, onOpen }:
  { data: CircuitData; groupe: (number | string)[] | null; onOpen: Ouvrir }) {
  const maps = useMemo(() => construireMaps(data), [data])
  const [openFam, setOpenFam] = useState<string | null>(null)
  const [openCat, setOpenCat] = useState<string | null>(null)
  const [koOnly, setKoOnly] = useState(true)
  const [query, setQuery] = useState('')
  const [hover, setHover] = useState<Hover>(null)
  const [tick, setTick] = useState(0)

  const diagramRef = useRef<HTMLDivElement>(null)
  const tanksRef = useRef<HTMLDivElement>(null)
  const tapsRef = useRef<HTMLDivElement>(null)
  const pumpRef = useRef<HTMLDivElement>(null)
  const [pipes, setPipes] = useState<{ d: string; cls: string }[]>([])

  const q = query.trim().toLowerCase()
  const enGroupe = !!groupe && groupe.length > 0
  const idsGroupe = useMemo(() => new Set((groupe || []).map(String)), [groupe])

  // moteurs distincts (pour le bloc pompe) — le code est la vérité.
  const nMoteurs = useMemo(() =>
    new Set(Object.values(data.chiffres).map((c: any) => c.moteur).filter(Boolean)).size, [data])

  const lit = useMemo(() => cheminsAllumes(hover, maps), [hover, maps])

  // ── visibilité d'une ligne : recherche > groupe > « que ce qui cloche » ──
  const tankVisible = (t: Reservoir) => {
    if (q) return (t.nom + ' ' + (t.producteur || '')).toLowerCase().includes(q)
    if (enGroupe) return idsGroupe.has(String(t.id))
    return koOnly ? koTank(t.etat) : true
  }
  const tapVisible = (t: Robinet) => {
    if (q) return (t.nom + ' ' + t.id + ' ' + (t.chiffres || []).join(' ')).toLowerCase().includes(q)
    if (enGroupe) return idsGroupe.has(String(t.id))
    return koOnly ? koTap(t.etat) : true
  }

  // ── tuyaux SVG (au niveau des blocs) : stubs + collecteur→pompe + distributeur→pompe ──
  useLayoutEffect(() => {
    const grid = diagramRef.current, tanks = tanksRef.current, taps = tapsRef.current, pump = pumpRef.current
    if (!grid || !tanks || !taps || !pump) return
    if (typeof window !== 'undefined' && window.innerWidth <= 1100) { setPipes([]); return }
    const gb = grid.getBoundingClientRect()
    const rel = (el: Element) => {
      const r = el.getBoundingClientRect()
      return { l: r.left - gb.left, r: r.right - gb.left, y: r.top - gb.top + Math.min(r.height, 52) / 2 }
    }
    const tc = tanks.getBoundingClientRect(), rc = taps.getBoundingClientRect(), pb = pump.getBoundingClientRect()
    const cx = tc.right - gb.left + 36, dx = rc.left - gb.left - 36
    const py = pb.top - gb.top + pb.height / 2
    const pumpL = pb.left - gb.left, pumpR = pb.right - gb.left
    const famHds = [...tanks.querySelectorAll('.node .hd')].map(rel)
    const catHds = [...taps.querySelectorAll('.node .hd')].map(rel)
    const litFam = new Set([...lit.familles])
    const litCat = new Set([...lit.categories])
    const famNoms = [...tanks.querySelectorAll<HTMLElement>('.node')].map((n) => n.dataset.fam || '')
    const catSlugs = [...taps.querySelectorAll<HTMLElement>('.node')].map((n) => n.dataset.cat || '')
    const out: { d: string; cls: string }[] = []
    // stubs famille (un par bloc)
    famHds.forEach((r, i) => out.push({
      d: `M${r.r},${r.y} L${cx},${r.y}`, cls: litFam.has(famNoms[i]) ? 'flow' : 'pipe' }))
    // stubs catégorie (un par bloc)
    catHds.forEach((r, i) => out.push({
      d: `M${dx},${r.y} L${r.l},${r.y}`, cls: litCat.has(catSlugs[i]) ? 'flow' : 'pipe' }))
    // collecteur (rail gauche) + connecteur pompe, D'UN SEUL TRAIT
    const fys = famHds.map((r) => r.y).concat(py)
    const cys = catHds.map((r) => r.y).concat(py)
    out.push({ d: `M${cx},${Math.min(...fys)} L${cx},${Math.max(...fys)} M${cx},${py} L${pumpL},${py}`,
      cls: litFam.size ? 'flow' : 'pipe' })
    out.push({ d: `M${dx},${Math.min(...cys)} L${dx},${Math.max(...cys)} M${dx},${py} L${pumpR},${py}`,
      cls: litCat.size ? 'flow' : 'pipe' })
    // fuites (pointillé rouge, agrégées une par couple famille↔catégorie), hors pompe
    const slugFam = new Map<string, string>()
    for (const r of data.reservoirs) if (r.slug) slugFam.set(r.slug, maps.famDeReservoir.get(r.id) || '')
    const vus = new Set<string>()
    let lane = 0
    for (const f of data.fuites || []) {
      const cats = [f.robinet_a, f.robinet_b].map((rid: string) => maps.robinetById.get(rid)?.categorie).filter((x: string | undefined): x is string => !!x)
      const fams: string[] = (data.chiffres[f.chiffre_id]?.reservoirs || []).map((s: string) => slugFam.get(s)).filter((x: string | undefined): x is string => !!x)
      for (const cat of cats) for (const fam of fams) {
        const key = fam + '→' + cat
        if (vus.has(key)) continue
        vus.add(key); lane++
        const fi = famNoms.indexOf(fam), ci = catSlugs.indexOf(cat)
        if (fi < 0 || ci < 0) continue
        const a = famHds[fi], b = catHds[ci], top = -10 - lane * 7
        out.push({ d: `M${a.r},${a.y + 8} L${cx + 14 + lane * 5},${a.y + 8} L${cx + 14 + lane * 5},${top} L${dx - 14 - lane * 5},${top} L${dx - 14 - lane * 5},${b.y} L${b.l},${b.y}`,
          cls: 'fuite' })
      }
    }
    setPipes(out)
  }, [data, maps, openFam, openCat, koOnly, q, enGroupe, lit, tick])

  // redessin sur redimensionnement + défilement
  useEffect(() => {
    const bump = () => setTick((t) => t + 1)
    window.addEventListener('resize', bump)
    window.addEventListener('scroll', bump, { passive: true })
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(bump) : null
    if (ro && diagramRef.current) ro.observe(diagramRef.current)
    return () => { window.removeEventListener('resize', bump); window.removeEventListener('scroll', bump); ro?.disconnect() }
  }, [])

  const dateFr = (s: string | null) => s ? new Date(s).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' }) : ''
  const parentNom = (rid: string | null) => rid ? (maps.robinetById.get(rid)?.nom || rid) : ''

  const famOuverte = (nom: string, aMatch: boolean) => openFam === nom || ((!!q || enGroupe) && aMatch)
  const catOuverte = (slug: string, aMatch: boolean) => openCat === slug || ((!!q || enGroupe) && aMatch)

  // pompe
  const residuel = data.residuel
  const m = data.manifeste || {}
  const pointeurs = [m.scoring_run, m.mvt_run, m.division_run].filter(Boolean)
  const pointeursMultiples = new Set(pointeurs).size > 1

  return (
    <>
      <div className="cbar">
        <input placeholder="Chercher un réservoir, un robinet, un chiffre…" value={query}
          onChange={(e) => setQuery(e.target.value)} />
        <button className={`sw ${koOnly ? 'on' : ''}`} onClick={() => setKoOnly((v) => !v)}>
          <span>Ne montrer que ce qui cloche</span><span className="tr"><i /></span>
        </button>
        <div className="legend">
          <span><i style={{ background: 'var(--mint)' }} />ça coule</span>
          <span><i style={{ background: 'var(--ambre)' }} />à regarder</span>
          <span><i style={{ background: 'var(--rouge)' }} />bloqué ou fuite</span>
          <span><i style={{ background: 'var(--gris)' }} />vide, manuel</span>
          <span><i style={{ background: 'var(--mauve)' }} />agent</span>
        </div>
      </div>

      <div className="diagram" ref={diagramRef}>
        <svg><g>{pipes.map((p, i) => <path key={i} d={p.d} className={p.cls} />)}</g></svg>

        {/* réservoirs */}
        <div>
          <div className="colh"><b>Réservoirs</b>
            <span>{data.compteurs.reservoirs}, {data.compteurs.a_regarder} à regarder</span></div>
          <div ref={tanksRef}>
            {data.familles.map((f) => {
              const tanks = f.ids.map((id) => maps.reservoirById.get(id)).filter(Boolean) as Reservoir[]
              const visibles = tanks.filter(tankVisible)
              const ko = tanks.filter((t) => koTank(t.etat)).length
              const open = famOuverte(f.nom, visibles.length > 0)
              const dim = hover ? !lit.familles.has(f.nom) : false
              return (
                <div key={f.nom} className={`node ${open ? 'open' : ''} ${dim ? 'dim' : ''} ${hover && lit.familles.has(f.nom) ? 'lit' : ''}`} data-fam={f.nom}>
                  <button className="hd" onClick={() => setOpenFam((v) => v === f.nom ? null : f.nom)}>
                    <span><span className="t">{f.nom}</span>
                      <span className="dots">{tanks.map((t) => <i key={t.id} className={t.etat[0] === 'mint' ? '' : t.etat[0]} />)}</span></span>
                    <span><span className="c">{tanks.length} réservoir{tanks.length > 1 ? 's' : ''}</span><br />
                      <span className={`av ${ko ? '' : 'ok'}`}>{ko ? `${ko} à regarder` : 'tout va bien'}</span></span>
                  </button>
                  <div className="rows">{visibles.map((t) => (
                    <button key={t.id} className="row" onMouseEnter={() => setHover({ type: 'reservoir', id: t.id })}
                      onMouseLeave={() => setHover(null)} onClick={() => onOpen('reservoir', t.id)}>
                      <i className={t.etat[0] === 'mint' ? '' : t.etat[0]} />
                      <span className="nm">{t.nom}</span>
                      <span className={`st ${t.etat[0] === 'mint' ? '' : t.etat[0]}`}>{t.etat[1]}</span>
                      <span className="mt">{t.millesime || '—'}{t.dernier_controle ? ` · contrôlé le ${dateFr(t.dernier_controle)}` : ''}{t.cadence_jours ? ` · ${t.cadence_jours} j` : ''}</span>
                    </button>
                  ))}</div>
                </div>
              )
            })}
          </div>
        </div>

        {/* la pompe */}
        <div>
          <div className="colh"><b>La pompe</b></div>
          <div className="pump" ref={pumpRef} onClick={() => onOpen('pompe', 'pompe')}>
            <div className="t">Le moteur</div>
            <div className="d">{nMoteurs} moteurs, {data.compteurs.chiffres} chiffres, une définition chacun.</div>
            <span className="run">{data.run_servi}</span>
            {data.candidat
              ? <div className="st ambre">Candidat {data.candidat} prêt : lis la note de version, puis bascule.</div>
              : residuel?.changees
                ? <div className="st ambre">Eau nouvelle en attente : {residuel.detail}.</div>
                : <div className="st mint">Rien en attente.</div>}
            {pointeursMultiples && <div className="st rouge">{pointeurs.length} pointeurs de run au lieu d'un.</div>}
          </div>
        </div>

        {/* robinets */}
        <div>
          <div className="colh"><b>Robinets</b>
            <span>{data.compteurs.robinets}, {data.compteurs.robinets_a_regarder} à regarder</span></div>
          <div ref={tapsRef}>
            {data.categories.map((c) => {
              const taps = c.ids.map((id) => maps.robinetById.get(id)).filter(Boolean) as Robinet[]
              const visibles = taps.filter(tapVisible)
              const ko = taps.filter((t) => koTap(t.etat)).length
              const open = catOuverte(c.slug, visibles.length > 0)
              const dim = hover ? !lit.categories.has(c.slug) : false
              return (
                <div key={c.slug} className={`node ${open ? 'open' : ''} ${dim ? 'dim' : ''} ${hover && lit.categories.has(c.slug) ? 'lit' : ''}`} data-cat={c.slug}>
                  <button className="hd" onClick={() => setOpenCat((v) => v === c.slug ? null : c.slug)}>
                    <span><span className="t">{c.nom}</span>
                      <span className="dots">{taps.map((t) => <i key={t.id} className={t.etat[0] === 'mint' ? '' : t.etat[0]} />)}</span></span>
                    <span><span className="c">{taps.length} robinet{taps.length > 1 ? 's' : ''}</span><br />
                      <span className={`av ${ko ? '' : 'ok'}`}>{ko ? `${ko} à regarder` : 'tout va bien'}</span></span>
                  </button>
                  <div className="rows">{visibles.map((t) => (
                    <button key={t.id} className="row" onMouseEnter={() => setHover({ type: 'robinet', id: t.id })}
                      onMouseLeave={() => setHover(null)} onClick={() => onOpen('robinet', t.id)}>
                      <i className={t.etat[0] === 'mint' ? '' : t.etat[0]} />
                      <span className="nm">{t.nom}</span>
                      <span className={`st ${t.etat[0] === 'mint' ? '' : t.etat[0]}`}>{t.etat[1]}</span>
                      <span className="mt">{(t.chiffres || []).length ? `${t.chiffres.length} chiffre${t.chiffres.length > 1 ? 's' : ''}` : 'tuiles ou géométries'}{t.parent ? ` · dans ${parentNom(t.parent)}` : ''}</span>
                    </button>
                  ))}</div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </>
  )
}
