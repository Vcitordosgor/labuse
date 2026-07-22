import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import {
  ajouterParcelle, chercherPlus, getCarteDecision, getParcoursEtat, proposerProjet, setStatutParcelle,
  type ParcoursEtat, type ParcoursItem, type StatutParcelle,
} from '../../lib/api'
import { fmtInt, fmtM2 } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'
import { Oiseau } from '../States'
import { TierBadge } from '../outils/TierBadge'

/** Parcours de sélection (Tinder) — la carte est en fond (pilotée par le store : moduleMap surligne
 *  les proposées, flyTo centre la courante), une carte de décision flotte par-dessus. Écarter est
 *  RÉVERSIBLE (pile écartées récupérable). Lot 3 (tri) + Lot 4 (sections) du parcours projet. */
export function ParcoursTinder() {
  const { parcours, setView, setOpenProjet, setModuleMap, setFlyTo, select, selectedIdu } = useApp()
  // retour du tri → on revient sur le KANBAN du projet (pas la liste) : une seule source de vérité,
  // les statuts qu'on vient de poser s'y reflètent immédiatement (query ['parcours', pid] partagée).
  const retourProjet = () => (parcours ? setOpenProjet({ id: parcours.id, nom: parcours.nom }) : setView('projets'))
  const qc = useQueryClient()
  const pid = parcours?.id ?? 0
  const proposed = useRef(false)
  const [sectionsOpen, setSectionsOpen] = useState(false)
  const [plusOpen, setPlusOpen] = useState(false)
  const [iduInput, setIduInput] = useState('')
  const [plusMsg, setPlusMsg] = useState('')
  // clic-carte : une parcelle cliquée sur la carte pré-remplit le champ IDU d'ajout manuel
  useEffect(() => { if (plusOpen && selectedIdu) setIduInput(selectedIdu) }, [plusOpen, selectedIdu])
  const refreshDeck = () => qc.invalidateQueries({ queryKey: ['parcours', pid] })
  const elargir = useMutation({
    // limit plus profond que la proposition initiale (24) → atteint de NOUVELLES parcelles au-delà du top
    mutationFn: () => chercherPlus(pid, { limit: 48, ile: true }),
    onSuccess: (r) => { setPlusMsg(r.n_added > 0 ? `+${r.n_added} parcelle(s) ajoutée(s) (élargi à l'île)` : 'aucune nouvelle parcelle (déjà toutes proposées)'); refreshDeck() },
  })
  const ajouter = useMutation({
    mutationFn: (idu: string) => ajouterParcelle(pid, idu),
    onSuccess: (r) => { setPlusMsg(r.already ? `${r.idu} est déjà dans le projet` : `${r.idu} ajoutée au tri`); setIduInput(''); refreshDeck() },
    onError: () => setPlusMsg('IDU inconnu — vérifiez la saisie'),
  })

  // À l'entrée : (re)proposer les parcelles du jour (idempotent, préserve les décisions) puis lire l'état.
  const etatQ = useQuery({ queryKey: ['parcours', pid], queryFn: () => getParcoursEtat(pid), enabled: pid > 0 })
  useEffect(() => {
    if (!pid || proposed.current) return
    proposed.current = true
    proposerProjet(pid).then(() => qc.invalidateQueries({ queryKey: ['parcours', pid] }))
  }, [pid, qc])

  const etat = etatQ.data
  const deck = etat?.proposees ?? []
  const current = deck[0] ?? null

  // surligne toutes les proposées sur la carte (contexte) + centre la courante
  useEffect(() => {
    if (!etat) return
    setModuleMap({ idus: etat.proposees.map((p) => p.idu), extra: null })
  }, [etat, setModuleMap])
  useEffect(() => {
    if (current?.center) setFlyTo({ center: current.center, zoom: 17 })
  }, [current?.idu, current?.center, setFlyTo])
  // sortie propre : on rend la carte au fond unique
  useEffect(() => () => { setModuleMap({ idus: [], extra: null }) }, [setModuleMap])

  const decide = useMutation({
    mutationFn: ({ idu, statut }: { idu: string; statut: StatutParcelle }) => setStatutParcelle(pid, idu, statut),
    // optimiste : on retire/replace localement pour un geste instantané, puis on resynchronise
    onMutate: async ({ idu, statut }) => {
      await qc.cancelQueries({ queryKey: ['parcours', pid] })
      const prev = qc.getQueryData<ParcoursEtat>(['parcours', pid])
      if (prev) qc.setQueryData<ParcoursEtat>(['parcours', pid], moveItem(prev, idu, statut))
      return { prev }
    },
    onError: (_e, _v, ctx) => { if (ctx?.prev) qc.setQueryData(['parcours', pid], ctx.prev) },
    // Phase 2 : retenir/retirer change AUSSI le CRM (auto-CRM) → resynchroniser le Kanban
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['parcours', pid] })
      qc.invalidateQueries({ queryKey: ['pipeline'] })
    },
  })

  if (!parcours) return null
  const c = etat?.counts
  const total = c ? c.proposee + c.retenue + c.ecartee + c.a_analyser : 0
  const decided = c ? c.retenue + c.ecartee + c.a_analyser : 0

  return (
    <div className="pointer-events-none absolute inset-0 z-30 flex flex-col">
      {/* barre haute : progression + sections + quitter */}
      <div className="pointer-events-auto flex flex-wrap items-center gap-x-3 gap-y-1.5 border-b border-line-2 bg-surface-1/95 px-4 py-2 backdrop-blur">
        <span className="font-display text-sm font-bold text-txt-hi">{parcours.nom}</span>
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <div className="h-1.5 min-w-[80px] flex-1 overflow-hidden rounded-full bg-surface-3">
            <div className="h-full bg-mint transition-[width] duration-soft ease-cockpit" style={{ width: total ? `${(decided / total) * 100}%` : '0%' }} />
          </div>
          <span data-parcours-progress className="tnum shrink-0 whitespace-nowrap font-mono text-[11px] text-txt-mut">
            {decided} / {total} triées · <span className="text-mint">{c?.retenue ?? 0} retenues</span>
          </span>
        </div>
        {/* action POSITIVE (chercher plus) : teinte menthe, la plus contrastée */}
        <button data-parcours-plus onClick={() => { setPlusOpen((o) => !o); setPlusMsg('') }}
          className={`min-h-7 rounded-md border px-3 py-1.5 text-[11.5px] font-medium transition-colors duration-quick ${plusOpen ? 'border-mint bg-mint/20 text-mint' : 'border-mint/45 bg-mint/10 text-mint hover:bg-mint/20'}`}>
          + Chercher plus
        </button>
        {/* consultation (retenues/écartées) : lisible, compteurs colorés pour le scan */}
        <button data-parcours-sections onClick={() => setSectionsOpen((o) => !o)}
          className={`min-h-7 rounded-md border px-3 py-1.5 text-[11.5px] font-medium transition-colors duration-quick ${sectionsOpen ? 'border-mint bg-surface-3 text-txt-hi' : 'border-line-2 bg-surface-3 text-txt hover:border-mint/50 hover:text-txt-hi'}`}>
          Retenues (<span className="text-mint">{c?.retenue ?? 0}</span>) · Écartées (<span className="text-st-ecartee">{c?.ecartee ?? 0}</span>)
        </button>
        {/* sortie : la plus sobre, sans concurrencer les actions */}
        <button data-parcours-quitter onClick={retourProjet}
          className="min-h-7 rounded-md border border-line-2 px-3 py-1.5 text-[11.5px] text-txt-mut transition-colors duration-quick hover:border-st-ecartee/50 hover:text-txt"
          title="Revenir au projet (l'état est gardé)">✕ Quitter</button>
      </div>

      {plusOpen && (
        <div data-parcours-plus-panel className="floating pointer-events-auto absolute right-3 top-14 z-40 w-[300px] p-3">
          <p className="label-caps">Chercher plus de parcelles</p>
          <button data-plus-elargir onClick={() => elargir.mutate()} disabled={elargir.isPending}
            className="mt-2 min-h-7 w-full rounded-md border border-line-2 py-1.5 text-[11px] text-txt transition-colors duration-quick hover:border-mint hover:text-txt-hi disabled:opacity-50">
            {elargir.isPending ? '…' : 'Élargir la recherche à toute l’île'}
          </button>
          <div className="mt-3 border-t border-line-2 pt-3">
            <p className="text-[10.5px] text-txt-dim">Ajouter une parcelle précise (IDU, ou cliquez-la sur la carte) :</p>
            <div className="mt-1.5 flex gap-1.5">
              <input data-plus-idu value={iduInput} onChange={(e) => setIduInput(e.target.value.trim())}
                placeholder="97415000CW0658"
                className="min-w-0 flex-1 rounded-md border border-line-2 bg-surface-3 px-2 py-1 font-mono text-[11px] text-txt focus:border-mint focus:outline-none" />
              <button data-plus-ajouter onClick={() => iduInput && ajouter.mutate(iduInput)} disabled={!iduInput || ajouter.isPending}
                className="min-h-7 shrink-0 rounded-md bg-mint px-2.5 py-1 text-[11px] font-medium text-mint-ink transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
                Ajouter
              </button>
            </div>
          </div>
          {plusMsg && <p data-plus-msg className="mt-2 text-[10.5px] text-mint">{plusMsg}</p>}
        </div>
      )}

      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-1" /> {/* la carte reste visible/agissable ici */}

        {/* carte de décision (droite) */}
        <div className="pointer-events-auto w-[360px] max-w-[85vw] shrink-0 overflow-y-auto p-4 sm:max-w-[42vw]">
          {etatQ.isLoading && <Loading label="Chargement du parcours…" />}
          {!etatQ.isLoading && !current && (
            <div data-parcours-fini className="floating p-5 text-center">
              <Oiseau className="mx-auto mb-2 h-5 w-auto" dim={false} />
              <p className="font-display text-sm font-bold text-txt-hi">Tri terminé</p>
              <p className="tnum mt-1 text-xs text-txt-mut">{c?.retenue ?? 0} retenues · {c?.ecartee ?? 0} écartées.</p>
              <button onClick={() => setSectionsOpen(true)} className="mt-3 min-h-7 text-xs font-medium text-mint hover:underline">
                Revoir les retenues et les écartées →
              </button>
            </div>
          )}
          {current && <DecisionCard pid={pid} item={current}
            onDecide={(statut) => decide.mutate({ idu: current.idu, statut })}
            onFiche={() => select(current.idu)} />}
        </div>
      </div>

      {sectionsOpen && etat && (
        <SectionsDrawer etat={etat} onClose={() => setSectionsOpen(false)}
          onFiche={(idu) => select(idu)}
          onStatut={(idu, statut) => decide.mutate({ idu, statut })} />
      )}
    </div>
  )
}

