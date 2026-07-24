import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { fusionnerProjets, getProjets, patchProjet, type FicheProjet, type Projet } from '../../lib/api'
import { fmtDate, fmtEurCompact } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { Skeleton } from '../Loading'
import { EmptyState } from '../States'
import { ProjetKanban } from './ProjetKanban'

const TYPE_LABEL: Record<string, string> = {
  logements: 'Logements', etudiant: 'Logement étudiant', bureaux: 'Bureaux', autre: 'Projet',
}
const CONTRAINTE_LABEL: Record<string, string> = {
  eviter_ppr: 'hors PPR', eviter_pollution: 'sol sain', eviter_abf: 'hors ABF', eviter_icpe: 'hors ICPE',
}

/** Résumé lisible d'un périmètre de fiche (sans commune = toute l'île). */
function perimetreLabel(f: FicheProjet): string {
  const p = f.perimetre
  if (!p || p.mode === 'ile') return "toute l'île"
  if (p.mode === 'secteur') return `secteur ${p.secteur}`
  const cs = p.communes ?? []
  return cs.length === 1 ? cs[0] : `${cs.length} communes`
}

/** L'en-tête de cadrage (programme + ampleur) — la ligne qui pèse — puis le reste
 *  (périmètre · contraintes · budget) réuni en une ligne calme. */
function ficheLignes(f: FicheProjet): { titre: string | null; reste: string } {
  let titre: string | null = null
  if (f.type_programme) {
    const amp = f.ampleur ?? {}
    const n = amp.logements ? ` · ${amp.logements} logements` : amp.sdp_m2 ? ` · ${amp.sdp_m2} m² SDP` : ''
    titre = `${TYPE_LABEL[f.type_programme] ?? 'Projet'}${n}`
  }
  const reste: string[] = [perimetreLabel(f)]
  if (f.contraintes?.length) reste.push(f.contraintes.map((c) => CONTRAINTE_LABEL[c] ?? c).join(' · '))
  if (f.budget_foncier_eur) reste.push(`budget ${fmtEurCompact(f.budget_foncier_eur)}`)
  return { titre, reste: reste.join(' · ') }
}

/** Fiche projet (PJ8) — l'objet persistant : nom, critères, mini-compteurs de tri (depuis
 *  projet_parcelles), dernière activité, actions. UN bouton principal : « Ouvrir » → la vue kanban. */
