// M114 — PAGE PROJETS refondue d'après DA-PROJETS-v1 (font foi). Fond noir, mint accent rare
// (action principale, progression, reste à trier), mono pour le statutaire. Un seul bouton plein.
// Trois corrections mesurées : (1) le parcours occupe l'écran seul (la liste ne s'empile plus
// dessous) ; (2) deux intensités de ligne (à trier / à jour) au lieu de cartes indistinguables ;
// (3) plus de chips qui répètent le titre — une ligne de contexte + la commune en mono suffisent.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type MouseEvent } from 'react'
import { fusionnerProjets, getCourrierDemandes, getProjets, patchProjet, type Cadrage, type Projet } from '../../lib/api'
import { fmtEurCompact } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { Skeleton } from '../Loading'
import { ProjetKanban } from './ProjetKanban'
import { ParcoursProjet } from './ParcoursProjet'

const MONO = 'ui-monospace, SFMono-Regular, Menlo, monospace'

/** M120 — le périmètre est une FACETTE du cadrage (`communes`) ; vide = toute l'île. */
function perimetreLabel(c: Cadrage): string {
  const cs = c.communes ?? []
  if (!cs.length) return "toute l'île"
  return cs.length === 1 ? cs[0] : `${cs.length} communes`
}

/** La ligne de contexte SOUS le titre — périmètre + budget indicatif. M120 : le cadrage porte les
 *  facettes ; le budget est INFORMATIF (dit « indic. »). */
function ctxLine(p: Projet): string {
  const nFacettes = Object.keys(p.cadrage).filter((k) => k !== 'communes').length
  const parts = [perimetreLabel(p.cadrage)]
  if (nFacettes) parts.push(`${nFacettes} facette${nFacettes > 1 ? 's' : ''}`)
  if (p.identite.budget_eur) parts.push(`budget ${fmtEurCompact(p.identite.budget_eur)} indic.`)
  return parts.join(' · ')
}

/** La commune en MONO à côté du titre — repère de lecture, pas un chip. M120-B : depuis le cadrage. */
function communeMono(p: Projet): string {
  const cs = p.cadrage.communes ?? []
  if (cs.length === 1) return cs[0].toUpperCase()
  return perimetreLabel(p.cadrage).toUpperCase()
}