/** retire l'item de son groupe et le pousse dans le groupe cible — maj optimiste de l'état. */
function moveItem(etat: ParcoursEtat, idu: string, statut: StatutParcelle): ParcoursEtat {
  let moved: ParcoursItem | null = null
  const strip = (arr: ParcoursItem[]) => arr.filter((x) => {
    if (x.idu === idu) { moved = { ...x, statut }; return false }
    return true
  })
  const proposees = strip(etat.proposees)
  const retenues = strip(etat.retenues)
  const ecartees = strip(etat.ecartees)
  const a_analyser = strip(etat.a_analyser)
  if (moved) {
    if (statut === 'retenue') retenues.push(moved)
    else if (statut === 'ecartee') ecartees.push(moved)
    else if (statut === 'a_analyser') a_analyser.push(moved)
    else proposees.push(moved)
  }
  return {
    ...etat, proposees, retenues, ecartees, a_analyser,
    counts: { proposee: proposees.length, retenue: retenues.length, ecartee: ecartees.length, a_analyser: a_analyser.length },
  }
}

function DecisionCard({ pid, item, onDecide, onFiche }: {
  pid: number; item: ParcoursItem
  onDecide: (s: StatutParcelle) => void; onFiche: () => void
}) {
  const carteQ = useQuery({ queryKey: ['carte-decision', pid, item.idu], queryFn: () => getCarteDecision(pid, item.idu) })
  const d = carteQ.data
  return (
    <div data-decision-card className="floating p-4 shadow-elev-3">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[11px] text-txt-dim">{item.idu.slice(8, 10)} {item.idu.slice(10)}</span>
        <TierBadge tier={item.tier} etage0={null} statut={null} />
      </div>
      <p className="mt-1 font-display text-sm font-bold text-txt-hi">{d?.adresse ?? item.commune}</p>
      <p className="tnum text-[11px] text-txt-mut">{d?.commune ?? item.commune}{d?.surface_m2 ? ` · ${fmtM2(d.surface_m2)}` : ''}</p>

      <div className="mt-3 flex gap-2">
        {[['Qualité', d?.q_score], ['Accès', d?.a_score], ['Complétude', d?.completeness]].map(([lab, val]) => (
          <div key={lab as string} className="flex-1 rounded-lg bg-surface-3 px-2 py-1.5 text-center">
            <div className="num-key text-base">{val == null ? '—' : fmtInt(val as number)}</div>
            <div className="label-caps text-[9px]">{lab}</div>
          </div>
        ))}
      </div>

      {d && (d.forces.length > 0 || d.attentions.length > 0) && (
        <div className="mt-3 space-y-1">
          {d.forces.slice(0, 3).map((f, i) => (
            <div key={`f${i}`} className="flex gap-1.5 text-[11px]"><span className="text-mint">✓</span>
              <span className="text-txt"><b className="text-txt-hi">{f.titre}</b> — {f.detail}</span></div>
          ))}
          {d.attentions.slice(0, 3).map((a, i) => (
            <div key={`a${i}`} className="flex gap-1.5 text-[11px]"><span className="text-st-creuser">▲</span>
              <span className="text-txt"><b className="text-txt-hi">{a.titre}</b> — {a.detail}</span></div>
          ))}
        </div>
      )}
      {carteQ.isLoading && <Loading className="mt-3" label="Points clés…" />}

      <button data-decision-fiche onClick={onFiche} className="mt-3 min-h-7 text-[11px] font-medium text-mint hover:underline">
        Voir la fiche complète →
      </button>

      {/* R2 (PJ2) — LES TROIS décisions en boutons francs, chacune à la couleur de sa colonne
          d'arrivée du Kanban M2 (écartée st-ecartee · à analyser st-creuser · retenue mint). Retenir
          reste le plus fort (plein) ; la sortie (✕ Quitter, barre haute) ne leur ressemble pas.
          Pas de raccourcis clavier : il n'en existe pas — on n'en invente pas dans ce lot. */}
      <div className="mt-4 flex gap-2">
        <button data-decision-ecarter onClick={() => onDecide('ecartee')}
          className="flex-1 rounded-xl border border-st-ecartee/50 py-2.5 text-sm font-medium text-st-ecartee transition-colors duration-quick hover:bg-st-ecartee/10"
          title="Écarter — réversible (pile Écartées)">
          ✕ Écarter
        </button>
        <button data-decision-analyser onClick={() => onDecide('a_analyser')}
          className="flex-1 rounded-xl border border-st-creuser/50 py-2.5 text-sm font-medium text-st-creuser transition-colors duration-quick hover:bg-st-creuser/10"
          title="Mettre de côté pour analyse — remonte en tête du Kanban avec le badge « à analyser »">
          ? À analyser
        </button>
        <button data-decision-retenir onClick={() => onDecide('retenue')}
          className="flex-1 rounded-xl bg-mint py-2.5 text-sm font-bold text-mint-ink transition-[filter] duration-quick hover:brightness-110"
          title="Retenir — passe en colonne Retenues (et au CRM)">
          ✓ Retenir
        </button>
      </div>
      <p className="mt-1.5 text-center text-[10px] text-txt-dim">Écarter est réversible — récupérable dans la pile Écartées.</p>
    </div>
  )
}

