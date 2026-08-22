import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  archivePipeline, createCrmColumn, deleteCrmColumn, getArchivedPipeline, getEventsCount, getPipeline,
  getPipelineMeta, patchPipeline, renameCrmColumn, reorderCrmColumns, resetCrmColumns, restorePipeline,
} from '../../lib/api'
import { fmtM2 } from '../../lib/format'
import type { PipelineColumn, PipelineEntry, PipelineMeta } from '../../lib/types'
import { Tip } from '../Tip'
import { ErrorState } from '../States'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'

/* accents de colonnes = tokens (txt-dim / st-creuser / mint / st-ecartee) en valeur
   hex car servis via style= (pas de classe dynamique). */
const TONE_ACCENT: Record<string, string> = {
  cold: '#5C7268', warm: '#E8B44C', hot: '#5CE6A1', reject: '#E8695A',
}

function Card({ e, onDragStart, newEvents, onArchive, onEdit }: { e: PipelineEntry; onDragStart: (ev: React.DragEvent) => void; newEvents: number; onArchive: () => void; onEdit: () => void }) {
  const { select, setView } = useApp()
  return (
    <div
      draggable
      onDragStart={onDragStart}
      onClick={(ev) => {
        // M137 — le CORPS de la carte ouvre l'ÉCRAN D'ÉDITION (note/priorité/relance/prospection).
        // Le bouton IDU garde l'ouverture de la fiche. Les autres boutons (✕) sont inertes ici.
        if ((ev.target as HTMLElement).closest('button')) return
        onEdit()
      }}
      className="group cursor-pointer rounded-lg bg-surface-3 p-3 shadow-elev-1 ring-1 ring-transparent transition-shadow duration-quick active:cursor-grabbing hover:ring-mint/30"
      title="Éditer la carte (note, priorité, relance) · glisser pour changer d'étape"
    >
      <div className="flex items-center justify-between gap-2">
        <button
          onClick={() => { setView('cartes'); select(e.idu) }}
          className="truncate font-mono text-xs font-medium text-txt-hi transition-colors duration-quick hover:text-mint"
          title="Ouvrir la fiche sur la carte"
        >
          {e.idu}
        </button>
        {newEvents > 0 && (
          <Tip tip="Événements non lus sur cette parcelle (cloche)">
            <span className="shrink-0 rounded-full bg-violet/15 px-1.5 py-0.5 text-[9px] font-medium text-violet">
              {newEvents} nouveau{newEvents > 1 ? 'x' : ''}
            </span>
          </Tip>
        )}
        <button
          onClick={onArchive}
          className="-m-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-txt-dim opacity-40 transition-opacity duration-quick hover:text-st-ecartee group-hover:opacity-100"
          title="Archiver (réversible — restaurable dans « Archivées »)"
          aria-label="Archiver la carte"
        >
          ✕
        </button>
      </div>
      <div className="tnum mt-1 truncate text-[11px] text-txt-mut">
        {e.parcel.surface_m2 ? `${fmtM2(e.parcel.surface_m2)} · ` : ''}{e.parcel.commune}
      </div>
      {/* Phase 2 : d'où vient la piste (projet) */}
      {e.projet && (
        <div className="mt-1 truncate text-[10.5px] text-violet" title={`Piste du projet « ${e.projet.nom} »`}>
          ▸ {e.projet.nom}
        </div>
      )}
      {/* Phase 2 : contact proprio — PRIVACY : personne morale publique OU particulier JAMAIS nommé */}
      {e.proprietaire_public && (
        e.proprietaire_public.type === 'personne_morale' ? (
          // DA §8 — carte CRM sans SIREN (nom du tiers en casse normale, texte neutre).
          <div className="mt-1 truncate text-[10.5px] text-txt-mut" title="Personne morale (registre public DGFiP)">
            <span className="text-txt">{e.proprietaire_public.denomination}</span>
          </div>
        ) : (
          <div className="mt-1 truncate text-[10.5px] italic text-txt-dim" title="Propriétaire personne physique — jamais nommé (privacy)">
            Propriétaire particulier — non communiqué
          </div>
        )
      )}
      {/* M136 P1 — infos de coin bas RETIRÉES (affichage seul) : coin bas-gauche (verdict
          `meta.label` + rang `#rang_v2`) et coin bas-droite (priorité `e.priority`). Aucune
          logique/endpoint/donnée touchés. Les champs restent au payload /pipeline
          (premium.rang_v2, verdict.rang, priority) — purge = décision de Vic (cf. audit). */}
    </div>
  )
}

