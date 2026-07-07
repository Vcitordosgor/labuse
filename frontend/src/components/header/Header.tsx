import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { deleteSearch, getCommunes, getEvents, getParcelsGeojson, getSavedSearches, markAllEventsRead, markEventRead, saveSearch, searchParcels } from '../../lib/api'
import { filtersToHash } from '../../lib/filters'
import { activeChips, FLAG_DEFS, removeToken } from '../../lib/filters'
import { STATUT_META } from '../../lib/status'
import type { Statut } from '../../lib/types'
import { EMPTY_FILTERS, useApp } from '../../store/useApp'

function Omnibox() {
  const { query, setQuery, select, setView, commune } = useApp()
  const ref = useRef<HTMLInputElement>(null)
  const geo = useQuery({ queryKey: ['geojson', commune], queryFn: getParcelsGeojson, enabled: commune != null })

  // raccourci « / » → focus (comme indiqué par le kbd)
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault()
        ref.current?.focus()
      }
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [])

  // Entrée : premier IDU correspondant → ouvre sa fiche (recherche = filtre live de la liste).
  // Mode île (ou introuvable localement) : le serveur cherche (/parcels/search) — le client
  // n'a plus les 431k features en mémoire.
  const onEnter = async () => {
    const qn = query.trim().toUpperCase().replace(/\s+/g, '')
    if (!qn) return
    const hit = geo.data?.features.find((f) => {
      const idu = String(f.properties?.idu ?? '').toUpperCase()
      return idu.includes(qn) || idu.slice(8).includes(qn)
    })
    if (hit) {
      setView('cartes')
      select(String(hit.properties?.idu))
      return
    }
    const remote = await searchParcels(qn).catch(() => [])
    if (remote[0]) {
      setView('cartes')
      select(remote[0].idu)
    }
  }

  return (
    <div className="flex h-8 w-[360px] items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 focus-within:border-[#2E6B4F]">
      <svg viewBox="0 0 20 20" className="h-4 w-4 shrink-0 text-txt-mut">
        <circle cx="9" cy="9" r="5.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
        <line x1="13" y1="13" x2="17" y2="17" stroke="currentColor" strokeWidth="1.5" />
      </svg>
      <input ref={ref} value={query} onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && onEnter()}
        placeholder="Rechercher un IDU : AB 0234, DE0805…"
        title="Filtre la liste des résultats ; Entrée ouvre la première fiche correspondante"
        className="min-w-0 flex-1 bg-transparent text-xs text-txt placeholder:text-txt-mut focus:outline-none" />
      <kbd className="shrink-0 rounded border border-line-2 px-1 font-mono text-[11px] text-txt-dim">/</kbd>
    </div>
  )
}

function NumField({ label, value, onChange, placeholder }: {
  label: string; value: number | null; onChange: (v: number | null) => void; placeholder: string
}) {
  return (
    <div className="min-w-0 flex-1">
      <label className="font-mono text-[10px] tracking-widest text-txt-dim">{label}</label>
      <input type="number" min={0} value={value ?? ''} placeholder={placeholder}
        onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))}
        className="mt-1 w-full rounded-lg border border-line-2 bg-surface-3 px-2 py-1 text-xs text-txt focus:border-mint focus:outline-none" />
    </div>
  )
}

function CheckRow({ label, on, toggle }: { label: string; on: boolean; toggle: () => void }) {
  return (
    <button onClick={toggle} className="flex items-center gap-2 text-left">
      <span className={`flex h-[13px] w-[13px] items-center justify-center rounded-[3px] ${on ? 'bg-mint' : 'border border-line-2'}`}>
        {on && <svg viewBox="0 0 10 10" className="h-2.5 w-2.5"><polyline points="2,5.5 4,7.5 8,3" fill="none" stroke="#06130C" strokeWidth="1.8" /></svg>}
      </span>
      <span className={`text-[11px] ${on ? 'text-txt' : 'text-txt-mut'}`}>{label}</span>
    </button>
  )
}