function ProjetCard({ p }: { p: Projet }) {
  const qc = useQueryClient()
  const setOpenProjet = useApp((s) => s.setOpenProjet)
  const [editing, setEditing] = useState(false)
  const [nom, setNom] = useState(p.nom)

  const patch = useMutation({
    mutationFn: (body: { nom?: string; statut?: string }) => patchProjet(p.id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projets'] }),
  })

  const archived = p.statut === 'archive'
  const c = p.counts ?? { proposee: 0, retenue: 0, ecartee: 0, a_analyser: 0 }
  const fiche = ficheLignes(p.fiche)
  return (
    <div data-projet-card className={`card-elev p-4 ${archived ? 'opacity-60' : ''}`}>
      <div className="flex items-start justify-between gap-3">
        {editing ? (
          <input
            data-projet-nom-input autoFocus value={nom}
            onChange={(e) => setNom(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && nom.trim()) { patch.mutate({ nom: nom.trim() }); setEditing(false) }
              if (e.key === 'Escape') { setNom(p.nom); setEditing(false) }
            }}
            onBlur={() => { if (nom.trim() && nom !== p.nom) patch.mutate({ nom: nom.trim() }); setEditing(false) }}
            className="min-w-0 flex-1 rounded-md border border-mint/40 bg-surface-3 px-2 py-1 text-sm text-txt-hi outline-none focus:border-mint"
          />
        ) : (
          <button data-projet-nom onClick={() => setOpenProjet({ id: p.id, nom: p.nom })}
            className="min-w-0 flex-1 truncate text-left font-display text-sm font-bold text-txt-hi hover:text-mint" title={p.nom}>
            {p.nom}
          </button>
        )}
        {archived && <span className="shrink-0 rounded-full border border-line-2 px-2 py-0.5 text-[11px] text-txt-dim">archivé</span>}
      </div>

      <div className="mt-2 space-y-1 text-[11px]">
        {fiche.titre && <p className="text-txt">{fiche.titre}</p>}
        <p className="text-txt-mut">{fiche.reste}</p>
      </div>
      {p.fiche.criteres_libres && (
        <p className="mt-2 border-l-2 border-line-2 pl-2 text-[11px] italic text-txt-dim">« {p.fiche.criteres_libres} »</p>
      )}

      {/* mini-compteurs de tri (source unique : projet_parcelles) — la couleur est un
          signal : elle ne s'allume que si le compte existe. */}
      <div data-projet-compteurs className="tnum mt-3 flex items-center gap-3 text-[11px]">
        <span className="text-txt-mut"><b className={c.proposee ? 'text-txt-hi' : 'text-txt-dim'}>{c.proposee}</b> à trier</span>
        <span className={c.retenue ? 'text-mint' : 'text-txt-dim'}><b>{c.retenue}</b> retenue{c.retenue > 1 ? 's' : ''}</span>
        <span className={c.ecartee ? 'text-st-ecartee' : 'text-txt-dim'}><b>{c.ecartee}</b> écartée{c.ecartee > 1 ? 's' : ''}</span>
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <span className="whitespace-nowrap font-mono text-[11px] text-txt-dim">
          {p.derniere_execution_at ? `rejoué ${fmtDate(p.derniere_execution_at)}` : `créé ${fmtDate(p.created_at)}`}
        </span>
        <div className="flex items-center gap-1.5">
          <button data-projet-editer onClick={() => setEditing(true)}
            className="min-h-7 rounded-md px-2 py-1 text-[11px] text-txt-mut transition-colors duration-quick hover:text-txt-hi"
            title="Renommer">Renommer</button>
          <button data-projet-archiver onClick={() => patch.mutate({ statut: archived ? 'actif' : 'archive' })}
            className="min-h-7 rounded-md px-2 py-1 text-[11px] text-txt-mut transition-colors duration-quick hover:text-txt-hi"
            title={archived ? 'Réactiver le projet' : 'Archiver le projet'}>{archived ? 'Réactiver' : 'Archiver'}</button>
          <button data-projet-ouvrir onClick={() => setOpenProjet({ id: p.id, nom: p.nom })}
            className="min-h-7 rounded-md border border-mint/50 px-3 py-1 text-[11px] font-semibold text-mint transition-colors duration-quick hover:bg-mint/10"
            title="Ouvrir le projet (kanban : à trier / retenues / écartées)">Ouvrir</button>
        </div>
      </div>
    </div>
  )
}

/** M2 — DÉDUP : bandeau pour un groupe de doublons (même nom) + action de FUSION. La fusion réunit
 *  parcelles + statuts (statut le plus avancé gagne), signale les conflits, ARCHIVE les sources
 *  (jamais de suppression silencieuse). Le résultat affiche les conflits. */
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
    <div data-dedup-banner className="rounded-xl bg-violet/[0.07] p-4 shadow-elev-1 ring-1 ring-violet/25">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <b className="text-txt-hi">{groupe.length} doublons</b>
          <span className="ml-2 text-txt-mut">« {groupe[0].nom} » — même nom / cadrage</span>
          <div className="mt-1 text-[11px] text-txt-dim">projets {groupe.map((p) => `nº${p.id}`).join(' · ')}</div>
        </div>
        {!res && (
          <button data-dedup-fusionner onClick={() => fusion.mutate()} disabled={fusion.isPending}
            className="min-h-7 shrink-0 rounded-lg border border-violet px-3 py-1.5 text-[11px] font-semibold text-violet transition-colors duration-quick hover:bg-violet/10 disabled:opacity-50"
            title="Réunir les parcelles et statuts en un seul projet (sources archivées, jamais supprimées)">
            {fusion.isPending ? 'Fusion…' : `Fusionner les ${groupe.length} →`}</button>
        )}
      </div>
      {res && <p data-dedup-res className="mt-2 text-[11px] text-mint">{res}</p>}
    </div>
  )
}

