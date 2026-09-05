// CIRCUIT-1 lot 5.2 — LA PAGE CIRCUIT, conforme à docs/CIRCUIT/maquette-circuit-v5.html :
// bandeau « Tout coule, sauf : » à pastilles cliquables · trois colonnes réservoirs / pompe /
// robinets · tuyaux SVG (chemin allumé au clic, fuites en rouge) · fiche du bas à trois
// colonnes · recherche · groupes repliables · pompe collante. Remplace la fourmilière
// (Flux.tsx) et l'onglet Mise à jour (MiseAJour.tsx — ses trois endpoints sont réutilisés).
// DA : survol vert opaque contenu inversé (.cl), mauve réservé aux agents (IA), aucun camaïeu.
// Données : GET /admin/circuit (un appel, < 1 s — mesuré 0,55 s sur la base réelle).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState } from 'react'

import { useApp } from '../../store/useApp'

import {
  getAdminCircuit, getAdminCircuitNoteVersion, postAdminCircuitPurger,
  postAdminCircuitRevenir, postAdminCircuitVerifier, postAdminFluxBascule, postAdminFluxLancerRun,
  postAdminSourceVeilleInjecter,
} from '../../lib/api'

const CSS = `
.cx{--bg:#0f1512;--panel:#141b17;--panel2:#1a221d;--line:rgba(255,255,255,.09);--line2:rgba(255,255,255,.18);
 --text:#e7ece8;--muted:#94a099;--faint:#66716a;--mint:#4ADE80;--ink:#0b1a10;--mint-soft:rgba(74,222,128,.11);
 --mauve:#c084fc;--jaune:#facc15;--ambre:#f5b942;--rouge:#f87171;--gris:#7c877f;color:var(--text);
 font-size:13px;line-height:1.45;font-variant-numeric:tabular-nums}
.cx .status{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:12px 14px;border:1px solid var(--line);border-radius:6px;background:var(--panel);margin-bottom:10px}
.cx .status h1{font-size:17px;font-weight:650;margin:0 10px 0 0}
.cx .pill{display:inline-flex;align-items:center;gap:7px;padding:4px 10px;border-radius:14px;border:1px solid;font-weight:600;font-size:12px;cursor:pointer;background:none}
.cx .pill i{width:8px;height:8px;border-radius:50%;display:inline-block}
.cx .pill.rouge{color:var(--rouge);border-color:var(--rouge)}.cx .pill.rouge i{background:var(--rouge)}
.cx .pill.ambre{color:var(--ambre);border-color:var(--ambre)}.cx .pill.ambre i{background:var(--ambre)}
.cx .pill.mint{color:var(--mint);border-color:var(--mint)}.cx .pill.mint i{background:var(--mint)}
.cx .pill.gris{color:var(--muted);border-color:var(--line2)}.cx .pill.gris i{background:var(--gris)}
.cx .btn{padding:7px 13px;border:1px solid var(--mint);color:var(--mint);border-radius:6px;font-weight:600;font-size:12.5px;background:none;cursor:pointer}
.cx .btn:hover{background:var(--mint);color:var(--ink)}
.cx .btn.ghost{border-color:var(--line2);color:var(--text)}.cx .btn.ghost:hover{background:var(--mint);border-color:var(--mint);color:var(--ink)}
.cx .btn.ambre{border-color:var(--ambre);color:var(--ambre)}.cx .btn.ambre:hover{background:var(--ambre);color:var(--ink)}
.cx .btn.mauve{border-color:var(--mauve);color:var(--mauve)}.cx .btn.mauve:hover{background:var(--mauve);color:var(--ink)}
.cx .btn[disabled]{opacity:.4;pointer-events:none}
.cx .legend{display:flex;gap:14px;flex-wrap:wrap;color:var(--muted);margin:0 0 12px 2px;font-size:12px;align-items:center}
.cx .legend i{display:inline-block;width:22px;height:0;border-top:2px solid var(--mint)}
.cx .legend i.rouge{border-top:2px dashed var(--rouge)}.cx .legend i.grey{border-top-color:rgba(255,255,255,.25)}
.cx .legend input{background:var(--panel);border:1px solid var(--line);color:var(--text);padding:5px 9px;border-radius:5px;font:inherit;min-width:260px;margin-left:auto}
.cx .cl{cursor:pointer}
.cx .cl:not(.active):hover{background:var(--mint) !important;border-color:var(--mint) !important;color:var(--ink) !important}
.cx .cl:not(.active):hover *{color:var(--ink) !important;border-color:var(--ink) !important}
.cx .cl:not(.active):hover .drop{background:var(--ink)}
.cx .cl:not(.active):hover .water::after{background:var(--ink);animation:none}
.cx .circuit{position:relative;display:grid;grid-template-columns:330px 230px 320px;justify-content:center;column-gap:64px}
.cx .circuit svg{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;overflow:visible}
.cx .col h3{margin:14px 0 4px;font-size:11.5px;font-weight:600;color:var(--muted);display:flex;align-items:center;gap:8px;cursor:pointer;user-select:none}
.cx .col h3 .n{color:var(--faint);font-weight:400}.cx .col h3 .tog{margin-left:auto;color:var(--faint);font-weight:400}
.cx .row{display:flex;align-items:center;gap:7px;height:21px;padding:0 8px;border:1px solid var(--line);border-radius:4px;background:var(--panel);margin-bottom:3px;width:100%;text-align:left;font-size:12px;position:relative;color:inherit}
.cx .row.child{padding-left:20px}.cx .row.child::before{content:"›";position:absolute;left:8px;color:var(--faint)}
.cx .row .nm{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cx .row .meta{color:var(--muted);font-size:11px;flex:none;white-space:nowrap}
.cx .row.dim{opacity:.2}.cx .row.lit{border-color:var(--mint)}
.cx .row.sel{border-color:var(--mint);box-shadow:0 0 0 1px var(--mint),0 0 14px rgba(74,222,128,.25)}
.cx .water{width:7px;height:14px;border:1px solid var(--line2);border-radius:2px;position:relative;overflow:hidden;flex:none}
.cx .water::after{content:"";position:absolute;left:0;right:0;bottom:0;height:100%;background:var(--mint)}
.cx .water.nouvelle::after{background:var(--ambre);animation:cxblink 1.1s ease-in-out infinite}
.cx .water.manuel::after{background:var(--gris);height:60%}
.cx .water.direct::after{background:var(--mint);opacity:.55}
.cx .water.vide::after{height:0}.cx .water.vide{border-style:dashed}
@keyframes cxblink{50%{opacity:.35}}
.cx .clock{font-size:11px;flex:none;color:var(--mint)}.cx .clock.attendu{color:var(--ambre)}
.cx .chk{font-size:10.5px;color:var(--muted);flex:none;padding:0 5px;border:1px solid var(--line);border-radius:3px;line-height:14px;white-space:nowrap}
.cx .chk.ok{color:var(--mint);border-color:rgba(74,222,128,.45)}
.cx .chk.warn{color:var(--ambre);border-color:rgba(245,185,66,.55)}
.cx .chk.bad{color:var(--rouge);border-color:rgba(248,113,113,.55)}
.cx .drop{width:8px;height:8px;border-radius:50%;flex:none;background:var(--mint)}
.cx .drop.vide{background:transparent;border:1px dashed var(--gris)}
.cx .row.ia .nm{color:var(--mauve)}
.cx .pump-col{position:relative}
.cx .pump{position:sticky;top:70px;border:1px solid var(--line2);border-radius:8px;background:var(--panel);padding:14px 14px 12px;text-align:left;width:100%}
.cx .pump .t{font-size:15px;font-weight:650;margin-bottom:2px}
.cx .pump .d{color:var(--muted);font-size:12px}
.cx .pump .st{margin-top:8px;padding-top:8px;border-top:1px solid var(--line);font-size:12px}
.cx .pump .st.ambre{color:var(--ambre)}.cx .pump .st.mint{color:var(--mint)}
.cx .rel{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:6px}
.cx .run{padding:2px 8px;border:1px solid var(--line2);border-radius:4px;font-family:ui-monospace,Menlo,monospace;font-size:11.5px}
.cx .run.servi{border-color:var(--mint);color:var(--mint)}.cx .run.cand{border-color:var(--ambre);color:var(--ambre)}
.cx path.pipe{stroke:rgba(255,255,255,.14);stroke-width:1.5;fill:none}
.cx path.flow{stroke:var(--mint);stroke-width:2.5;fill:none;stroke-dasharray:6 7;animation:cxflow .9s linear infinite}
.cx path.fuite{stroke:var(--rouge);stroke-width:2;fill:none;stroke-dasharray:5 6;opacity:.75}
@keyframes cxflow{to{stroke-dashoffset:-13}}
.cx .sheet{position:sticky;bottom:0;background:var(--panel);border:1px solid var(--line2);border-radius:8px 8px 0 0;padding:14px 20px 16px;margin-top:14px;z-index:5}
.cx .sheet .in{display:grid;grid-template-columns:1.2fr 1.1fr 1fr;gap:20px}
.cx .sheet h4{margin:0 0 2px;font-size:15px;font-weight:650}
.cx .sheet .k{color:var(--muted);font-size:12px;margin-top:8px}
.cx .chip{display:inline-block;padding:1px 7px;border-radius:4px;background:var(--panel2);border:1px solid var(--line);margin:2px 3px 0 0;font-size:11.5px;white-space:nowrap}
.cx .chip.rouge{color:var(--rouge);border-color:var(--rouge)}.cx .chip.ambre{color:var(--ambre);border-color:var(--ambre)}
.cx .chip.ia{color:var(--mauve);border-color:rgba(192,132,252,.5)}
.cx .fiche-lien{color:var(--jaune)}
.cx .dates{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;margin-top:6px;font-size:12px}
.cx .dates div:nth-child(odd){color:var(--muted)}
.cx .muted{color:var(--muted)}
`