/* ── M12 LOT H — dialogue « où déplacer les cartes ? » avant suppression d'une colonne peuplée.
   La boussole produit : une carte ne disparaît JAMAIS en silence — le déplacement est obligatoire. */
function DeleteColumnDialog({ col, others, onCancel, onConfirm }: {
  col: PipelineColumn; others: PipelineColumn[]; onCancel: () => void
  onConfirm: (moveTo: number | null) => void
}) {
  const [target, setTarget] = useState<number | ''>(others[0]?.id ?? '')
  const populated = (col as { cards?: number }).cards ?? 0
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onCancel}>
      <div className="w-full max-w-sm rounded-xl border border-line-2 bg-surface-1 p-5 shadow-elev-2"
        onClick={(ev) => ev.stopPropagation()}>
        <h3 className="font-display text-sm font-bold text-txt-hi">Supprimer « {col.label} »</h3>
        {populated > 0 ? (
          <>
            <p className="mt-2 text-[12px] text-txt-mut">
              Cette colonne contient <span className="text-txt">{populated} carte{populated > 1 ? 's' : ''}</span>.
              Choisissez où les déplacer — aucune carte n'est perdue.
            </p>
            <label className="mt-3 block text-[11px] text-txt-dim">Déplacer les cartes vers</label>
            <select
              value={target}
              onChange={(ev) => setTarget(ev.target.value ? Number(ev.target.value) : '')}
              className="mt-1 w-full rounded-md border border-line-2 bg-surface-2 px-2 py-1.5 text-[12px] text-txt"
            >
              {others.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
            </select>
          </>
        ) : (
          <p className="mt-2 text-[12px] text-txt-mut">Cette colonne est vide — suppression immédiate.</p>
        )}
        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onCancel}
            className="rounded-md px-3 py-1.5 text-[12px] text-txt-dim hover:text-txt">Annuler</button>
          <button
            onClick={() => onConfirm(populated > 0 ? (target === '' ? null : target) : null)}
            disabled={populated > 0 && target === ''}
            className="rounded-md bg-st-ecartee/90 px-3 py-1.5 text-[12px] font-medium text-bg hover:bg-st-ecartee disabled:opacity-40"
          >Supprimer</button>
        </div>
      </div>
    </div>
  )
}

/* M137 — écran d'édition d'une carte : câble ce que le modèle + le PATCH portaient déjà mais que
   AUCUNE UI n'exposait (note, priorité, date de relance, prospection). Tout passe par le PATCH
   existant (cloison compte_id en place). */