// Popover d'ajout de filtre — filtres MÉTIER combinables (statuts multi, plages, booléens, flags).
function AddFilter() {
  const { filters, setFilter, setFilters } = useApp()
  const [open, setOpen] = useState(false)
  const STATUTS: Statut[] = ['chaude', 'a_surveiller', 'a_creuser', 'ecartee']
  useEffect(() => {
    if (!open) return
    const h = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [open])
  const toggleStatut = (s: Statut) =>
    setFilter('statuts', filters.statuts.includes(s) ? filters.statuts.filter((x) => x !== s) : [...filters.statuts, s])
  const toggleFlag = (k: string) =>
    setFilter('flags', filters.flags.includes(k) ? filters.flags.filter((x) => x !== k) : [...filters.flags, k])
  return (
    <div className="relative">
      <button onClick={() => setOpen((o) => !o)}
        className={`flex h-[26px] shrink-0 items-center gap-1 rounded-full border border-dashed px-3 text-xs ${
          open ? 'border-mint text-mint' : 'border-line-2 text-txt-mut hover:text-txt'}`}>+ Filtre</button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-9 z-20 w-[300px] rounded-xl border border-line-2 bg-surface-2 p-4 shadow-2xl">
            <label className="font-mono text-[10px] tracking-widest text-txt-dim">STATUT (multi)</label>
            <div className="mb-3 mt-1.5 flex flex-wrap gap-1.5">
              {STATUTS.map((s) => (
                <button key={s} onClick={() => toggleStatut(s)}
                  className={`rounded-full border px-2 py-0.5 text-[11px] ${
                    filters.statuts.includes(s) ? 'border-mint text-txt-hi' : 'border-line-2 text-txt-mut'}`}>
                  {STATUT_META[s].label}
                </button>
              ))}
            </div>
            <div className="mb-3 flex gap-2">
              <NumField label="SCORE Q ≥" value={filters.scoreMin} onChange={(v) => setFilter('scoreMin', v)} placeholder="70" />
              <NumField label="SDP ≥ m²" value={filters.sdpMin} onChange={(v) => setFilter('sdpMin', v)} placeholder="800" />
            </div>
            <div className="mb-3 flex gap-2">
              <NumField label="SURFACE ≥" value={filters.surfaceMin} onChange={(v) => setFilter('surfaceMin', v)} placeholder="1 000" />
              <NumField label="SURFACE ≤" value={filters.surfaceMax} onChange={(v) => setFilter('surfaceMax', v)} placeholder="20 000" />
            </div>
            <div className="mb-3 flex flex-col gap-1.5">
              <CheckRow label="Avec événement (BODACC)" on={filters.evenement} toggle={() => setFilter('evenement', !filters.evenement)} />
              <CheckRow label="Vue mer dégagée" on={filters.vueMer} toggle={() => setFilter('vueMer', !filters.vueMer)} />
            </div>
            <label className="font-mono text-[10px] tracking-widest text-txt-dim">FLAGS ACTIFS (au moins un)</label>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {FLAG_DEFS.map((d) => (
                <button key={d.key} onClick={() => toggleFlag(d.key)}
                  className={`rounded-full border px-2 py-0.5 text-[11px] ${
                    filters.flags.includes(d.key) ? 'border-st-creuser text-st-creuser' : 'border-line-2 text-txt-mut'}`}>
                  ⚑ {d.label}
                </button>
              ))}
            </div>
            <button onClick={() => { setFilters(EMPTY_FILTERS); setOpen(false) }}
              className="mt-3 w-full rounded-lg border border-line-2 py-1 text-[11px] text-txt-dim hover:text-txt">
              Réinitialiser tous les filtres
            </button>
          </div>
        </>
      )}
    </div>
  )
}

// Sélecteur de commune — le périmètre n'est plus fixe : les 24 communes + « Toute l'île ».
// Pilote carte, compteurs, liste, modules ; l'état vit dans l'URL (App.tsx).
function CommuneSelect() {
  const { commune, setCommune } = useApp()
  const [open, setOpen] = useState(false)
  const communes = useQuery({ queryKey: ['communes'], queryFn: getCommunes })
  useEffect(() => {
    if (!open) return
    const h = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [open])
  const pick = (c: string | null) => { setCommune(c); setOpen(false) }
  return (
    <div className="relative shrink-0">
      <button onClick={() => setOpen((o) => !o)} data-commune-select
        title="Changer de commune (périmètre de la carte, des compteurs et des modules)"
        className="flex h-[26px] shrink-0 items-center gap-1.5 rounded-full border border-line-2 bg-surface-3 px-3 text-xs text-txt hover:border-[#2E6B4F]">
        <span className="h-1.5 w-1.5 rounded-full bg-mint" />
        {commune ?? 'Toute l’île'}
        <svg viewBox="0 0 10 10" className="h-2.5 w-2.5 text-txt-dim"><polyline points="2,4 5,7 8,4" fill="none" stroke="currentColor" strokeWidth="1.4" /></svg>
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-9 z-20 flex max-h-[70vh] w-[320px] flex-col overflow-y-auto rounded-lg border border-line-2 bg-surface-2 p-1.5 shadow-xl">
            <button onClick={() => pick(null)}
              className={`flex items-center justify-between rounded-md px-3 py-2 text-left text-xs hover:bg-surface-3 ${commune == null ? 'bg-surface-3 text-mint' : 'text-txt'}`}>
              <span className="font-medium">Toute l’île</span>
              <span className="font-mono text-[10px] text-txt-dim">24 communes</span>
            </button>
            <div className="mx-3 my-1 border-t border-line" />
            {(communes.data ?? []).map((c) => (
              <button key={c.insee} onClick={() => pick(c.commune)}
                className={`flex items-center justify-between rounded-md px-3 py-1.5 text-left text-xs hover:bg-surface-3 ${commune === c.commune ? 'bg-surface-3 text-mint' : 'text-txt'}`}>
                <span>{c.commune} <span className="font-mono text-[10px] text-txt-dim">{c.insee}</span></span>
                <span className="font-mono text-[10px]">
                  {c.evaluees === 0
                    ? <span className="text-txt-dim">en calcul…</span>
                    : <span className={c.chaudes > 0 ? 'text-mint' : 'text-txt-dim'}>{c.chaudes} chaude{c.chaudes > 1 ? 's' : ''}</span>}
                </span>
              </button>
            ))}
            {communes.isLoading && <p className="p-3 text-xs text-txt-dim">Chargement…</p>}
          </div>
        </>
      )}
    </div>
  )
}