type Sel = { type: 'tank' | 'tap' | 'pump'; id: string } | null

export function CircuitSection() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin-circuit'], queryFn: getAdminCircuit, refetchInterval: 60_000 })
  const [sel, setSel] = useState<Sel>(null)
  const [filtre, setFiltre] = useState('')
  const [fermes, setFermes] = useState<Record<string, boolean>>({})
  const [noteLue, setNoteLue] = useState<string | null>(null)   // 5.4 : Basculer inactif tant que la note n'est pas OUVERTE
  const [note, setNote] = useState<any>(null)
  const gridRef = useRef<HTMLDivElement>(null)
  const [pipes, setPipes] = useState<{ d: string; cls: string }[]>([])
  const tracage = useApp((s) => s.tracage)
  const setTracage = useApp((s) => s.setTracage)

  const d = q.data
  const verifier = useMutation({ mutationFn: postAdminCircuitVerifier, onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-circuit'] }) })
  const purger = useMutation({ mutationFn: postAdminCircuitPurger })
  const lancer = useMutation({ mutationFn: () => postAdminFluxLancerRun('m36'), onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-circuit'] }) })
  const revenir = useMutation({ mutationFn: postAdminCircuitRevenir,
    onSuccess: () => { setNoteLue(null); setNote(null); qc.invalidateQueries({ queryKey: ['admin-circuit'] }) } })
  const basculer = useMutation({
    mutationFn: (run: string) => postAdminFluxBascule(run),
    onSuccess: () => { setNoteLue(null); setNote(null); qc.invalidateQueries({ queryKey: ['admin-circuit'] }) },
  })
  const injecter = useMutation({ mutationFn: (sourceId: number) => postAdminSourceVeilleInjecter(sourceId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-circuit'] }) })

  // ── graphe dérivé (réservoir↔chiffre↔robinet) ────────────────────────────────────────────
  const g = useMemo(() => {
    const T2C: Record<string, Set<string>> = {}; const C2R: Record<string, Set<string>> = {}
    const C2T: Record<string, Set<string>> = {}; const R2C: Record<string, Set<string>> = {}
    if (d) {
      for (const [res, cid] of d.aretes.reservoir_vers_chiffre) {
        (T2C[res] = T2C[res] || new Set()).add(cid); (C2R[cid] = C2R[cid] || new Set()).add(res)
      }
      for (const [cid, rob] of d.aretes.chiffre_vers_robinet) {
        (C2T[cid] = C2T[cid] || new Set()).add(rob); (R2C[rob] = R2C[rob] || new Set()).add(cid)
      }
    }
    return { T2C, C2R, C2T, R2C }
  }, [d])
  // ids de réservoirs du registre ↔ lignes data_sources : le registre parle en slugs, la page en
  // noms — l'allumage passe par les chiffres (slugs) ; les tanks affichés utilisent le nom.
  const litSets = useMemo(() => {
    const tanks = new Set<string>(); const taps = new Set<string>(); const chiffres = new Set<string>()
    if (!d || !sel) return { tanks, taps, chiffres }
    if (sel.type === 'tap') {
      taps.add(sel.id)
      for (const c of g.R2C[sel.id] || []) { chiffres.add(c); (g.C2R[c] || new Set()).forEach(r => tanks.add(r)) }
    } else if (sel.type === 'tank') {
      tanks.add(sel.id)
      for (const c of g.T2C[sel.id] || []) { chiffres.add(c); (g.C2T[c] || new Set()).forEach(t => taps.add(t)) }
    }
    return { tanks, taps, chiffres }
  }, [d, sel, g])

  // ── tuyaux SVG : chaque ligne visible → bord de la pompe (base) ; allumés sur sélection ──
  useEffect(() => {
    const grid = gridRef.current
    if (!grid || !d) return
    const gb = grid.getBoundingClientRect()
    const pump = grid.querySelector('.pump')
    if (!pump) return
    const pb = pump.getBoundingClientRect()
    const out: { d: string; cls: string }[] = []
    grid.querySelectorAll<HTMLElement>('.row[data-side]').forEach(el => {
      const b = el.getBoundingClientRect()
      if (b.height === 0) return
      const y = b.top + b.height / 2 - gb.top
      const side = el.dataset.side
      const lit = el.classList.contains('lit') || el.classList.contains('sel')
      const x1 = side === 'tank' ? b.right - gb.left : b.left - gb.left
      const x2 = side === 'tank' ? pb.left - gb.left : pb.right - gb.left
      const ym = pb.top + pb.height / 2 - gb.top
      const mx = (x1 + x2) / 2
      out.push({ d: `M ${x1} ${y} C ${mx} ${y}, ${mx} ${ym}, ${x2} ${ym}`, cls: lit ? 'flow' : 'pipe' })
    })
    setPipes(out)
  }, [d, sel, filtre, fermes])

  if (q.isLoading) return <div className="cx"><style>{CSS}</style><div className="muted">Circuit — chargement…</div></div>
  if (!d) return <div className="cx"><style>{CSS}</style><div className="muted">Circuit indisponible.</div></div>

  const cpt = d.compteurs
  const runsCandidats = (d.runs || []).filter((r: any) => r.statut === 'termine')
  const candidat = runsCandidats[0]?.label as string | undefined
  const fam = new Map<string, any[]>()
  for (const r of d.reservoirs) { const f = r.famille || 'aucune'; (fam.get(f) || fam.set(f, []).get(f)!).push(r) }
  const cats = new Map<string, any[]>()
  for (const r of d.robinets) { (cats.get(r.categorie) || cats.set(r.categorie, []).get(r.categorie)!).push(r) }
  const match = (s: string) => !filtre || s.toLowerCase().includes(filtre.toLowerCase())
  // slug registre du tank sélectionné : on n'a pas le mapping nom→slug côté page ; l'allumage
  // tank→robinets se fait par les slugs du registre (sheet), le tank data_sources s'allume seul.
  const tankSel = sel?.type === 'tank' ? d.reservoirs.find((r: any) => String(r.id) === sel.id) : null
  const tapSel = sel?.type === 'tap' ? d.robinets.find((r: any) => r.id === sel.id) : null

  const eauTank = (r: any) =>
    r.veille?.statut === 'nouvelle_version' ? 'nouvelle'
      : r.mode === 'depot_manuel' ? 'manuel'
        : r.mode === 'en_direct' ? 'direct'
          : r.mode === 'absente' ? 'vide' : ''
  const chkTank = (r: any) => {
    if (r.a_verifier) return <span className="chk warn">à vérifier (cadence dépassée)</span>
    const v = r.veille
    if (!v) return <span className="chk warn">jamais vérifié</span>
    if (v.methode === 'rappel') return <span className="chk">rappel {v.rappel_jours ?? '—'} j</span>
    if (!v.statut) return <span className="chk warn">sonde jamais passée</span>
    const quand = v.passage ? new Date(v.passage).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' }) : ''
    if (v.statut === 'injoignable') return <span className="chk bad">sonde {quand}, injoignable</span>
    if (v.statut === 'nouvelle_version') return <span className="chk warn">sonde {quand}, nouvelle version</span>
    return <span className="chk ok">sonde {quand}</span>
  }

  return (
    <div className="cx">
      <style>{CSS}</style>

      {/* ── bandeau « Tout coule, sauf : » ── */}
      <div className="status">
        <h1>{cpt.fuites_ouvertes === 0 && cpt.eau_ancienne_ouverte === 0 ? 'Tout coule.' : 'Tout coule, sauf :'}</h1>
        {cpt.fuites_ouvertes > 0 && <button className="pill rouge"><i />{cpt.fuites_ouvertes} fuite{cpt.fuites_ouvertes > 1 ? 's' : ''}</button>}
        {/* lot 5.3 — les écarts de type classe et géométrie comptent comme les autres */}
        {(cpt.fuites_classe ?? 0) > 0 && <button className="pill rouge"><i />{cpt.fuites_classe} écart{cpt.fuites_classe > 1 ? 's' : ''} de classe</button>}
        {(cpt.fuites_geometrie ?? 0) > 0 && <button className="pill rouge"><i />{cpt.fuites_geometrie} écart{cpt.fuites_geometrie > 1 ? 's' : ''} de géométrie</button>}
        {cpt.eau_ancienne_ouverte > 0 && <button className="pill ambre"><i />{cpt.eau_ancienne_ouverte} eau ancienne</button>}
        {cpt.jamais_verifies > 0 && <button className="pill gris"><i />{cpt.jamais_verifies} jamais vérifiés</button>}
        {cpt.a_verifier > 0 && <button className="pill ambre"><i />{cpt.a_verifier} à vérifier</button>}
        <span className="pill mint"><i />{cpt.vannes} vannes · {cpt.surveilles} sondes</span>
        <span className="muted" style={{ marginLeft: 'auto', fontSize: 11.5 }}>
          {d.dernier_controle
            ? <>dernier contrôle {new Date(d.dernier_controle.ts).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })} · {Number(d.dernier_controle.duree_s).toFixed(1)} s</>
            : 'jamais contrôlé'}
        </span>
        <button className="btn ghost" onClick={() => verifier.mutate()} disabled={verifier.isPending}>
          {verifier.isPending ? 'Vérification…' : 'Vérifier que tout coule'}
        </button>
        <button className="btn mauve" disabled
          title="Agents prêts (labuse agent source) — bouton câblé au premier crédit API.">Envoyer les agents</button>
        {/* CIRCUIT-1 lot 7.2 — l'interrupteur du MODE TRAÇAGE (admin) : chaque nombre étiqueté
            porte son chiffre_id sur les fiches ; éteint : rendu strictement identique. */}
        <button className={tracage ? 'btn' : 'btn ghost'} onClick={() => setTracage(!tracage)}
          style={tracage ? { borderColor: '#facc15', color: '#facc15' } : undefined}>
          {tracage ? 'Traçage : allumé' : 'Traçage'}
        </button>
      </div>

      <div className="legend">
        <span><i /> ça coule par le moteur</span><span><i className="grey" /> tuyau au repos</span>
        <span><i className="rouge" /> fuite mesurée</span>
        <span>⟳ se remplit seul (cron)</span>
        <input placeholder="Chercher un réservoir, un robinet, un chiffre…" value={filtre}
          onChange={e => setFiltre(e.target.value)} />
      </div>

      {/* ── les trois colonnes ── */}
      <div className="circuit" ref={gridRef}>
        <svg>{pipes.map((p, i) => <path key={i} d={p.d} className={p.cls} />)}</svg>

        <div className="col">
          {[...fam.entries()].map(([f, tanks]) => (
            <div key={f}>
              <h3 onClick={() => setFermes(x => ({ ...x, [f]: !x[f] }))}>
                {f} <span className="n">{tanks.length}</span><span className="tog">{fermes[f] ? '▸' : '▾'}</span>
              </h3>
              {!fermes[f] && tanks.filter((t: any) => match(t.nom + ' ' + (t.producteur || ''))).map((t: any) => (
                <button key={t.id} data-side="tank"
                  className={`row cl ${sel?.type === 'tank' && sel.id === String(t.id) ? 'sel' : ''} ${sel && !(sel.type === 'tank' && sel.id === String(t.id)) ? 'dim' : ''}`}
                  onClick={() => setSel(s => s?.type === 'tank' && s.id === String(t.id) ? null : { type: 'tank', id: String(t.id) })}>
                  <span className={`water ${eauTank(t)}`} />
                  <span className="nm">{t.nom}</span>
                  {t.mode === 'cron_mensuel' && <span className="clock" title="se remplit seul (cron)">⟳</span>}
                  {chkTank(t)}
                </button>
              ))}
            </div>
          ))}
        </div>

        {/* ── LA POMPE (collante) ── */}
        <div className="col pump-col">
          <div className="pump">
            <div className="t">La pompe</div>
            <div className="d">cascade · scoring · résiduel · division · tuiles — un manifeste, un geste</div>
            <div className="rel">
              <span className="run servi">{d.run_servi}</span>
              {candidat && <span className="run cand">{candidat}</span>}
            </div>
            <div className={`st ${d.residuel?.changees ? 'ambre' : 'mint'}`}>
              {d.residuel?.changees
                ? <>résiduel : entrées plus récentes ({d.residuel.detail}) — candidat requis avant bascule</>
                : <>résiduel : {d.residuel?.detail || 'reporté tel quel à la bascule'}</>}
            </div>
            <div className="rel" style={{ marginTop: 10 }}>
              <button className="btn" onClick={() => lancer.mutate()} disabled={lancer.isPending}>Faire tourner</button>
              <button className="btn ambre" disabled={!candidat}
                onClick={async () => { if (!candidat) return; setNote(await getAdminCircuitNoteVersion(candidat)); setNoteLue(candidat) }}>
                Note de version
              </button>
              <button className="btn ambre" disabled={!candidat || noteLue !== candidat}
                title={noteLue !== candidat ? 'Ouvrez la note de version d’abord.' : ''}
                onClick={() => candidat && basculer.mutate(candidat)}>
                Basculer
              </button>
              {/* Revenir = SERVEUR (le précédent du manifeste, jamais l'état client — recette 5.7). */}
              <button className="btn ghost" onClick={() => revenir.mutate()}
                disabled={revenir.isPending || !d.manifeste?.precedent?.scoring_run}>Revenir</button>
              <button className="btn ghost" onClick={() => purger.mutate()} disabled={purger.isPending}>Purger les runs morts</button>
            </div>
            {note && (
              <div className="st">
                <b>Note de version — {note.candidat}</b>
                <div className="muted">réservoirs : {note.reservoirs?.length ?? 0} · chiffres recalculés : {note.chiffres_recalcules?.length ?? 0}</div>
                {note.ecart_classement?.ok === false && <div className="muted">écart : {note.ecart_classement.motif}</div>}
              </div>
            )}
            {purger.data && (
              <div className="st">
                <b>Purge (dry-run)</b> : {purger.data.purgeables?.length ? purger.data.purgeables.join(', ') : 'rien à purger'}
                <div className="muted">{purger.data.note}</div>
              </div>
            )}
            {(d.journal || []).length > 0 && (
              <div className="st">
                <b>Journal</b>
                {d.journal.slice(0, 5).map((jn: any, i: number) => (
                  <div key={i} className="muted" style={{ fontSize: 11 }}>
                    {new Date(jn.ts).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })} · {jn.geste} {jn.cible} ({jn.par || '—'}) — {jn.resultat}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="col">
          {[...cats.entries()].map(([cat, taps]) => (
            <div key={cat}>
              <h3 onClick={() => setFermes(x => ({ ...x, ['c:' + cat]: !x['c:' + cat] }))}>
                {cat} <span className="n">{taps.length}</span><span className="tog">{fermes['c:' + cat] ? '▸' : '▾'}</span>
              </h3>
              {!fermes['c:' + cat] && taps.filter((t: any) =>
                match(t.nom + ' ' + t.id + ' ' + (t.chiffres || []).join(' '))).map((t: any) => (
                  <button key={t.id} data-side="tap"
                    className={`row cl ${t.categorie === 'copilote' ? 'ia' : ''} ${t.parent ? 'child' : ''} ${sel?.type === 'tap' && sel.id === t.id ? 'sel' : ''} ${sel && !litSets.taps.has(t.id) && !(sel.type === 'tap' && sel.id === t.id) ? 'dim' : litSets.taps.has(t.id) ? 'lit' : ''}`}
                    onClick={() => setSel(s => s?.type === 'tap' && s.id === t.id ? null : { type: 'tap', id: t.id })}>
                    <span className={`drop ${(t.chiffres || []).length ? '' : 'vide'}`} />
                    <span className="nm">{t.nom}</span>
                    <span className="meta">{(t.chiffres || []).length || '—'}</span>
                  </button>
                ))}
            </div>
          ))}
        </div>
      </div>

      {/* ── la fiche du bas (trois colonnes) ── */}
      {(tankSel || tapSel) && (
        <div className="sheet">
          <div className="in">
            {tankSel && (<>
              <div>
                <h4>{tankSel.nom}</h4>
                <div className="muted">{tankSel.producteur} · {tankSel.famille}</div>
                <div className="dates">
                  <div>millésime servi</div><div>{tankSel.millesime || '—'}</div>
                  <div>ingéré le</div><div>{tankSel.ingere_le ? new Date(tankSel.ingere_le).toLocaleDateString('fr-FR') : '—'}</div>
                  <div>mode</div><div>{tankSel.mode}</div>
                  <div>cadence</div><div>{tankSel.cadence_jours ? `${tankSel.cadence_jours} j (${tankSel.cadence_statut})` : 'sans objet'}</div>
                </div>
              </div>
              <div>
                <div className="k">La vanne</div>
                {tankSel.vanne.type === 'injecter' && (
                  <button className="btn" onClick={() => injecter.mutate(tankSel.id)} disabled={injecter.isPending}>
                    Ouvrir la vanne (injecter)
                  </button>)}
                {tankSel.vanne.type === 'depot' && <span className="chip ambre">déposer un fichier — dépôt manuel</span>}
                {tankSel.vanne.type === 'aucune' && <span className="chip">{tankSel.vanne.motif}</span>}
                <div className="k">Surveillance</div>
                {chkTank(tankSel)}
              </div>
              <div>
                <div className="k">Agent</div>
                <button className="btn mauve" disabled title="Lot 6.">Envoyer un agent</button>
              </div>
            </>)}
            {tapSel && (<>
              <div>
                <h4>{tapSel.nom}</h4>
                <div className="muted">{tapSel.categorie}{tapSel.parent ? ` · ${tapSel.parent}` : ''}</div>
                <div className="k">Route</div>
                <code style={{ fontSize: 11 }}>{tapSel.route}</code>
              </div>
              <div>
                {/* CIRCUIT-2 lot 5.1 — la fiche du bas liste TOUTES les données du robinet, PAR TYPE,
                    avec leur tampon ; une couche montre sa table/tuilage et sa fabrication. */}
                <div className="k">Données servies ({(tapSel.chiffres || []).length})</div>
                {(() => {
                  const parType = new Map<string, string[]>()
                  for (const c of (tapSel.chiffres || []) as string[]) {
                    const t = d.chiffres[c]?.type || 'nombre'
                    parType.set(t, [...(parType.get(t) || []), c])
                  }
                  return [...parType.entries()].map(([t, ids]) => (
                    <div key={t} style={{ marginTop: 4 }}>
                      <span className="muted" style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.12em' }}>{t}</span>
                      <div>
                        {ids.map((c) => {
                          const ch = d.chiffres[c]
                          const tampon = [ch?.definition,
                            ch?.table ? `table : ${ch.table}` : null,
                            ch?.fabrication ? `fabrication : ${ch.fabrication}` : null,
                            ch?.domaine ? `domaine : ${ch.domaine.join(', ')}` : null,
                          ].filter(Boolean).join('\n')
                          return (
                            <span key={c} className="chip" title={tampon}>
                              {ch?.libelle || c}{ch?.portee === 'run' ? ' · run' : ''}
                              {ch?.type === 'couche' && ch?.fabrication ? ` · ${ch.fabrication}` : ''}
                            </span>)
                        })}
                      </div>
                    </div>
                  ))
                })()}
                {tapSel.hors_registre && <div className="muted" style={{ marginTop: 6 }}>hors registre : {tapSel.hors_registre}</div>}
              </div>
              <div>
                <div className="k">Réservoirs amont</div>
                {[...new Set([...(tapSel.chiffres || [])].flatMap((c: string) => [...(g.C2R[c] || [])]))].map(r => (
                  <span key={r} className="chip">{r}</span>))}
              </div>
            </>)}
          </div>
        </div>
      )}
    </div>
  )
}
