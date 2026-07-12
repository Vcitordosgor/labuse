import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { getApercu, getProjets, patchProjet, rejouerProjet, type FicheProjet, type Projet } from '../../lib/api'
import { useApplySearch } from '../../lib/useApplySearch'
import { useApp } from '../../store/useApp'

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

function ficheLignes(f: FicheProjet): string[] {
  const out: string[] = []
  if (f.type_programme) {
    const amp = f.ampleur ?? {}
    const n = amp.logements ? ` · ${amp.logements} logements` : amp.sdp_m2 ? ` · ${amp.sdp_m2} m² SDP` : ''
    out.push(`${TYPE_LABEL[f.type_programme] ?? 'Projet'}${n}`)
  }
  out.push(perimetreLabel(f))
  if (f.contraintes?.length) out.push(f.contraintes.map((c) => CONTRAINTE_LABEL[c] ?? c).join(' · '))
  if (f.budget_foncier_eur) out.push(`budget ${(f.budget_foncier_eur / 1000).toLocaleString('fr-FR')} k€`)
  return out
}

function frDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: '2-digit' })
}

function ProjetCard({ p }: { p: Projet }) {
  const qc = useQueryClient()
  const apply = useApplySearch()
  const [editing, setEditing] = useState(false)
  const [nom, setNom] = useState(p.nom)

  const patch = useMutation({
    mutationFn: (body: { nom?: string; statut?: string }) => patchProjet(p.id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projets'] }),
  })
  const rejouer = useMutation({
    mutationFn: async () => {
      const d = await rejouerProjet(p.id)
      const ap = await getApercu(p.fiche)   // recette + pourquoi recalculés sur les données du JOUR
      return { d, ap }
    },
    onSuccess: async ({ d, ap }) => {
      qc.invalidateQueries({ queryKey: ['projets'] })
      // OUVRIR = REJOUER : filtres réappliqués + restitution enrichie (déjà enregistré → PDF direct).
      // apply() bascule DÉJÀ sur la vue Cartes (et, avec la nav exclusive B2, nettoie les panneaux) ;
      // on pose la restitution APRÈS — un setView ici la balaierait (B2 vide iaRestitution).
      await apply(d.projet.filtres, `parcelles pour « ${d.projet.nom} »`)
      useApp.getState().setIaRestitution({
        n: ap.n,
        phrase: ap.programme_defini
          ? 'parcelles portent la capacité du programme — voici les meilleures'
          : 'parcelles correspondent à votre projet — voici les meilleures',
        top: ap.top.map((t) => ({ idu: t.idu, commune: t.commune, q_score: t.q_score ?? 0, pourquoi: t.pourquoi })),
        projet: { nom: d.projet.nom, fiche: p.fiche as Record<string, unknown>, id: p.id },
      })
    },
  })

  const archived = p.statut === 'archive'
  return (
    <div
      data-projet-card
      className={`rounded-xl border border-line-2 bg-surface-2 p-4 ${archived ? 'opacity-60' : ''}`}
    >
      <div className="flex items-start justify-between gap-3">
        {editing ? (
          <input
            data-projet-nom-input
            autoFocus
            value={nom}
            onChange={(e) => setNom(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && nom.trim()) { patch.mutate({ nom: nom.trim() }); setEditing(false) }
              if (e.key === 'Escape') { setNom(p.nom); setEditing(false) }
            }}
            onBlur={() => { if (nom.trim() && nom !== p.nom) patch.mutate({ nom: nom.trim() }); setEditing(false) }}
            className="min-w-0 flex-1 rounded-md border border-mint/40 bg-surface-3 px-2 py-1 text-sm text-txt-hi outline-none"
          />
        ) : (
          <h3
            data-projet-nom
            className="min-w-0 flex-1 truncate font-display text-sm font-bold text-txt-hi"
            title={p.nom}
          >
            {p.nom}
          </h3>
        )}
        {archived && (
          <span className="shrink-0 rounded-full border border-line-2 px-2 py-0.5 text-[11px] text-txt-dim">archivé</span>
        )}
      </div>

      <ul className="mt-2 space-y-0.5 text-[11px] text-txt-mut">
        {ficheLignes(p.fiche).map((l, i) => (
          <li key={i}>{l}</li>
        ))}
      </ul>
      {p.fiche.criteres_libres && (
        <p className="mt-1.5 border-l-2 border-line-2 pl-2 text-[11px] italic text-txt-dim">
          « {p.fiche.criteres_libres} »
        </p>
      )}

      <div className="mt-3 flex items-center justify-between">
        <span className="font-mono text-[11px] text-txt-dim">
          {p.derniere_execution_at ? `rejoué ${frDate(p.derniere_execution_at)}` : `créé ${frDate(p.created_at)}`}
        </span>
        <div className="flex items-center gap-1.5">
          <button
            data-projet-editer
            onClick={() => setEditing(true)}
            className="rounded-md px-2 py-1 text-[11px] text-txt-mut hover:text-txt-hi"
            title="Renommer"
          >
            Renommer
          </button>
          <button
            data-projet-archiver
            onClick={() => patch.mutate({ statut: archived ? 'actif' : 'archive' })}
            className="rounded-md px-2 py-1 text-[11px] text-txt-mut hover:text-txt-hi"
            title={archived ? 'Réactiver le projet' : 'Archiver le projet'}
          >
            {archived ? 'Réactiver' : 'Archiver'}
          </button>
          <button
            data-projet-ouvrir
            onClick={() => rejouer.mutate()}
            disabled={rejouer.isPending}
            className="rounded-md bg-mint px-3 py-1 text-[11px] font-medium text-[#06130C] hover:brightness-110 disabled:opacity-50"
            title="Ouvrir = rejouer les filtres sur les données actuelles"
          >
            {rejouer.isPending ? '…' : 'Ouvrir'}
          </button>
        </div>
      </div>
    </div>
  )
}

