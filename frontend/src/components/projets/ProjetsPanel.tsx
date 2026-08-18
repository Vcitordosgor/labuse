// M114 — PAGE PROJETS refondue d'après DA-PROJETS-v1 (font foi). Fond noir, mint accent rare
// (action principale, progression, reste à trier), mono pour le statutaire. Un seul bouton plein.
// Trois corrections mesurées : (1) le parcours occupe l'écran seul (la liste ne s'empile plus
// dessous) ; (2) deux intensités de ligne (à trier / à jour) au lieu de cartes indistinguables ;
// (3) plus de chips qui répètent le titre — une ligne de contexte + la commune en mono suffisent.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type MouseEvent } from 'react'
import { fusionnerProjets, getProjets, patchProjet, type FicheProjet, type Projet } from '../../lib/api'
import { fmtEurCompact } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { Skeleton } from '../Loading'
import { ProjetKanban } from './ProjetKanban'
import { ParcoursProjet } from './ParcoursProjet'
import { Vignette } from './Vignette'

const MONO = 'ui-monospace, SFMono-Regular, Menlo, monospace'

/** Résumé lisible d'un périmètre de fiche (sans commune = toute l'île). */
function perimetreLabel(f: FicheProjet): string {
  const p = f.perimetre
  if (!p || p.mode === 'ile') return "toute l'île"
  if (p.mode === 'secteur') return `secteur ${p.secteur}`
  const cs = p.communes ?? []
  return cs.length === 1 ? cs[0] : `${cs.length} communes`
}

/** La ligne de contexte SOUS le titre — programme + budget, ou « Cadrage à compléter ». Plus de
 *  chips qui répètent le titre, plus de date de création qui prend la place de l'info utile. */
function ctxLine(p: Projet): string {
  const amp = p.fiche.ampleur ?? {}
  const prog = amp.logements ? `${amp.logements} logements`
    : amp.sdp_m2 ? `${amp.sdp_m2} m² de plancher` : null
  if (!prog) return 'Cadrage à compléter'
  const parts = [prog]
  if (p.fiche.budget_foncier_eur) parts.push(`budget ${fmtEurCompact(p.fiche.budget_foncier_eur)}`)
  return parts.join(' · ')
}

/** La commune en MONO à côté du titre — repère de lecture, pas un chip. */
function communeMono(p: Projet): string {
  const c = p.vignette?.commune
  if (c) return c.toUpperCase()
  const per = p.fiche.perimetre
  if (per?.mode === 'communes' && per.communes?.length === 1) return per.communes[0].toUpperCase()
  return perimetreLabel(p.fiche).toUpperCase()
}

/** Une LIGNE de projet, deux intensités : `à trier` (bande mint, vignette 64, barre, compteur mint)
 *  ou `à jour` (bande grise, vignette 52, mention discrète). Toute la ligne est cliquable ; le menu
 *  ⋯ (Renommer / Archiver) apparaît au survol et ne déclenche pas l'ouverture. */