function SectionsDrawer({ etat, onClose, onFiche, onStatut }: {
  etat: ParcoursEtat; onClose: () => void
  onFiche: (idu: string) => void; onStatut: (idu: string, s: StatutParcelle) => void
}) {
  const Row = ({ p, actions }: { p: ParcoursItem; actions: React.ReactNode }) => (
    <div className="flex items-center gap-2 rounded-lg bg-surface-3 px-3 py-2 shadow-elev-1">
      <div className="min-w-0 flex-1">
        <div className="font-mono text-[11px] text-txt-hi">{p.idu.slice(8, 10)} {p.idu.slice(10)}
          <span className="ml-1.5 font-sans text-[10px] text-txt-dim">{p.commune}</span></div>
        <div className="tnum text-[10px] text-txt-mut">qualité {fmtInt(p.q_score)}/100 · {p.tier ?? '—'}</div>
      </div>
      <button onClick={() => onFiche(p.idu)}
        className="min-h-7 text-[10px] text-txt-mut transition-colors duration-quick hover:text-txt">fiche</button>
      {actions}
    </div>
  )
  return (
    <div className="pointer-events-auto absolute inset-0 z-40 flex justify-end bg-black/40" onClick={onClose}>
      <div className="flex w-[420px] max-w-[92vw] flex-col bg-surface-1 shadow-elev-3" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-line-2 px-4 py-3">
          <span className="font-display text-sm font-bold text-txt-hi">Retenues & écartées</span>
          <button data-sections-close onClick={onClose} aria-label="Fermer"
            className="flex h-7 w-7 items-center justify-center rounded-md text-txt-mut transition-colors duration-quick hover:bg-surface-3 hover:text-txt">✕</button>
        </div>
        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
          <div>
            <p className="label-caps mb-1.5 text-mint">Retenues ({etat.retenues.length})</p>
            {etat.retenues.length === 0 && <p className="text-[11px] text-txt-dim">Aucune retenue pour l'instant.</p>}
            <div data-section-retenues className="space-y-1.5">
              {etat.retenues.map((p) => <Row key={p.idu} p={p} actions={
                <button onClick={() => onStatut(p.idu, 'proposee')}
                  className="min-h-7 text-[10px] text-txt-mut transition-colors duration-quick hover:text-txt" title="Remettre à trier">retirer</button>
              } />)}
            </div>
          </div>
          <div>
            <p className="label-caps mb-1.5 text-st-ecartee">Écartées ({etat.ecartees.length}) — récupérables</p>
            {etat.ecartees.length === 0 && <p className="text-[11px] text-txt-dim">Aucune écartée.</p>}
            <div data-section-ecartees className="space-y-1.5">
              {etat.ecartees.map((p) => <Row key={p.idu} p={p} actions={
                <button data-recuperer onClick={() => onStatut(p.idu, 'proposee')}
                  className="min-h-7 rounded border border-mint/50 px-1.5 py-0.5 text-[10px] text-mint transition-colors duration-quick hover:bg-mint/10" title="Récupérer (repasse à trier)">↩ récupérer</button>
              } />)}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