function FilterChips() {
  const { filters, setFilters } = useApp()
  const chips = activeChips(filters)
  return (
    // RÈGLE (post-régression P0) : « + Filtre » et son popover vivent HORS du conteneur défilant.
    // Un popover absolu DANS un overflow-x-auto est rogné (overflow-y calculé auto) : présent au
    // DOM, invisible à l'utilisateur — le bug exact constaté par Vic. Seuls les chips défilent.
    <div className="flex min-w-0 items-center gap-2">
      <CommuneSelect />
      <div className="flex min-w-0 items-center gap-2 overflow-x-auto" data-chips>
        {chips.map((c) => (
          <span key={c.token} className="flex h-[26px] shrink-0 items-center gap-2 rounded-full border border-line-2 bg-surface-3 px-3 text-xs text-txt">
            {c.label}
            <button onClick={() => setFilters(removeToken(filters, c.token))} className="text-txt-dim hover:text-txt-hi" title="Retirer ce filtre">×</button>
          </span>
        ))}
      </div>
      <AddFilter />
    </div>
  )
}

function VerdictToggle() {
  const { mode, setMode } = useApp()
  return (
    <div className="flex items-center gap-0.5 rounded-lg border border-line-2 bg-surface-2 p-1">
      {(['verdict', 'mutabilite'] as const).map((m) => (
        <button key={m} onClick={() => setMode(m)}
          className={`rounded-md px-3 py-1 text-xs ${m === mode ? 'bg-mint font-medium text-mint-ink' : 'text-txt-mut hover:text-txt'}`}>
          {m === 'verdict' ? 'Verdict' : 'Mutabilité'}
        </button>
      ))}
    </div>
  )
}