function ProjetRow({ p }: { p: Projet }) {
  const qc = useQueryClient()
  const setOpenProjet = useApp((s) => s.setOpenProjet)
  const [editing, setEditing] = useState(false)
  const [nom, setNom] = useState(p.nom)
  const patch = useMutation({
    mutationFn: (body: { nom?: string; statut?: string }) => patchProjet(p.id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projets'] }),
  })
  const c = p.counts ?? { proposee: 0, retenue: 0, ecartee: 0, a_analyser: 0 }
  const todo = c.proposee > 0
  const total = c.proposee + c.retenue
  const pct = total > 0 ? Math.round((c.retenue / total) * 100) : 0
  const archived = p.statut === 'archive'
  const ouvrir = () => setOpenProjet({ id: p.id, nom: p.nom })
  const stop = (e: MouseEvent) => e.stopPropagation()

  return (
    <div data-projet-row data-intensite={todo ? 'todo' : 'ajour'} onClick={ouvrir}
      className="group" style={{ display: 'flex', background: '#0C1410', borderRadius: 10, overflow: 'hidden', marginBottom: 8, cursor: 'pointer' }}>
      <div style={{ width: 3, flexShrink: 0, background: todo ? '#4ADE80' : '#1A241E' }} />
      <div style={{ flexShrink: 0, padding: todo ? '16px 0 16px 16px' : '14px 0 14px 16px' }}>
        <Vignette v={p.vignette} size={todo ? 64 : 52} />
      </div>
      <div style={{ flex: 1, minWidth: 0, padding: todo ? '16px 18px' : '14px 18px', display: 'flex', alignItems: 'center', gap: 20 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: todo ? 5 : 4 }}>
            {editing ? (
              <input data-projet-nom-input autoFocus value={nom} onClick={stop}
                onChange={(e) => setNom(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && nom.trim()) { patch.mutate({ nom: nom.trim() }); setEditing(false) }
                  if (e.key === 'Escape') { setNom(p.nom); setEditing(false) }
                }}
                onBlur={() => { if (nom.trim() && nom !== p.nom) patch.mutate({ nom: nom.trim() }); setEditing(false) }}
                style={{ minWidth: 0, flex: 1, borderRadius: 6, border: '.5px solid #4ADE80', background: '#060A08', padding: '4px 8px', fontSize: todo ? 17 : 16, color: '#ECF5EF', outline: 'none' }} />
            ) : (
              <span data-projet-titre style={{ fontSize: todo ? 17 : 16, color: todo ? '#ECF5EF' : '#C9DCD1', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{p.nom}</span>
            )}
            <span data-projet-commune style={{ fontFamily: MONO, fontSize: 11, color: todo ? '#5F7267' : '#4A5C52', letterSpacing: '.06em', flexShrink: 0 }}>{communeMono(p)}</span>
          </div>
          <div style={{ fontSize: 12, color: todo ? '#A8BDB0' : '#8FA69A', marginBottom: todo ? 11 : 0 }}>{ctxLine(p)}</div>
          {todo && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ width: 140, height: 3, background: '#12291D', borderRadius: 2, overflow: 'hidden' }}>
                {c.retenue > 0 && <div style={{ width: `${pct}%`, height: '100%', background: '#4ADE80', borderRadius: 2 }} />}
              </div>
              <span data-projet-barre style={{ fontFamily: MONO, fontSize: 11, color: '#8FA69A' }}>
                {c.retenue > 0 ? `${c.retenue} / ${total} RETENUES` : 'AUCUNE RETENUE'}</span>
            </div>
          )}
        </div>
        <div style={{ textAlign: 'right', whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: 14 }}>
          {todo ? (
            <div data-projet-atrier>
              <div style={{ fontSize: 28, color: '#4ADE80', fontWeight: 500, lineHeight: 1 }}>{c.proposee}</div>
              <div style={{ fontFamily: MONO, fontSize: 10, color: '#8FA69A', marginTop: 4, letterSpacing: '.06em' }}>À TRIER</div>
            </div>
          ) : (
            <span data-projet-rien style={{ fontFamily: MONO, fontSize: 11, color: '#4A5C52', letterSpacing: '.06em' }}>RIEN À TRIER</span>
          )}
          <details data-projet-menu className="relative shrink-0 opacity-0 transition-opacity duration-quick group-hover:opacity-100" onClick={stop}>
            <summary className="cursor-pointer list-none px-1 text-txt-ghost transition-colors duration-quick hover:text-txt" title="Plus d’actions">⋯</summary>
            <div className="absolute right-0 z-20 mt-1 flex flex-col gap-0.5 rounded-lg border border-line-3 bg-bg-3 p-1 shadow-flottante" style={{ minWidth: 128 }}>
              <button data-projet-editer onClick={(e) => { stop(e); setEditing(true) }}
                className="rounded px-2 py-1 text-left text-[12px] text-txt transition-colors duration-quick hover:bg-bg-2">Renommer</button>
              <button data-projet-archiver onClick={(e) => { stop(e); patch.mutate({ statut: archived ? 'actif' : 'archive' }) }}
                className="rounded px-2 py-1 text-left text-[12px] text-txt transition-colors duration-quick hover:bg-bg-2">{archived ? 'Réactiver' : 'Archiver'}</button>
            </div>
          </details>
        </div>
      </div>
    </div>
  )
}

/** M2 — DÉDUP : bandeau pour un groupe de doublons (même nom) + FUSION (statut le plus avancé gagne,
 *  sources archivées jamais supprimées). Apparaît seulement quand il y a des doublons. */