/** Détecte les groupes de doublons parmi les projets actifs (même nom normalisé, ≥ 2). */
function groupesDoublons(actifs: Projet[]): Projet[][] {
  const par: Record<string, Projet[]> = {}
  for (const p of actifs) (par[p.nom.trim().toLowerCase()] ??= []).push(p)
  return Object.values(par).filter((g) => g.length > 1)
}

/** Vue PROJETS (copilote-projet) — liste « Mes projets » OU, si un projet est ouvert, sa vue
 *  kanban unifiée (À trier / Retenues / Écartées). « Ouvrir » = la vue kanban ; le tri vit dedans. */
export function ProjetsPanel() {
  const { ouvrirEntretien, openProjet } = useApp()
  const [showArchived, setShowArchived] = useState(false)
  const projetsQ = useQuery({ queryKey: ['projets'], queryFn: getProjets })

  // un projet ouvert → sa vue unifiée (le tri Tinder se lance DE LÀ et y revient)
  if (openProjet) return <ProjetKanban pid={openProjet.id} nom={openProjet.nom} />

  const all = projetsQ.data ?? []
  const actifs = all.filter((p) => p.statut === 'actif')
  const archives = all.filter((p) => p.statut === 'archive')
  const visibles = showArchived ? archives : actifs

  return (
    <div className="flex min-w-0 flex-1 flex-col overflow-y-auto bg-bg">
      <div className="mx-auto w-full max-w-3xl px-4 py-6 sm:px-8 sm:py-10">
        <div className="flex flex-wrap items-end justify-between gap-4 sm:flex-nowrap">
          <div className="min-w-0">
            <h1 className="font-display text-xl font-bold text-txt-hi">Mes projets</h1>
            <p className="mt-1 text-xs text-txt-mut">
              Chaque projet garde votre cadrage — ouvrez-le pour trier, retenir, écarter (rejouable, exportable).
            </p>
          </div>
          <button data-projet-nouveau onClick={() => ouvrirEntretien()}
            className="shrink-0 rounded-lg bg-mint px-4 py-2 text-xs font-medium text-mint-ink transition-[filter] duration-quick hover:brightness-110"
            title="Décrire un nouveau projet — ouvre directement « Votre projet »">+ Décrire un projet</button>
        </div>

        {archives.length > 0 && (
          <div className="mt-6 flex gap-1.5 text-[11px]">
            <button onClick={() => setShowArchived(false)}
              className={`min-h-7 rounded-full px-3 py-1 transition-colors duration-quick ${!showArchived ? 'bg-surface-3 text-txt-hi' : 'text-txt-mut hover:text-txt'}`}>Actifs ({actifs.length})</button>
            <button onClick={() => setShowArchived(true)}
              className={`min-h-7 rounded-full px-3 py-1 transition-colors duration-quick ${showArchived ? 'bg-surface-3 text-txt-hi' : 'text-txt-mut hover:text-txt'}`}>Archivés ({archives.length})</button>
          </div>
        )}

        {!showArchived && groupesDoublons(actifs).length > 0 && (
          <div className="mt-6 space-y-2">
            {groupesDoublons(actifs).map((g) => <DedupBanner key={g[0].id} groupe={g} />)}
          </div>
        )}

        <div data-projets-liste className="mt-6 space-y-3">
          {projetsQ.isLoading && (
            <>
              <Skeleton className="h-36 rounded-xl" />
              <Skeleton className="h-36 rounded-xl" />
            </>
          )}
          {!projetsQ.isLoading && visibles.length === 0 && (
            <div data-projets-vide className="card-elev">
              <EmptyState
                mint={!showArchived}
                title={showArchived ? 'Aucun projet archivé.' : 'Aucun projet encore.'}
                hint={showArchived ? undefined : 'Un projet garde votre cadrage (programme, périmètre, contraintes, budget) et vos décisions de tri.'}
                action={!showArchived && (
                  <button onClick={() => ouvrirEntretien()} className="text-xs font-medium text-mint hover:underline">
                    Décrivez votre opération au copilote →
                  </button>
                )}
              />
            </div>
          )}
          {visibles.map((p) => <ProjetCard key={p.id} p={p} />)}
        </div>
      </div>
    </div>
  )
}