/** Vue PROJETS (copilote-projet, V1) — l'objet persistant : liste, ouvrir = rejouer,
 *  renommer, archiver. Le nouveau projet se crée par l'ENTRETIEN (copilote IA). */
export function ProjetsPanel() {
  const { setView } = useApp()
  const [showArchived, setShowArchived] = useState(false)
  const projetsQ = useQuery({ queryKey: ['projets'], queryFn: getProjets })
  const all = projetsQ.data ?? []
  const actifs = all.filter((p) => p.statut === 'actif')
  const archives = all.filter((p) => p.statut === 'archive')
  const visibles = showArchived ? archives : actifs

  return (
    <div className="flex min-w-0 flex-1 flex-col overflow-y-auto bg-bg">
      <div className="mx-auto w-full max-w-3xl px-8 py-10">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h1 className="font-display text-xl font-bold text-txt-hi">Mes projets</h1>
            <p className="mt-1 text-xs text-txt-mut">
              Chaque projet garde votre cadrage — rejouable sur les données du jour, exportable.
            </p>
          </div>
          <button
            data-projet-nouveau
            onClick={() => setView('ia')}
            className="shrink-0 rounded-lg bg-mint px-4 py-2 text-xs font-medium text-[#06130C] hover:brightness-110"
            title="Décrire un nouveau projet au copilote"
          >
            + Décrire un projet
          </button>
        </div>

        {archives.length > 0 && (
          <div className="mt-6 flex gap-1.5 text-[11px]">
            <button
              onClick={() => setShowArchived(false)}
              className={`rounded-full px-3 py-1 ${!showArchived ? 'bg-surface-3 text-txt-hi' : 'text-txt-mut'}`}
            >
              Actifs ({actifs.length})
            </button>
            <button
              onClick={() => setShowArchived(true)}
              className={`rounded-full px-3 py-1 ${showArchived ? 'bg-surface-3 text-txt-hi' : 'text-txt-mut'}`}
            >
              Archivés ({archives.length})
            </button>
          </div>
        )}

        <div data-projets-liste className="mt-6 space-y-3">
          {projetsQ.isLoading && <p className="text-xs text-txt-dim">Chargement…</p>}
          {!projetsQ.isLoading && visibles.length === 0 && (
            <div
              data-projets-vide
              className="rounded-xl border border-dashed border-line-2 px-6 py-12 text-center"
            >
              <p className="text-sm text-txt-mut">
                {showArchived ? 'Aucun projet archivé.' : 'Aucun projet encore.'}
              </p>
              {!showArchived && (
                <button
                  onClick={() => setView('ia')}
                  className="mt-3 text-xs font-medium text-mint hover:underline"
                >
                  Décrivez votre opération au copilote →
                </button>
              )}
            </div>
          )}
          {visibles.map((p) => (
            <ProjetCard key={p.id} p={p} />
          ))}
        </div>
      </div>
    </div>
  )
}