function DedupBanner({ groupe }: { groupe: Projet[] }) {
  const qc = useQueryClient()
  const [res, setRes] = useState<string | null>(null)
  const fusion = useMutation({
    mutationFn: () => fusionnerProjets(groupe.map((p) => p.id)),
    onSuccess: (r) => {
      const c = r.conflits.length
      setRes(`Fusionnés dans le projet nº${r.cible} · ${r.n_parcelles} parcelle(s)`
        + (c ? ` · ${c} conflit(s) de statut signalé(s) (statut le plus avancé retenu)` : ' · aucun conflit'))
      qc.invalidateQueries({ queryKey: ['projets'] })
    },
  })
  return (
    <div data-dedup-banner className="mb-2 rounded-xl bg-violet/[0.07] p-4 shadow-elev-1 ring-1 ring-violet/25">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <b className="text-txt-hi">{groupe.length} doublons</b>
          <span className="ml-2 text-txt-mut">« {groupe[0].nom} » — même nom / cadrage</span>
        </div>
        {!res && (
          <button data-dedup-fusionner onClick={() => fusion.mutate()} disabled={fusion.isPending}
            className="min-h-7 shrink-0 rounded-lg border border-violet px-3 py-1.5 text-[11px] font-semibold text-violet transition-colors duration-quick hover:bg-violet/10 disabled:opacity-50">
            {fusion.isPending ? 'Fusion…' : `Fusionner les ${groupe.length} →`}</button>
        )}
      </div>
      {res && <p data-dedup-res className="mt-2 text-[11px] text-mint">{res}</p>}
    </div>
  )
}

function groupesDoublons(actifs: Projet[]): Projet[][] {
  const par: Record<string, Projet[]> = {}
  for (const p of actifs) (par[p.nom.trim().toLowerCase()] ??= []).push(p)
  return Object.values(par).filter((g) => g.length > 1)
}

/** Ordre par défaut : le TRAVAIL RESTANT d'abord. Les projets à trier (proposée > 0) remontent, du
 *  plus gros reste au plus petit ; les autres suivent par activité récente. Aucun intertitre. */
function parTravail(a: Projet, b: Projet): number {
  const pa = a.counts?.proposee ?? 0, pb = b.counts?.proposee ?? 0
  if ((pa > 0) !== (pb > 0)) return pa > 0 ? -1 : 1
  if (pa > 0 && pb > 0) return pb - pa
  const act = (p: Projet) => new Date(p.derniere_execution_at ?? p.updated_at ?? p.created_at ?? 0).getTime()
  return act(b) - act(a)
}

const btnPlein = { padding: '9px 18px', background: '#4ADE80', color: '#05140B', borderRadius: 8, fontSize: 14, fontWeight: 500, cursor: 'pointer', border: 0 } as const

/** Vue PROJETS — liste « Vos projets », ou (si un projet est ouvert) sa vue kanban, ou (si le
 *  parcours de création est ouvert) le parcours SEUL. */