function NotifBell() {
  const [open, setOpen] = useState(false)
  const [veilleNom, setVeilleNom] = useState('')
  const qc = useQueryClient()
  const { filters, zone, select, setView } = useApp()
  const ev = useQuery({ queryKey: ['events'], queryFn: getEvents, refetchInterval: 60_000 })
  const veilles = useQuery({ queryKey: ['searches'], queryFn: getSavedSearches, enabled: open })
  const invalidate = () => { qc.invalidateQueries({ queryKey: ['events'] }); qc.invalidateQueries({ queryKey: ['events-count'] }) }
  const readOne = useMutation({ mutationFn: markEventRead, onSuccess: invalidate })
  const readAll = useMutation({ mutationFn: markAllEventsRead, onSuccess: invalidate })
  const addVeille = useMutation({ mutationFn: () => saveSearch(veilleNom, filtersToHash(filters, zone) || '#f=1'),
    onSuccess: () => { setVeilleNom(''); qc.invalidateQueries({ queryKey: ['searches'] }) } })
  const delVeille = useMutation({ mutationFn: deleteSearch, onSuccess: () => qc.invalidateQueries({ queryKey: ['searches'] }) })
  const unread = ev.data?.unread ?? 0
  return (
    <div className="relative">
      <button onClick={() => setOpen((o) => !o)} title="Notifications"
        className="relative flex h-9 w-9 items-center justify-center rounded-full border border-line-2 bg-surface-3 text-txt-mut hover:text-txt">
        <svg viewBox="0 0 20 20" className="h-[18px] w-[18px]">
          <path d="M10 3 a4 4 0 0 1 4 4 v3 l1.5 2.5 h-11 L6 10 V7 a4 4 0 0 1 4-4Z" fill="none" stroke="currentColor" strokeWidth="1.4" />
          <path d="M8.5 15 a1.5 1.5 0 0 0 3 0" fill="none" stroke="currentColor" strokeWidth="1.4" />
        </svg>
        {unread > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-st-ecartee px-1 font-mono text-[9px] font-bold text-white">
            {unread}
          </span>
        )}
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-11 z-20 flex max-h-[70vh] w-[380px] flex-col rounded-lg border border-line-2 bg-surface-2 shadow-xl">
            <div className="flex shrink-0 items-center justify-between border-b border-line px-4 py-2.5">
              <p className="font-mono text-[11px] tracking-widest text-txt-dim">NOTIFICATIONS · {unread} non lue{unread > 1 ? 's' : ''}</p>
              <div className="flex gap-3">
                <a href="/events/digest.html" target="_blank" rel="noreferrer" className="text-[11px] text-mint hover:underline" title="Digest hebdo (HTML email-ready)">Digest →</a>
                {unread > 0 && <button onClick={() => readAll.mutate()} className="text-[11px] text-txt-mut hover:text-txt">tout lire</button>}
              </div>
            </div>
            <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto p-2">
              {(ev.data?.items ?? []).length === 0 && <p className="p-3 text-xs text-txt-dim">Aucun événement — le prochain run de scoring alimentera cette liste.</p>}
              {(ev.data?.items ?? []).map((e) => (
                <div key={e.id} className={`rounded-lg border px-3 py-2 ${e.lu ? 'border-line-2 opacity-55' : 'border-[#3a3050] bg-[#171221]'}`}>
                  <div className="flex items-center gap-2">
                    {e.demo && <span className="rounded-full bg-[#2a2138] px-1.5 py-0.5 text-[8.5px] font-medium text-[#B497F0]" title="Événement de démonstration (run q_v2_demo)">DÉMO</span>}
                    <button onClick={() => { if (e.idu) { setView('cartes'); select(e.idu) } setOpen(false) }}
                      className="min-w-0 flex-1 truncate text-left text-xs text-txt hover:text-txt-hi">{e.titre}</button>
                    {!e.lu && <button onClick={() => readOne.mutate(e.id)} className="shrink-0 text-[10px] text-txt-dim hover:text-mint" title="Marquer lu">✓</button>}
                  </div>
                  {e.detail && <p className="mt-0.5 text-[10px] leading-snug text-txt-dim">{e.detail}</p>}
                  <p className="mt-0.5 font-mono text-[9px] text-txt-dim">{e.date}</p>
                </div>
              ))}
            </div>
            <div className="shrink-0 border-t border-line p-3">
              <p className="font-mono text-[10px] tracking-widest text-txt-dim">VEILLES (recherches sauvegardées)</p>
              {(veilles.data ?? []).map((v) => (
                <div key={v.id} className="mt-1.5 flex items-center gap-2 text-[11px]">
                  <a href={'/socle/' + v.hash} className="min-w-0 flex-1 truncate text-txt hover:text-mint" title={v.hash}>{v.nom}</a>
                  <button onClick={() => delVeille.mutate(v.id)} className="text-txt-dim hover:text-st-ecartee">×</button>
                </div>
              ))}
              <div className="mt-2 flex gap-1.5">
                <input value={veilleNom} onChange={(e) => setVeilleNom(e.target.value)} placeholder="Nommer la recherche courante…"
                  className="min-w-0 flex-1 rounded border border-line-2 bg-surface-3 px-2 py-1 text-[11px] text-txt focus:border-mint focus:outline-none" />
                <button onClick={() => veilleNom.trim() && addVeille.mutate()} disabled={!veilleNom.trim()}
                  className="rounded bg-mint px-2 text-[11px] font-medium text-mint-ink disabled:opacity-40">+ Veille</button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export function Header() {
  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-line bg-bg px-4">
      {/* identité — la buse + wordmark */}
      <div className="flex shrink-0 items-center gap-2 pr-1" title="LABUSE — Radar foncier premium, La Réunion">
        <svg viewBox="0 0 240 82" className="h-4 w-auto" fill="#2FE0A0" style={{ filter: 'drop-shadow(0 0 6px rgba(47,224,160,0.35))' }}>
          <path d="M2 15 C58 10 100 18 120 27 C140 18 182 10 238 15 C202 29 162 40 135 46 C127 49 122 53 120 60 C118 53 113 49 105 46 C78 40 38 29 2 15 Z" />
        </svg>
        <span className="hidden font-display text-sm font-bold tracking-wide text-txt-hi min-[1350px]:inline">LABUSE</span>
      </div>
      <Omnibox />
      <FilterChips />
      <div className="ml-auto flex items-center gap-3">
        <VerdictToggle />
        <NotifBell />
        <span className="flex h-8 w-8 items-center justify-center rounded-full border border-line-2 bg-surface-3 font-mono text-[11px] text-mint">VL</span>
      </div>
    </header>
  )
}
