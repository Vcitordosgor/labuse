import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import {
  ajouterParcelle, chercherPlus, getCarteDecision, getParcoursEtat, proposerProjet, setStatutParcelle,
  type ParcoursEtat, type ParcoursItem, type StatutParcelle,
} from '../../lib/api'
import { useApp } from '../../store/useApp'
import { TierBadge } from '../outils/TierBadge'

const fmt = (n: number | null | undefined) => (n == null ? '—' : Math.round(Number(n)).toLocaleString('fr-FR'))

/** Parcours de sélection (Tinder) — la carte est en fond (pilotée par le store : moduleMap surligne
 *  les proposées, flyTo centre la courante), une carte de décision flotte par-dessus. Écarter est
 *  RÉVERSIBLE (pile écartées récupérable). Lot 3 (tri) + Lot 4 (sections) du parcours projet. */
export function ParcoursTinder() {
  const { parcours, setView, setModuleMap, setFlyTo, select, selectedIdu } = useApp()
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
      <div className="pointer-events-auto flex items-center gap-3 border-b border-line-2 bg-surface-1/95 px-4 py-2 backdrop-blur">
        <span className="font-display text-sm font-bold text-txt-hi">{parcours.nom}</span>
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <div className="h-1.5 min-w-[80px] flex-1 overflow-hidden rounded-full bg-surface-3">
            <div className="h-full bg-mint transition-all" style={{ width: total ? `${(decided / total) * 100}%` : '0%' }} />
          </div>
          <span data-parcours-progress className="shrink-0 font-mono text-[11px] text-txt-mut">
            {decided} / {total} triées · <span className="text-mint">{c?.retenue ?? 0} retenues</span>
          </span>
        </div>
        {/* action POSITIVE (chercher plus) : teinte menthe, la plus contrastée */}
        <button data-parcours-plus onClick={() => { setPlusOpen((o) => !o); setPlusMsg('') }}
          className={`rounded-md border px-3 py-1.5 text-[11.5px] font-medium transition-colors ${plusOpen ? 'border-mint bg-mint/20 text-mint' : 'border-mint/45 bg-mint/10 text-mint hover:bg-mint/20'}`}>
          ＋ Chercher plus
        </button>
        {/* consultation (retenues/écartées) : lisible, compteurs colorés pour le scan */}
        <button data-parcours-sections onClick={() => setSectionsOpen((o) => !o)}
          className={`rounded-md border px-3 py-1.5 text-[11.5px] font-medium transition-colors ${sectionsOpen ? 'border-mint bg-surface-3 text-txt-hi' : 'border-line-2 bg-surface-3 text-txt hover:border-mint/50 hover:text-txt-hi'}`}>
          Retenues (<span className="text-mint">{c?.retenue ?? 0}</span>) · Écartées (<span className="text-st-ecartee">{c?.ecartee ?? 0}</span>)
        </button>
        {/* sortie : la plus sobre, sans concurrencer les actions */}
        <button data-parcours-quitter onClick={() => setView('projets')}
          className="rounded-md border border-line-2 px-3 py-1.5 text-[11.5px] text-txt-mut hover:border-st-ecartee/50 hover:text-txt"
          title="Revenir aux projets (l'état est gardé)">✕ Quitter</button>
      </div>

      {plusOpen && (
        <div data-parcours-plus-panel className="pointer-events-auto absolute right-3 top-14 z-40 w-[300px] rounded-xl border border-line-2 bg-surface-2 p-3 shadow-2xl">
          <p className="font-mono text-[10px] tracking-widest text-txt-dim">CHERCHER PLUS DE PARCELLES</p>
          <button data-plus-elargir onClick={() => elargir.mutate()} disabled={elargir.isPending}
            className="mt-2 w-full rounded-md border border-line-2 py-1.5 text-[11px] text-txt hover:border-mint hover:text-txt-hi disabled:opacity-50">
            {elargir.isPending ? '…' : 'Élargir la recherche à toute l’île'}
          </button>
          <div className="mt-3 border-t border-line-2 pt-3">
            <p className="text-[10.5px] text-txt-dim">Ajouter une parcelle précise (IDU, ou cliquez-la sur la carte) :</p>
            <div className="mt-1.5 flex gap-1.5">
              <input data-plus-idu value={iduInput} onChange={(e) => setIduInput(e.target.value.trim())}
                placeholder="97415000CW0658"
                className="min-w-0 flex-1 rounded-md border border-line-2 bg-surface-3 px-2 py-1 font-mono text-[11px] text-txt focus:border-mint focus:outline-none" />
              <button data-plus-ajouter onClick={() => iduInput && ajouter.mutate(iduInput)} disabled={!iduInput || ajouter.isPending}
                className="shrink-0 rounded-md bg-mint px-2.5 py-1 text-[11px] font-medium text-[#06130C] hover:brightness-110 disabled:opacity-40">
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
        <div className="pointer-events-auto w-[360px] max-w-[42vw] shrink-0 overflow-y-auto p-4">
          {etatQ.isLoading && <p className="text-xs text-txt-dim">Chargement du parcours…</p>}
          {!etatQ.isLoading && !current && (
            <div data-parcours-fini className="rounded-2xl border border-line-2 bg-surface-2 p-5 text-center">
              <p className="font-display text-sm font-bold text-txt-hi">Tri terminé 🎉</p>
              <p className="mt-1 text-xs text-txt-mut">{c?.retenue ?? 0} retenues · {c?.ecartee ?? 0} écartées.</p>
              <button onClick={() => setSectionsOpen(true)} className="mt-3 text-xs font-medium text-mint hover:underline">
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
    <div data-decision-card className="rounded-2xl border border-line-2 bg-surface-2 p-4 shadow-2xl">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[11px] text-txt-dim">{item.idu.slice(8, 10)} {item.idu.slice(10)}</span>
        <TierBadge tier={item.tier} etage0={null} statut={null} />
      </div>
      <p className="mt-1 font-display text-sm font-bold text-txt-hi">{d?.adresse ?? item.commune}</p>
      <p className="text-[11px] text-txt-mut">{d?.commune ?? item.commune}{d?.surface_m2 ? ` · ${fmt(d.surface_m2)} m²` : ''}</p>

      <div className="mt-3 flex gap-2">
        {[['Qualité', d?.q_score], ['Accès', d?.a_score], ['Complétude', d?.completeness]].map(([lab, val]) => (
          <div key={lab as string} className="flex-1 rounded-lg bg-surface-3 px-2 py-1.5 text-center">
            <div className="font-display text-base font-bold text-mint">{val == null ? '—' : fmt(val as number)}</div>
            <div className="font-mono text-[9px] text-txt-dim">{lab}</div>
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
            <div key={`a${i}`} className="flex gap-1.5 text-[11px]"><span className="text-[#E8B44C]">⚠</span>
              <span className="text-txt"><b className="text-txt-hi">{a.titre}</b> — {a.detail}</span></div>
          ))}
        </div>
      )}
      {carteQ.isLoading && <p className="mt-3 text-[11px] text-txt-dim">Points clés…</p>}

      <button data-decision-fiche onClick={onFiche} className="mt-3 text-[11px] font-medium text-mint hover:underline">
        Voir la fiche complète →
      </button>

      <div className="mt-4 flex gap-2">
        <button data-decision-ecarter onClick={() => onDecide('ecartee')}
          className="flex-1 rounded-xl border border-[#E8695A]/50 py-2.5 text-sm font-medium text-[#E8695A] hover:bg-[#E8695A]/10">
          ✕ Écarter
        </button>
        <button data-decision-retenir onClick={() => onDecide('retenue')}
          className="flex-1 rounded-xl bg-mint py-2.5 text-sm font-bold text-[#06130C] hover:brightness-110">
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
    <div className="flex items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-2">
      <div className="min-w-0 flex-1">
        <div className="font-mono text-[11px] text-txt-hi">{p.idu.slice(8, 10)} {p.idu.slice(10)}
          <span className="ml-1.5 font-sans text-[10px] text-txt-dim">{p.commune}</span></div>
        <div className="text-[10px] text-txt-mut">qualité {fmt(p.q_score)}/100 · {p.tier ?? '—'}</div>
      </div>
      <button onClick={() => onFiche(p.idu)} className="text-[10px] text-txt-mut hover:text-txt">fiche</button>
      {actions}
    </div>
  )
  return (
    <div className="pointer-events-auto absolute inset-0 z-40 flex justify-end bg-black/40" onClick={onClose}>
      <div className="flex w-[420px] max-w-[92vw] flex-col bg-surface-1 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-line-2 px-4 py-3">
          <span className="font-display text-sm font-bold text-txt-hi">Retenues & écartées</span>
          <button data-sections-close onClick={onClose} className="text-txt-mut hover:text-txt">✕</button>
        </div>
        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
          <div>
            <p className="mb-1.5 font-mono text-[10px] tracking-widest text-mint">RETENUES ({etat.retenues.length})</p>
            {etat.retenues.length === 0 && <p className="text-[11px] text-txt-dim">Aucune retenue pour l'instant.</p>}
            <div data-section-retenues className="space-y-1.5">
              {etat.retenues.map((p) => <Row key={p.idu} p={p} actions={
                <button onClick={() => onStatut(p.idu, 'proposee')} className="text-[10px] text-txt-mut hover:text-txt" title="Remettre à trier">retirer</button>
              } />)}
            </div>
          </div>
          <div>
            <p className="mb-1.5 font-mono text-[10px] tracking-widest text-[#E8695A]">ÉCARTÉES ({etat.ecartees.length}) — récupérables</p>
            {etat.ecartees.length === 0 && <p className="text-[11px] text-txt-dim">Aucune écartée.</p>}
            <div data-section-ecartees className="space-y-1.5">
              {etat.ecartees.map((p) => <Row key={p.idu} p={p} actions={
                <button data-recuperer onClick={() => onStatut(p.idu, 'proposee')}
                  className="rounded border border-mint/50 px-1.5 py-0.5 text-[10px] text-mint hover:bg-mint/10" title="Récupérer (repasse à trier)">↩ récupérer</button>
              } />)}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