function CardEditPanel({ e, meta, onCancel, onSave, saving }: {
  e: PipelineEntry; meta: PipelineMeta | undefined; onCancel: () => void
  onSave: (body: Record<string, unknown>) => void; saving: boolean
}) {
  const { select, setView } = useApp()
  const pr = e.prospection ?? {}
  const [priority, setPriority] = useState(e.priority)
  const [reminder, setReminder] = useState(e.reminder_date ?? '')
  const [notes, setNotes] = useState(e.notes ?? '')
  const [statutProp, setStatutProp] = useState(pr.statut_proprietaire ?? 'inconnu')
  const [action, setAction] = useState(pr.prochaine_action ?? '')
  const [nom, setNom] = useState(pr.contact_nom ?? '')
  const [tel, setTel] = useState(pr.contact_telephone ?? '')
  const [mail, setMail] = useState(pr.contact_email ?? '')
  const inputCls = 'mt-1 w-full rounded-md border border-line-2 bg-surface-2 px-2 py-1.5 text-[12px] text-txt focus:border-mint focus:outline-none'
  const submit = () => onSave({
    priority, notes, reminder_date: reminder,
    prospection: { statut_proprietaire: statutProp, prochaine_action: action,
                   contact_nom: nom, contact_telephone: tel, contact_email: mail },
  })
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onCancel}>
      <div className="flex max-h-[85vh] w-full max-w-md flex-col rounded-xl border border-line-2 bg-surface-1 shadow-elev-2"
        onClick={(ev) => ev.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-line-2 px-5 py-3">
          <button onClick={() => { setView('cartes'); select(e.idu) }}
            className="font-mono text-xs font-medium text-txt-hi hover:text-mint" title="Ouvrir la fiche">{e.idu}</button>
          <button onClick={onCancel} className="text-txt-dim hover:text-txt" aria-label="Fermer">✕</button>
        </div>
        <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-5 py-4">
          <label className="block text-[11px] text-txt-dim">Priorité
            <select value={priority} onChange={(ev) => setPriority(ev.target.value)} className={inputCls}>
              {(meta?.priorities ?? []).map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
            </select>
          </label>
          <label className="block text-[11px] text-txt-dim">Date de relance
            <input type="date" value={reminder} onChange={(ev) => setReminder(ev.target.value)} className={inputCls} />
          </label>
          <label className="block text-[11px] text-txt-dim">Statut du propriétaire
            <select value={statutProp} onChange={(ev) => setStatutProp(ev.target.value)} className={inputCls}>
              {(meta?.proprietaire_statuts ?? []).map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
            </select>
          </label>
          <label className="block text-[11px] text-txt-dim">Prochaine action
            <input value={action} maxLength={2000} onChange={(ev) => setAction(ev.target.value)}
              placeholder="ex. rappeler le propriétaire" className={inputCls} />
          </label>
          <div className="grid grid-cols-2 gap-2">
            <label className="block text-[11px] text-txt-dim">Contact — nom
              <input value={nom} maxLength={2000} onChange={(ev) => setNom(ev.target.value)} className={inputCls} />
            </label>
            <label className="block text-[11px] text-txt-dim">Téléphone
              <input value={tel} maxLength={2000} onChange={(ev) => setTel(ev.target.value)} className={inputCls} />
            </label>
          </div>
          <label className="block text-[11px] text-txt-dim">Email
            <input value={mail} maxLength={2000} onChange={(ev) => setMail(ev.target.value)} className={inputCls} />
          </label>
          <label className="block text-[11px] text-txt-dim">Notes
            <textarea value={notes} maxLength={4000} rows={3} onChange={(ev) => setNotes(ev.target.value)}
              className={`${inputCls} resize-none`} />
          </label>
          <p className="text-[10px] leading-snug text-txt-faint">
            Contact saisi manuellement — LA BUSE ne récupère aucune donnée propriétaire automatiquement.
          </p>
        </div>
        <div className="flex justify-end gap-2 border-t border-line-2 px-5 py-3">
          <button onClick={onCancel} className="rounded-md px-3 py-1.5 text-[12px] text-txt-dim hover:text-txt">Annuler</button>
          <button onClick={submit} disabled={saving}
            className="rounded-md bg-mint px-3 py-1.5 text-[12px] font-medium text-mint-ink hover:brightness-110 disabled:opacity-40">
            {saving ? '…' : 'Enregistrer'}</button>
        </div>
      </div>
    </div>
  )
}

export function Kanban() {
  const qc = useQueryClient()
  const { setToast } = useApp()
  const meta = useQuery({ queryKey: ['pipeline-meta'], queryFn: getPipelineMeta })
  const entries = useQuery({ queryKey: ['pipeline'], queryFn: getPipeline })
  const evCount = useQuery({ queryKey: ['events-count'], queryFn: getEventsCount, refetchInterval: 60_000 })
  const [dragId, setDragId] = useState<number | null>(null)
  const [overCol, setOverCol] = useState<string | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editLabel, setEditLabel] = useState('')
  const [pendingDelete, setPendingDelete] = useState<PipelineColumn | null>(null)
  // M137 — archivage réversible : confirmation avant d'archiver, panneau pour consulter/restaurer.
  const [pendingArchive, setPendingArchive] = useState<PipelineEntry | null>(null)
  const [showArchived, setShowArchived] = useState(false)
  const [editingEntry, setEditingEntry] = useState<PipelineEntry | null>(null)   // M137 — écran d'édition de carte
  const archived = useQuery({ queryKey: ['pipeline-archived'], queryFn: getArchivedPipeline, enabled: showArchived })
  // QA-46 (M13-C) : le kanban NE DÉFILE PLUS horizontalement (barre de scroll proscrite). Les
  // colonnes qui ne tiennent pas côte à côte sont paginées : on affiche une FENÊTRE de COLS_PAR_VUE
  // colonnes qui remplissent la largeur (flex-1), et deux flèches ‹ › font glisser la fenêtre.
  // Le drag-drop reste possible vers toute colonne visible ; pour une colonne hors fenêtre, on
  // pagine d'abord. Choix consigné au rapport (mandat : « pas une barre horizontale »).
  const COLS_PAR_VUE = 5
  const [winStart, setWinStart] = useState(0)
  // M13-B3 : plus AUCUN window.prompt/confirm — ajout inline + dialogue de réinitialisation en DA.
  const [adding, setAdding] = useState(false)
  const [newColLabel, setNewColLabel] = useState('')
  const [confirmReset, setConfirmReset] = useState(false)
  // M137 (C1) — optimistic + rollback + toast : un état affiché que le serveur n'a PAS confirmé ne
  // persiste jamais. onMutate applique localement + snapshot ; onError restaure le snapshot + prévient.
  const move = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) => patchPipeline(id, { status }),
    onMutate: async ({ id, status }) => {
      await qc.cancelQueries({ queryKey: ['pipeline'] })
      const prev = qc.getQueryData<PipelineEntry[]>(['pipeline'])
      qc.setQueryData<PipelineEntry[]>(['pipeline'], (old) => old?.map((x) => (x.id === id ? { ...x, status } : x)))
      return { prev }
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(['pipeline'], ctx.prev)
      setToast('Déplacement échoué — la carte est revenue à son étape.')
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ['pipeline'] }),
  })
  const archive = useMutation({
    mutationFn: (id: number) => archivePipeline(id),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: ['pipeline'] })
      const prev = qc.getQueryData<PipelineEntry[]>(['pipeline'])
      qc.setQueryData<PipelineEntry[]>(['pipeline'], (old) => old?.filter((x) => x.id !== id))
      return { prev }
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(['pipeline'], ctx.prev)
      setToast("Archivage échoué — la carte est toujours là.")
    },
    onSuccess: () => setToast('Carte archivée — restaurable dans « Archivées ».'),
    onSettled: () => {
      setPendingArchive(null)
      qc.invalidateQueries({ queryKey: ['pipeline'] })
      qc.invalidateQueries({ queryKey: ['pipeline-archived'] })
    },
  })
  const restore = useMutation({
    mutationFn: (id: number) => restorePipeline(id),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: ['pipeline-archived'] })
      const prev = qc.getQueryData<PipelineEntry[]>(['pipeline-archived'])
      qc.setQueryData<PipelineEntry[]>(['pipeline-archived'], (old) => old?.filter((x) => x.id !== id))
      return { prev }
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(['pipeline-archived'], ctx.prev)
      setToast('Restauration échouée — réessayez.')
    },
    onSuccess: () => setToast('Carte restaurée.'),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['pipeline'] })
      qc.invalidateQueries({ queryKey: ['pipeline-archived'] })
    },
  })
  // M137 Lot 3 — édition de carte (note/priorité/relance/prospection) via le PATCH existant.
  const patch = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Record<string, unknown> }) => patchPipeline(id, body),
    onMutate: async ({ id, body }) => {
      await qc.cancelQueries({ queryKey: ['pipeline'] })
      const prev = qc.getQueryData<PipelineEntry[]>(['pipeline'])
      qc.setQueryData<PipelineEntry[]>(['pipeline'], (old) => old?.map((x) => (x.id === id
        ? { ...x, ...body, prospection: { ...(x.prospection ?? {}), ...((body.prospection as Record<string, string>) ?? {}) } }
        : x)))
      return { prev }
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(['pipeline'], ctx.prev)
      setToast('Édition échouée — vos changements ne sont pas enregistrés.')
    },
    onSuccess: () => { setEditingEntry(null); setToast('Carte mise à jour.') },
    onSettled: () => qc.invalidateQueries({ queryKey: ['pipeline'] }),
  })
  // M12 LOT H — mutations colonnes (invalident meta + pipeline : le remap de cartes est visible)
  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ['pipeline-meta'] })
    qc.invalidateQueries({ queryKey: ['pipeline'] })
  }
  // M137 (C1) — un échec de mutation ne tombe plus dans le vide : message visible (les mutations de
  // colonnes invalident au succès, sans optimistic, donc pas de rollback à faire — juste prévenir).
  const onColError = () => setToast("Action sur la colonne échouée — réessayez.")
  const addCol = useMutation({
    mutationFn: (label: string) => createCrmColumn(label),
    onSuccess: () => { setAdding(false); setNewColLabel(''); invalidateAll() }, onError: onColError,
  })
  const renameCol = useMutation({
    mutationFn: ({ id, label }: { id: number; label: string }) => renameCrmColumn(id, label),
    onSuccess: () => { setEditingId(null); invalidateAll() }, onError: onColError,
  })
  const reorderCol = useMutation({ mutationFn: (order: number[]) => reorderCrmColumns(order), onSuccess: invalidateAll, onError: onColError })
  const delCol = useMutation({
    mutationFn: ({ id, moveTo }: { id: number; moveTo: number | null }) => deleteCrmColumn(id, moveTo),
    onSuccess: () => { setPendingDelete(null); invalidateAll() }, onError: onColError,
  })
  const resetCols = useMutation({ mutationFn: () => resetCrmColumns(), onSuccess: () => { setConfirmReset(false); invalidateAll() }, onError: onColError })

  if (meta.isError || entries.isError) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <ErrorState message="Pipeline inaccessible"
          hint="Le serveur ne répond pas — vos données sont intactes, seule la connexion est en cause."
          retry={() => { meta.refetch(); entries.refetch() }} />
      </div>
    )
  }

  const cols = meta.data?.columns ?? []
  // Fenêtre paginée (QA-46) : quand il y a plus de COLS_PAR_VUE colonnes, on n'en montre qu'une
  // tranche. maxStart = dernier décalage laissant une fenêtre pleine ; start est borné.
  const paginated = cols.length > COLS_PAR_VUE
  const maxStart = Math.max(0, cols.length - COLS_PAR_VUE)
  const start = Math.min(winStart, maxStart)
  const visibleCols = paginated ? cols.slice(start, start + COLS_PAR_VUE) : cols
  const byCol = (key: string) => (entries.data ?? []).filter((e) => e.status === key)
  const cardCount = (key: string) => byCol(key).length

  const startEdit = (c: PipelineColumn) => { setEditingId(c.id ?? null); setEditLabel(c.label) }
  const commitEdit = () => {
    if (editingId != null && editLabel.trim()) renameCol.mutate({ id: editingId, label: editLabel.trim() })
    else setEditingId(null)
  }
  const doAdd = () => { setAdding(true); setNewColLabel('') }
  const commitAdd = () => {
    const label = newColLabel.trim()
    if (label) addCol.mutate(label)
    else setAdding(false)
  }
  const moveCol = (idx: number, dir: -1 | 1) => {
    const ids = cols.map((c) => c.id!).filter((i) => i != null)
    const j = idx + dir
    if (j < 0 || j >= ids.length) return
    ;[ids[idx], ids[j]] = [ids[j], ids[idx]]
    reorderCol.mutate(ids)
  }
  // colonne enrichie du nombre de cartes (le dialogue de suppression en a besoin)
  const withCounts = cols.map((c) => ({ ...c, cards: cardCount(c.key) })) as (PipelineColumn & { cards: number })[]

  return (
    <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
      <div className="flex shrink-0 flex-wrap items-baseline justify-between gap-2 px-4 pt-5 sm:px-6">
        <div>
          <h2 className="font-display text-lg font-bold text-txt-hi">CRM — pipeline de prospection</h2>
          <p className="mt-0.5 text-[11px] text-txt-dim">
            {(entries.data ?? []).length} parcelle{(entries.data ?? []).length > 1 ? 's' : ''} suivie{(entries.data ?? []).length > 1 ? 's' : ''} ·
            glisser une carte pour changer d'étape · ajout depuis la fiche (+ Pipeline)
          </p>
        </div>
        {/* H (M12) : barre d'édition des colonnes (personnaliser/ajouter/réinitialiser). */}
        <div className="flex shrink-0 items-center gap-2">
          {/* QA-46 (M13-C) : pagination par FLÈCHES (plus de défilement horizontal). Les flèches
              n'apparaissent que si toutes les colonnes ne tiennent pas dans la fenêtre. */}
          {paginated && !editMode && (
            <span className="flex shrink-0 items-center gap-1.5">
              <button
                onClick={() => setWinStart((s) => Math.max(0, Math.min(s, maxStart) - 1))}
                disabled={start === 0}
                className="flex h-6 w-6 items-center justify-center rounded-md border border-line-2 text-txt-dim hover:border-mint hover:text-mint disabled:opacity-25"
                title="Colonnes précédentes" aria-label="Colonnes précédentes">‹</button>
              <span className="whitespace-nowrap font-mono text-[10.5px] text-txt-mut">
                {start + 1}–{Math.min(start + COLS_PAR_VUE, cols.length)} / {cols.length}
              </span>
              <button
                onClick={() => setWinStart((s) => Math.min(maxStart, Math.min(s, maxStart) + 1))}
                disabled={start >= maxStart}
                className="flex h-6 w-6 items-center justify-center rounded-md border border-line-2 text-txt-dim hover:border-mint hover:text-mint disabled:opacity-25"
                title="Colonnes suivantes" aria-label="Colonnes suivantes">›</button>
            </span>
          )}
          {editMode && (
            <>
              {/* M13-B3 : ajout INLINE (plus de window.prompt) — le champ apparaît ici,
                  Entrée valide, Échap annule, la colonne apparaît immédiatement (invalidateAll). */}
              {adding ? (
                <span className="flex items-center gap-1">
                  <input
                    autoFocus
                    value={newColLabel}
                    onChange={(ev) => setNewColLabel(ev.target.value)}
                    onKeyDown={(ev) => { if (ev.key === 'Enter') commitAdd(); if (ev.key === 'Escape') { setAdding(false); setNewColLabel('') } }}
                    placeholder="Nom de la colonne…"
                    maxLength={80}
                    className="w-40 rounded-md border border-mint/50 bg-surface-2 px-2 py-1 text-[11px] text-txt focus:border-mint focus:outline-none"
                    aria-label="Nom de la nouvelle colonne"
                  />
                  <button onClick={commitAdd} disabled={!newColLabel.trim() || addCol.isPending}
                    className="rounded-md bg-mint px-2 py-1 text-[11px] font-medium text-mint-ink hover:brightness-110 disabled:opacity-40"
                    title="Ajouter">{addCol.isPending ? '…' : 'Ajouter'}</button>
                  <button onClick={() => { setAdding(false); setNewColLabel('') }}
                    className="rounded-md px-2 py-1 text-[11px] text-txt-dim hover:text-txt" title="Annuler">Annuler</button>
                </span>
              ) : (
                <button onClick={doAdd}
                  className="rounded-md border border-line-2 px-2.5 py-1 text-[11px] text-txt hover:border-mint hover:text-mint"
                  title="Ajouter une colonne">+ Colonne</button>
              )}
              <button
                onClick={() => setConfirmReset(true)}
                className="rounded-md border border-line-2 px-2.5 py-1 text-[11px] text-txt-dim hover:border-st-ecartee hover:text-st-ecartee"
                title="Restaurer le kanban LABUSE par défaut">Réinitialiser</button>
            </>
          )}
          {/* M137 — accès aux cartes archivées (consulter / restaurer). */}
          {!editMode && (
            <button
              onClick={() => setShowArchived(true)}
              className="rounded-md border border-line-2 px-2.5 py-1 text-[11px] text-txt-dim hover:border-mint hover:text-mint"
              title="Voir les cartes archivées (restaurables)">Archivées</button>
          )}
          <button
            onClick={() => { setEditMode((v) => !v); setEditingId(null) }}
            className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors duration-quick ${
              editMode ? 'bg-mint/15 text-mint' : 'border border-line-2 text-txt-dim hover:text-txt'}`}
            title="Personnaliser les colonnes du kanban"
          >{editMode ? 'Terminé' : 'Personnaliser'}</button>
        </div>
      </div>
      <div className="relative mt-4 min-h-0 flex-1">
        {/* QA-46 (M13-C) : plus de `overflow-x-auto`. Les colonnes de la fenêtre visible sont
            `flex-1 basis-0 min-w-0` — elles se PARTAGENT la largeur, aucune barre horizontale.
            G6 (M12) : items-start préservé (une colonne vide ne s'étire pas sur toute la hauteur). */}
        <div data-crm-cols className="flex h-full items-start gap-3 overflow-x-clip px-4 pb-5 sm:px-6">
        {meta.isLoading && <div className="p-2"><Loading label="Chargement du pipeline" className="text-xs" /></div>}
        {visibleCols.map((c) => {
          const idx = cols.indexOf(c)
          const items = byCol(c.key)
          const accent = TONE_ACCENT[c.tone ?? ''] ?? '#5C7268'
          return (
            <div
              key={c.key}
              onDragOver={(ev) => { ev.preventDefault(); setOverCol(c.key) }}
              onDragLeave={() => setOverCol((o) => (o === c.key ? null : o))}
              onDrop={(ev) => {
                ev.preventDefault()
                setOverCol(null)
                if (dragId != null) move.mutate({ id: dragId, status: c.key })
                setDragId(null)
              }}
              className={`flex max-h-full min-w-0 flex-1 basis-0 flex-col rounded-xl border bg-surface-1 shadow-elev-1 transition-colors duration-quick ${
                overCol === c.key ? 'border-mint ring-1 ring-mint/40' : 'border-transparent'}`}
            >
              <div className="flex shrink-0 items-center gap-2 px-3 py-2.5">
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: accent }} />
                {editMode && editingId === c.id ? (
                  <input
                    autoFocus
                    value={editLabel}
                    onChange={(ev) => setEditLabel(ev.target.value)}
                    onBlur={commitEdit}
                    onKeyDown={(ev) => { if (ev.key === 'Enter') commitEdit(); if (ev.key === 'Escape') setEditingId(null) }}
                    className="min-w-0 flex-1 rounded border border-mint/40 bg-surface-2 px-1 py-0.5 text-[11px] text-txt"
                    aria-label="Renommer la colonne"
                  />
                ) : (
                  <button
                    disabled={!editMode}
                    onClick={() => editMode && startEdit(c)}
                    className={`min-w-0 flex-1 truncate text-left text-[11px] font-medium text-txt ${editMode ? 'cursor-text hover:text-mint' : 'cursor-default'}`}
                    title={editMode ? 'Cliquer pour renommer' : c.label}
                  >{c.label}</button>
                )}
                {!editMode && <span className="ml-auto font-mono text-[11px] text-txt-dim">{items.length}</span>}
                {editMode && (
                  <span className="ml-auto flex shrink-0 items-center gap-0.5">
                    <button onClick={() => moveCol(idx, -1)} disabled={idx === 0}
                      className="flex h-5 w-5 items-center justify-center rounded text-txt-dim hover:text-txt disabled:opacity-25"
                      title="Déplacer à gauche" aria-label="Déplacer la colonne à gauche">←</button>
                    <button onClick={() => moveCol(idx, 1)} disabled={idx === cols.length - 1}
                      className="flex h-5 w-5 items-center justify-center rounded text-txt-dim hover:text-txt disabled:opacity-25"
                      title="Déplacer à droite" aria-label="Déplacer la colonne à droite">→</button>
                    <button
                      onClick={() => setPendingDelete(withCounts[idx])}
                      disabled={cols.length <= 1}
                      className="flex h-5 w-5 items-center justify-center rounded text-txt-dim hover:text-st-ecartee disabled:opacity-25"
                      title={cols.length <= 1 ? 'La dernière colonne ne peut pas être supprimée' : 'Supprimer la colonne'}
                      aria-label="Supprimer la colonne">✕</button>
                  </span>
                )}
              </div>
              {/* G6 (M12) : min-h modeste = zone de dépôt confortable pour une colonne vide, sans
                  la colonne géante de ~800 px. Une colonne pleine défile en interne (max-h-full). */}
              <div className="flex min-h-[72px] flex-1 flex-col gap-2.5 overflow-y-auto overflow-x-clip px-2.5 pb-2.5">
                {items.map((e) => (
                  <Card key={e.id} e={e} onDragStart={() => setDragId(e.id)}
                    newEvents={evCount.data?.par_parcelle[e.idu] ?? 0}
                    onArchive={() => setPendingArchive(e)}
                    onEdit={() => setEditingEntry(e)} />
                ))}
                {items.length === 0 && (
                  /* DA §8 — colonne vide PARLANTE (dit quoi faire), pas un « vide » muet. */
                  <div className="empty">Aucune parcelle<div className="mt-1 text-txt-faint">glissez-en une ici</div></div>
                )}
              </div>
            </div>
          )
        })}
        </div>
      </div>
      {pendingDelete && (
        <DeleteColumnDialog
          col={pendingDelete}
          others={withCounts.filter((c) => c.id !== pendingDelete.id)}
          onCancel={() => setPendingDelete(null)}
          onConfirm={(moveTo) => delCol.mutate({ id: pendingDelete.id!, moveTo })}
        />
      )}
      {/* M13-B3 : réinitialisation confirmée par un dialogue en DA LABUSE (plus de window.confirm). */}
      {confirmReset && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={() => setConfirmReset(false)}>
          <div className="w-full max-w-sm rounded-xl border border-line-2 bg-surface-1 p-5 shadow-elev-2"
            onClick={(ev) => ev.stopPropagation()}>
            <h3 className="font-display text-sm font-bold text-txt-hi">Réinitialiser le kanban</h3>
            <p className="mt-2 text-[12px] text-txt-mut">
              Restaurer le kanban LABUSE par défaut ? Toutes les cartes seront replacées dans la
              première colonne — aucune n'est perdue.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setConfirmReset(false)}
                className="rounded-md px-3 py-1.5 text-[12px] text-txt-dim hover:text-txt">Annuler</button>
              <button onClick={() => resetCols.mutate()} disabled={resetCols.isPending}
                className="rounded-md bg-st-ecartee/90 px-3 py-1.5 text-[12px] font-medium text-bg hover:bg-st-ecartee disabled:opacity-40">
                {resetCols.isPending ? '…' : 'Réinitialiser'}</button>
            </div>
          </div>
        </div>
      )}
      {/* M137 — écran d'édition d'une carte (note/priorité/relance/prospection) via le PATCH existant. */}
      {editingEntry && (
        <CardEditPanel
          e={editingEntry}
          meta={meta.data}
          saving={patch.isPending}
          onCancel={() => setEditingEntry(null)}
          onSave={(body) => patch.mutate({ id: editingEntry.id, body })}
        />
      )}
      {/* M137 — confirmation avant ARCHIVAGE (réversible, mais on prévient : la carte quitte le tableau). */}
      {pendingArchive && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={() => setPendingArchive(null)}>
          <div className="w-full max-w-sm rounded-xl border border-line-2 bg-surface-1 p-5 shadow-elev-2"
            onClick={(ev) => ev.stopPropagation()}>
            <h3 className="font-display text-sm font-bold text-txt-hi">Archiver cette carte</h3>
            <p className="mt-2 text-[12px] text-txt-mut">
              <span className="font-mono text-txt">{pendingArchive.idu.slice(8)}</span> quitte le tableau
              mais n'est <b>pas supprimée</b> : notes et prospection saisies sont conservées et
              restaurables depuis « Archivées ».
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setPendingArchive(null)}
                className="rounded-md px-3 py-1.5 text-[12px] text-txt-dim hover:text-txt">Annuler</button>
              <button onClick={() => archive.mutate(pendingArchive.id)} disabled={archive.isPending}
                className="rounded-md bg-st-ecartee/90 px-3 py-1.5 text-[12px] font-medium text-bg hover:bg-st-ecartee disabled:opacity-40">
                {archive.isPending ? '…' : 'Archiver'}</button>
            </div>
          </div>
        </div>
      )}
      {/* M137 — panneau des cartes ARCHIVÉES : consulter + restaurer. Aucune purge automatique. */}
      {showArchived && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={() => setShowArchived(false)}>
          <div className="flex max-h-[80vh] w-full max-w-md flex-col rounded-xl border border-line-2 bg-surface-1 p-5 shadow-elev-2"
            onClick={(ev) => ev.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h3 className="font-display text-sm font-bold text-txt-hi">Cartes archivées</h3>
              <button onClick={() => setShowArchived(false)} className="text-txt-dim hover:text-txt" aria-label="Fermer">✕</button>
            </div>
            <div className="mt-3 min-h-0 flex-1 space-y-2 overflow-y-auto">
              {archived.isLoading && <Loading label="Chargement" className="text-xs" />}
              {archived.data?.length === 0 && <p className="text-[12px] text-txt-dim">Aucune carte archivée.</p>}
              {(archived.data ?? []).map((e) => (
                <div key={e.id} className="flex items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-2">
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-mono text-xs text-txt-hi">{e.idu.slice(8)}</div>
                    <div className="truncate text-[10.5px] text-txt-mut">{e.parcel.commune}</div>
                  </div>
                  <button onClick={() => restore.mutate(e.id)} disabled={restore.isPending}
                    className="shrink-0 rounded-md border border-line-2 px-2 py-1 text-[11px] text-txt hover:border-mint hover:text-mint disabled:opacity-40">
                    Restaurer</button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