/** Une LIGNE de projet, deux intensités : `à trier` (bande mint, barre, compteur mint) ou `à jour`
 *  (bande grise, mention discrète). M120-B : plus de vignette d'emprise. Toute la ligne est cliquable ;
 *  le menu ⋯ (Renommer / Archiver) apparaît au survol et ne déclenche pas l'ouverture. */
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
  // OUTILS-5 (P5) — le VIVIER entier = à explorer + décidées (retenues + écartées + à analyser).
  const vivier = c.proposee + c.retenue + c.ecartee + (c.a_analyser ?? 0)
  const ouvrir = () => setOpenProjet({ id: p.id, nom: p.nom })
  const stop = (e: MouseEvent) => e.stopPropagation()

  return (
    <div data-projet-row data-intensite={todo ? 'todo' : 'ajour'} onClick={ouvrir}
      className="group" style={{ display: 'flex', background: '#0C1410', borderRadius: 10, overflow: 'hidden', marginBottom: 8, cursor: 'pointer' }}>
      {/* M120-B — bande d'état conservée ; la vignette d'emprise (M114) est retirée (rien à la place). */}
      <div style={{ width: 3, flexShrink: 0, background: todo ? '#4ADE80' : '#1A241E' }} />
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
          {/* OUTILS-5 (P5) — « vivier N classé · valeurs au JJ/MM · contexte » — jamais un stock global anxiogène. */}
          <div data-projet-vivier style={{ fontSize: 12, color: todo ? '#A8BDB0' : '#8FA69A', marginBottom: 11 }}>
            vivier {vivier.toLocaleString('fr-FR')} classé{p.proposee_at ? ` · valeurs au ${new Date(p.proposee_at).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })}` : ''}{ctxLine(p) ? ` · ${ctxLine(p)}` : ''}
          </div>
          {/* jauge de progression + détail : retenues / écartées / à explorer (classées). */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 200, height: 5, background: '#060A08', borderRadius: 3, overflow: 'hidden' }}>
              {vivier > 0 && <div style={{ width: `${Math.round(((c.retenue + c.ecartee) / vivier) * 100)}%`, height: '100%', background: '#4ADE80', borderRadius: 3 }} />}
            </div>
            <span data-projet-barre style={{ fontFamily: MONO, fontSize: 11, color: '#8FA69A' }}>
              {c.retenue} retenue{c.retenue > 1 ? 's' : ''} · {c.ecartee} écartée{c.ecartee > 1 ? 's' : ''} · {c.proposee.toLocaleString('fr-FR')} à explorer, classées</span>
          </div>
        </div>
        {/* OUTILS-5 (P5) — à droite, le compteur RETENUES (l'avancement RÉEL, pas la taille du stock) ;
            le menu ⋯ (Renommer/Archiver) DISPARAÎT de l'accueil (ces actions vivent dans le projet ouvert). */}
        <div data-projet-retenues style={{ textAlign: 'right', whiteSpace: 'nowrap' }} title="Parcelles retenues — l'avancement réel du projet">
          <div style={{ fontFamily: MONO, fontSize: 24, color: '#4ADE80', fontWeight: 700, lineHeight: 1 }}>{c.retenue}</div>
          <div style={{ fontFamily: MONO, fontSize: 10, color: '#8FA69A', marginTop: 4, letterSpacing: '.16em' }}>RETENUES</div>
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
  const { openProjet, setOpenProjet } = useApp()
  const [showArchived, setShowArchived] = useState(false)
  const [showCourriers, setShowCourriers] = useState(false)   // OUTILS-1 A4 — onglet « Mes courriers »
  const [formOuvert, setFormOuvert] = useState(false)
  const [toutMontre, setToutMontre] = useState(false)
  const qc = useQueryClient()
  const projetsQ = useQuery({ queryKey: ['projets'], queryFn: getProjets })
  // OUTILS-1 A4/B6 — le client retrouve ici ses demandes de courrier (n°, date, communes, volume),
  // SANS état interne d'exécution (qui reste à la Tour de contrôle admin). Vue minimale, lecture seule.
  const courriersQ = useQuery({ queryKey: ['courrier-demandes'], queryFn: getCourrierDemandes })
  const courriers = courriersQ.data?.demandes ?? []

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
          {/* M118 — « Décrire au copilote » RETIRÉ : la création de projet quitte le Copilote, elle se
              fait ici, par le parcours guidé. Un seul point d'entrée. */}
          <div className="flex items-center gap-[18px]" style={{ whiteSpace: 'nowrap' }}>
            <button data-projet-nouveau onClick={() => { setFormOuvert(true) }} style={btnPlein}>Nouveau projet</button>
          </div>
        </div>

        {projetsQ.isLoading && (<><Skeleton className="mb-2 h-20 rounded-xl" /><Skeleton className="h-16 rounded-xl" /></>)}

        {!projetsQ.isLoading && all.length === 0 && courriers.length === 0 ? (
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
              <button data-tab-actifs onClick={() => { setShowArchived(false); setShowCourriers(false); setToutMontre(false) }} style={tab(!showArchived && !showCourriers)}>Actifs {actifs.length}</button>
              <button data-tab-archives onClick={() => { setShowArchived(true); setShowCourriers(false); setToutMontre(false) }} style={tab(showArchived && !showCourriers)}>Archivés {archives.length}</button>
              <button data-tab-courriers onClick={() => { setShowCourriers(true); setToutMontre(false) }} style={tab(showCourriers)}>Mes courriers {courriers.length}</button>
            </div>

            {showCourriers ? (
              /* OUTILS-1 A4/B6 — MES COURRIERS : n°, date, communes, volume. Aucun état interne. */
              <div data-mes-courriers>
                {/* F5 (OUTILS-3) — accès à l'outil Courrier propriétaire (étape 1) depuis Projets. */}
                <button data-mes-courriers-nouveau
                  onClick={() => { const s = useApp.getState(); s.setView('cartes'); s.setModule('courriers') }}
                  style={{ ...btnPlein, display: 'inline-block', marginBottom: 16 }}>Nouveau courrier →</button>
                {courriers.length === 0 && (
                  <p style={{ fontSize: 13, color: '#5F7267', padding: '16px 0' }}>Aucune demande de courrier pour l'instant.</p>
                )}
                {courriers.map((d) => (
                  <div key={d.id} data-courrier-ligne={d.id}
                    style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 14,
                      padding: '11px 4px', borderBottom: '.5px solid #16211B' }}>
                    <span style={{ minWidth: 0, color: '#ECF5EF', fontSize: 13 }}>
                      <b style={{ fontFamily: MONO, fontSize: 12, color: '#8FA69A' }}>n° {d.id}</b>
                      {' — '}{d.n} courrier{d.n > 1 ? 's' : ''}{d.communes ? ` · ${d.communes}` : ''}
                    </span>
                    <span style={{ flexShrink: 0, fontFamily: MONO, fontSize: 11, color: '#5F7267' }}>{String(d.ts).slice(0, 10)}</span>
                  </div>
                ))}
                <p style={{ fontSize: 11.5, color: '#5F7267', marginTop: 12 }}>
                  LABUSE vous rappelle sous 24 h ouvrées avec le tarif — impression, mise sous pli, affranchissement et suivi compris.
                </p>
              </div>
            ) : (
              <>
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
          </>
        )}
      </div>
    </div>
  )
}