export function ProjetsPanel() {
  const { ouvrirEntretien, openProjet, setOpenProjet } = useApp()
  const [showArchived, setShowArchived] = useState(false)
  const [formOuvert, setFormOuvert] = useState(false)
  const [toutMontre, setToutMontre] = useState(false)
  const qc = useQueryClient()
  const projetsQ = useQuery({ queryKey: ['projets'], queryFn: getProjets })

  if (openProjet) return <ProjetKanban pid={openProjet.id} nom={openProjet.nom} />

  // Phase 1 — le parcours occupe l'ÉCRAN SEUL : la liste n'apparaît pas dessous. Échap/croix ferment.
  if (formOuvert) {
    return (
      <div className="flex min-w-0 flex-1 flex-col overflow-y-auto" style={{ background: '#060A08' }}>
        <div className="mx-auto w-full max-w-[900px] px-4 py-10 sm:px-8">
          <ParcoursProjet plein
            onVoir={(pr) => { setFormOuvert(false); void qc.invalidateQueries({ queryKey: ['projets'] }); setOpenProjet(pr) }}
            onFermer={() => setFormOuvert(false)} />
        </div>
      </div>
    )
  }

  const all = projetsQ.data ?? []
  const actifs = all.filter((p) => p.statut === 'actif')
  const archives = all.filter((p) => p.statut === 'archive')
  const visibles = (showArchived ? archives : actifs).slice().sort(parTravail)
  const affichees = toutMontre ? visibles : visibles.slice(0, 4)
  const reste = visibles.length - affichees.length

  const tab = (on: boolean) => ({
    padding: '7px 16px', fontSize: 13, borderRadius: 6, cursor: 'pointer', border: 0,
    background: on ? '#4ADE80' : 'transparent', color: on ? '#05140B' : '#8FA69A', fontWeight: on ? 500 : 400,
  }) as const

  return (
    <div className="flex min-w-0 flex-1 flex-col overflow-y-auto" style={{ background: '#060A08' }}>
      <div className="mx-auto w-full max-w-[900px] px-4 py-10 sm:px-8">
        {/* 1 · EN-TÊTE — « Vos projets », un seul bouton plein, « Décrire au copilote » en lien discret. */}
        <div className="flex items-start justify-between gap-6" style={{ marginBottom: 28 }}>
          <div className="min-w-0">
            <h1 style={{ fontSize: 22, fontWeight: 500, color: '#ECF5EF', margin: '0 0 5px' }}>Vos projets</h1>
            <p style={{ fontSize: 13, color: '#6F8578', margin: 0 }}>Chaque projet garde votre cadrage et vos parcelles retenues.</p>
          </div>
          <div className="flex items-center gap-[18px]" style={{ whiteSpace: 'nowrap' }}>
            <button data-projet-decrire onClick={() => ouvrirEntretien()}
              style={{ fontSize: 13, color: '#8FA69A', cursor: 'pointer', background: 'none', border: 0 }}>Décrire au copilote</button>
            <button data-projet-nouveau onClick={() => { setFormOuvert(true) }} style={btnPlein}>Nouveau projet</button>
          </div>
        </div>

        {projetsQ.isLoading && (<><Skeleton className="mb-2 h-20 rounded-xl" /><Skeleton className="h-16 rounded-xl" /></>)}

        {!projetsQ.isLoading && all.length === 0 ? (
          /* 3 · ÉTAT VIDE — il doit inviter, pas constater. */
          <div data-projets-vide style={{ marginTop: 8, padding: 32, border: '.5px dashed #1E2A23', borderRadius: 12, textAlign: 'center' }}>
            <h3 style={{ fontSize: 15, color: '#8FA69A', fontWeight: 400, margin: '0 0 6px' }}>Aucun projet pour l'instant</h3>
            <p style={{ fontSize: 13, color: '#5F7267', margin: '0 0 16px' }}>Un projet garde votre cadrage et vos parcelles retenues.</p>
            <button data-projet-nouveau-vide onClick={() => setFormOuvert(true)} style={{ ...btnPlein, display: 'inline-block' }}>Créer votre premier projet</button>
          </div>
        ) : !projetsQ.isLoading && (
          <>
            {/* 2 · ONGLETS — deux seulement. */}
            <div style={{ display: 'inline-flex', gap: 4, background: '#0C1410', borderRadius: 9, padding: 4, marginBottom: 20 }}>
              <button data-tab-actifs onClick={() => { setShowArchived(false); setToutMontre(false) }} style={tab(!showArchived)}>Actifs {actifs.length}</button>
              <button data-tab-archives onClick={() => { setShowArchived(true); setToutMontre(false) }} style={tab(showArchived)}>Archivés {archives.length}</button>
            </div>

            {!showArchived && groupesDoublons(actifs).map((g) => <DedupBanner key={g[0].id} groupe={g} />)}

            <div data-projets-liste>
              {visibles.length === 0 && (
                <p style={{ fontSize: 13, color: '#5F7267', padding: '16px 0' }}>
                  {showArchived ? 'Aucun projet archivé.' : 'Aucun projet actif.'}
                </p>
              )}
              {affichees.map((p) => <ProjetRow key={p.id} p={p} />)}
            </div>

            {/* 7 · VOIR LES N AUTRES — ne pas dérouler 9 lignes d'un coup. */}
            {reste > 0 && (
              <div data-projets-plus onClick={() => setToutMontre(true)}
                style={{ textAlign: 'center', padding: '16px 0 4px', fontFamily: MONO, fontSize: 12, color: '#8FA69A', letterSpacing: '.06em', cursor: 'pointer' }}>
                VOIR LES {reste} AUTRES
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
