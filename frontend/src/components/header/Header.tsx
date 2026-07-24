import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { banAutocomplete, deleteSearch, getCommunes, getEvents, getParcelsGeojson, getSavedSearches, markAllEventsRead, markEventRead, parcelAt, saveSearch, searchParcels } from '../../lib/api'
import { filtersToHash } from '../../lib/filters'
import { activeChips, FLAG_DEFS, removeToken, V_SIGNAL_DEFS } from '../../lib/filters'
import { TIER_V2_META, type TierV2 } from '../../lib/status'
import { EMPTY_FILTERS, useApp } from '../../store/useApp'
import { Loading } from '../Loading'

function Omnibox() {
  const { query, setQuery, select, setView, setCommune, commune, setToast } = useApp()
  const ref = useRef<HTMLInputElement>(null)
  const geo = useQuery({ queryKey: ['geojson', commune], queryFn: getParcelsGeojson, enabled: commune != null })
  const communes = useQuery({ queryKey: ['communes'], queryFn: getCommunes })

  // raccourci « / » → focus (le kbd a disparu mais le raccourci reste, pratique)
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

  // A6 (post-revue) + M12-D3 : la barre du HAUT cherche dans TOUT le dashboard :
  //  1) COMMUNE (nom, sans chiffre) → bascule le périmètre ;  2) IDU → ouvre la fiche ;
  //  3) ADRESSE (M12-D3) → géocodage BAN → parcelle contenant le point → ouvre la fiche.
  const onEnter = async () => {
    const raw = query.trim()
    if (!raw) return
    if (!/\d/.test(raw)) {
      const low = raw.toLowerCase()
      const c = (communes.data ?? []).find((x) => x.commune.toLowerCase() === low)
        ?? (raw.length >= 3 ? (communes.data ?? []).find((x) => x.commune.toLowerCase().startsWith(low)) : undefined)
      if (c) { setCommune(c.commune); setView('cartes'); return }
    }
    const qn = raw.toUpperCase().replace(/\s+/g, '')
    const hit = geo.data?.features.find((f) => {
      const idu = String(f.properties?.idu ?? '').toUpperCase()
      return idu.includes(qn) || idu.slice(8).includes(qn)
    })
    if (hit) { setView('cartes'); select(String(hit.properties?.idu)); return }
    // un IDU est unique à l'échelle de l'île : la recherche parcelle IGNORE le périmètre
    // commune actif (sinon : no-op silencieux dès que la parcelle est ailleurs).
    const remote = await searchParcels(qn, { ileEntiere: true }).catch(() => [])
    if (remote[0]) { setView('cartes'); select(remote[0].idu); return }
    // M12-D3 — 3e entrée : une ADRESSE (contient un chiffre + du texte). On géocode via la BAN
    // puis on cherche la parcelle CONTENANT le point (parcels/at). Landing sur la fiche.
    if (/[a-zA-Zà-ÿ]/.test(raw)) {
      const feats = await banAutocomplete(raw).catch(() => [])
      if (feats[0]) {
        const at = await parcelAt(feats[0].lon, feats[0].lat).catch(() => null)
        if (at?.idu) { setView('cartes'); select(at.idu); return }
        setToast(`« ${feats[0].label} » géocodée, mais aucune parcelle en base à ce point.`)
        return
      }
    }
    // jamais de no-op muet : dire à l'utilisateur que la recherche n'a rien donné
    setToast(`Aucune commune, parcelle ni adresse trouvée pour « ${raw} »`)
  }

  return (
    <div className="flex h-8 w-[360px] items-center gap-2 rounded-lg border border-line-2 bg-surface-3 pl-3 pr-0.5 transition-colors duration-quick focus-within:border-mint">
      <input ref={ref} data-omnibox value={query} onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && onEnter()}
        placeholder="Rechercher : commune · IDU (AB 0234) · adresse…"
        title="Recherche du dashboard : une commune (bascule le périmètre), un IDU (ouvre la fiche) ou une adresse (géocodage → parcelle)"
        className="min-w-0 flex-1 bg-transparent text-xs text-txt placeholder:text-txt-mut focus:outline-none" />
      {/* A5 (post-revue) : la LOUPE remplace le « / » et passe à DROITE — cliquable pour lancer */}
      <button onClick={onEnter} title="Lancer la recherche" aria-label="Lancer la recherche"
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-mint text-mint-ink transition-[filter] duration-quick hover:brightness-110">
        <svg viewBox="0 0 20 20" className="h-[15px] w-[15px]">
          <circle cx="9" cy="9" r="5.5" fill="none" stroke="currentColor" strokeWidth="2" />
          <line x1="13" y1="13" x2="17.5" y2="17.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </button>
    </div>
  )
}

function NumField({ label, value, onChange, placeholder }: {
  label: string; value: number | null; onChange: (v: number | null) => void; placeholder: string
}) {
  return (
    <div className="min-w-0 flex-1">
      <label className="label-caps block">{label}</label>
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

// Popover d'ajout de filtre — filtres MÉTIER combinables (M5.1 : tiers v2 multi, plages,
// booléens, flags, signaux propriétaire). Le tier v1.3 « 🔥 » et les bandes V ont disparu.
function AddFilter() {
  const { filters, setFilter, setFilters } = useApp()
  const [open, setOpen] = useState(false)
  const TIERS: TierV2[] = ['brulante', 'chaude', 'reserve_fonciere', 'a_creuser', 'ecartee']
  useEffect(() => {
    if (!open) return
    const h = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [open])
  const toggleTier = (t: TierV2) =>
    setFilter('tiers', filters.tiers.includes(t) ? filters.tiers.filter((x) => x !== t) : [...filters.tiers, t])
  const toggleFlag = (k: string) =>
    setFilter('flags', filters.flags.includes(k) ? filters.flags.filter((x) => x !== k) : [...filters.flags, k])
  const toggleVSignal = (k: string) =>
    setFilter('vSignals', filters.vSignals.includes(k) ? filters.vSignals.filter((x) => x !== k) : [...filters.vSignals, k])
  return (
    <div className="relative">
      <button onClick={() => setOpen((o) => !o)}
        className={`flex h-[26px] shrink-0 items-center gap-1 rounded-full border border-dashed px-3 text-xs ${
          open ? 'border-mint text-mint' : 'border-line-2 text-txt-mut hover:text-txt'}`}>+ Filtre</button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="floating absolute left-0 top-9 z-20 w-[300px] p-4">
            <label className="label-caps block">Verdict · Scoring v2 (multi)</label>
            <div className="mb-3 mt-1.5 flex flex-wrap gap-1.5">
              {TIERS.map((t) => (
                <button key={t} onClick={() => toggleTier(t)}
                  title={t === 'ecartee' ? 'Exclusions dures de l\'étage 0 (run servi)' : undefined}
                  className={`rounded-full border px-2 py-0.5 text-[11px] ${
                    filters.tiers.includes(t) ? 'border-mint text-txt-hi' : 'border-line-2 text-txt-mut'}`}>
                  <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full" style={{ background: TIER_V2_META[t].color }} />
                  {TIER_V2_META[t].label}
                </button>
              ))}
            </div>
            {/* E1 (M12) : « Score Q » et « SDP » renommés en langage client (cohérent B1).
                SDP exclut silencieusement les parcelles sans surface résiduelle mesurée (A5) —
                dit dans le title. */}
            <div className="mb-3 flex gap-2">
              <NumField label="POTENTIEL ≥ /100" value={filters.scoreMin} onChange={(v) => setFilter('scoreMin', v)} placeholder="70" />
              <NumField label="SURF. CONSTR. ≥ m²" value={filters.sdpMin} onChange={(v) => setFilter('sdpMin', v)} placeholder="800" />
            </div>
            <div className="mb-3 flex gap-2">
              <NumField label="SURFACE ≥" value={filters.surfaceMin} onChange={(v) => setFilter('surfaceMin', v)} placeholder="1 000" />
              <NumField label="SURFACE ≤" value={filters.surfaceMax} onChange={(v) => setFilter('surfaceMax', v)} placeholder="20 000" />
            </div>
            <div className="mb-3 flex flex-col gap-1.5">
              <CheckRow label="Avec événement (BODACC)" on={filters.evenement} toggle={() => setFilter('evenement', !filters.evenement)} />
              <CheckRow label="Veille succession" on={filters.veille} toggle={() => setFilter('veille', !filters.veille)} />
              <CheckRow label="Masquer les copropriétés" on={filters.horsCopro} toggle={() => setFilter('horsCopro', !filters.horsCopro)} />
            </div>
            <label className="label-caps block">Flags actifs (au moins un)</label>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {FLAG_DEFS.map((d) => (
                <button key={d.key} onClick={() => toggleFlag(d.key)}
                  className={`rounded-full border px-2 py-0.5 text-[11px] ${
                    filters.flags.includes(d.key) ? 'border-st-creuser text-st-creuser' : 'border-line-2 text-txt-mut'}`}>
                  ⚑ {d.label}
                </button>
              ))}
            </div>
            {/* Signaux propriétaire (dossier de la fiche) — libellés métier, au moins un présent */}
            <label className="label-caps mt-3 block">Signaux propriétaire</label>
            {/* E1 (M12) : « Dirigeant 65+ » MASQUÉ — audit A5, les codes RNE_DIRIGEANT_* sont
                absents des données (0 résultat sur le run servi). Le code du filtre reste
                (V_SIGNAL_DEFS, R1 : masquer ≠ supprimer) ; il réapparaîtra dès le backfill du signal. */}
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {V_SIGNAL_DEFS.filter((d) => d.key !== 'dirigeant').map((d) => (
                <button key={d.key} onClick={() => toggleVSignal(d.key)}
                  className={`rounded-full border px-2 py-0.5 text-[11px] ${
                    filters.vSignals.includes(d.key) ? 'border-st-creuser text-st-creuser' : 'border-line-2 text-txt-mut'}`}
                  title={`Au moins un signal « ${d.label} » au dossier propriétaire`}>
                  {d.label}
                </button>
              ))}
            </div>
            <button onClick={() => { setFilters(EMPTY_FILTERS); setOpen(false) }}
              className="mt-3 min-h-7 w-full rounded-lg border border-line-2 py-1 text-[11px] text-txt-dim transition-colors duration-quick hover:text-txt">
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
  const { commune, setCommune, setContexteCommune } = useApp()
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
        className="flex h-[26px] shrink-0 items-center gap-1.5 rounded-full border border-line-2 bg-surface-3 px-3 text-xs text-txt transition-colors duration-quick hover:border-mint/40">
        <span className="h-1.5 w-1.5 rounded-full bg-txt-dim" />
        {commune ?? 'Toute l’île'}
        <svg viewBox="0 0 10 10" className="h-2.5 w-2.5 text-txt-dim"><polyline points="2,4 5,7 8,4" fill="none" stroke="currentColor" strokeWidth="1.4" /></svg>
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="floating absolute left-0 top-9 z-20 flex max-h-[70vh] w-[320px] flex-col overflow-y-auto p-1.5">
            <button onClick={() => pick(null)}
              className={`flex items-center justify-between rounded-md px-3 py-2 text-left text-xs hover:bg-surface-3 ${commune == null ? 'bg-surface-3 text-mint' : 'text-txt'}`}>
              <span className="font-medium">Toute l’île</span>
              <span className="font-mono text-[11px] text-txt-dim">24 communes</span>
            </button>
            <div className="mx-3 my-1 border-t border-line" />
            {/* VUES item 6 (12/07) : les « N chaudes » par ligne disparaissent (bruit de
                vente dans un simple sélecteur de périmètre) ; le ⓘ devient un lien explicite
                « voir la fiche commune → » — même action (volet contexte SRU/ANRU/PLH/marché). */}
            {(communes.data ?? []).map((c) => (
              <div key={c.insee} className={`flex items-center rounded-md hover:bg-surface-3 ${commune === c.commune ? 'bg-surface-3' : ''}`}>
                <button onClick={() => pick(c.commune)}
                  className={`min-w-0 flex-1 px-3 py-1.5 text-left text-xs ${commune === c.commune ? 'text-mint' : 'text-txt'}`}>
                  {c.commune} <span className="font-mono text-[11px] text-txt-dim">{c.insee}</span>
                </button>
                <button data-fiche-commune onClick={() => { setContexteCommune(c.commune); setOpen(false) }}
                  className="shrink-0 whitespace-nowrap px-3 py-1.5 text-[11px] text-txt-dim hover:text-mint"
                  title={`Fiche de ${c.commune} — SRU, ANRU, PLH, marché logement (sources officielles)`}>
                  voir la fiche commune →
                </button>
              </div>
            ))}
            {communes.isLoading && <div className="p-3"><Loading label="Chargement des communes" className="text-xs" /></div>}
          </div>
        </>
      )}
    </div>
  )
}

// bouton CONTEXTE — visible quand une commune est active : le volet SRU/ANRU/PLH/marché
function ContexteButton() {
  const { commune, setContexteCommune } = useApp()
  if (!commune) return null
  return (
    <button onClick={() => setContexteCommune(commune)} data-contexte-btn
      className="flex h-[26px] shrink-0 items-center gap-1 rounded-full border border-violet/40 bg-violet/[0.08] px-2.5 text-[11px] text-violet transition-colors duration-quick hover:border-violet"
      title="Contexte commune — SRU, ANRU, PLH, marché logement (sources officielles)">
      ⓘ Contexte
    </button>
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
      <ContexteButton />
      <div className="flex min-w-0 items-center gap-2 overflow-x-auto" data-chips>
        {chips.map((c) => (
          <span key={c.token} className="flex h-[26px] shrink-0 items-center gap-1 rounded-full border border-line-2 bg-surface-3 pl-3 pr-1 text-xs text-txt">
            {c.label}
            <button onClick={() => setFilters(removeToken(filters, c.token))}
              className="flex h-5 w-5 items-center justify-center rounded-full text-txt-dim transition-colors duration-quick hover:bg-surface-2 hover:text-txt-hi"
              title="Retirer ce filtre" aria-label={`Retirer le filtre ${c.label}`}>×</button>
          </span>
        ))}
      </div>
      <AddFilter />
    </div>
  )
}

// M9 lot 4 : le toggle carte « Verdict / Mutabilité » est RETIRÉ. Le potentiel de
// transformation (fond de l'ancien mode Mutabilité) vit désormais dans la fiche, à la
// parcelle (bloc « Potentiel de transformation »), alimenté par le ratio SDP consommée/
// autorisée du bloc D + le signal surélévation. Cf. reports/m9-fiche/SYNTHESE-M9.md.

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
      <button onClick={() => setOpen((o) => !o)} title="Notifications" aria-label="Notifications"
        className="relative flex h-9 w-9 items-center justify-center rounded-full border border-line-2 bg-surface-3 text-txt-mut transition-colors duration-quick hover:text-txt">
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
          <div className="floating absolute right-0 top-11 z-20 flex max-h-[70vh] w-[380px] flex-col overflow-hidden">
            <div className="flex shrink-0 items-center justify-between border-b border-line px-4 py-2.5">
              <p className="label-caps">Notifications · {unread} non lue{unread > 1 ? 's' : ''}</p>
              <div className="flex gap-3">
                <a href="/events/digest.html" target="_blank" rel="noreferrer" className="text-[11px] text-mint hover:underline" title="Digest hebdo (HTML email-ready)">Digest →</a>
                {unread > 0 && <button onClick={() => readAll.mutate()} className="text-[11px] text-txt-mut hover:text-txt">tout lire</button>}
              </div>
            </div>
            <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto p-2">
              {(ev.data?.items ?? []).length === 0 && <p className="p-3 text-xs text-txt-dim">Aucun événement — le prochain run de scoring alimentera cette liste.</p>}
              {(ev.data?.items ?? []).map((e) => (
                <div key={e.id} className={`rounded-lg border px-3 py-2 ${e.lu ? 'border-line-2 opacity-55' : 'border-violet/30 bg-violet/[0.07]'}`}>
                  <div className="flex items-center gap-2">
                    {e.demo && <span className="rounded-full bg-violet/15 px-1.5 py-0.5 text-[8.5px] font-medium text-violet" title="Événement de démonstration (run q_v2_demo)">DÉMO</span>}
                    <button onClick={() => { if (e.idu) { setView('cartes'); select(e.idu) } setOpen(false) }}
                      className="min-w-0 flex-1 truncate text-left text-xs text-txt hover:text-txt-hi">{e.titre}</button>
                    {!e.lu && <button onClick={() => readOne.mutate(e.id)} className="shrink-0 text-[11px] text-txt-dim hover:text-mint" title="Marquer lu" aria-label="Marquer comme lu">✓</button>}
                  </div>
                  {e.detail && <p className="mt-0.5 text-[11px] leading-snug text-txt-dim">{e.detail}</p>}
                  <p className="mt-0.5 font-mono text-[9px] text-txt-dim">{e.date}</p>
                </div>
              ))}
            </div>
            <div className="shrink-0 border-t border-line p-3">
              <p className="label-caps">Veilles (recherches sauvegardées)</p>
              {(veilles.data ?? []).map((v) => (
                <div key={v.id} className="mt-1.5 flex items-center gap-2 text-[11px]">
                  <a href={'/socle/' + v.hash} className="min-w-0 flex-1 truncate text-txt hover:text-mint" title={v.hash}>{v.nom}</a>
                  <button onClick={() => delVeille.mutate(v.id)} aria-label="Supprimer la veille"
                  className="flex h-5 w-5 items-center justify-center rounded-full text-txt-dim transition-colors duration-quick hover:bg-surface-3 hover:text-st-ecartee">×</button>
                </div>
              ))}
              <div className="mt-2 flex gap-1.5">
                <input value={veilleNom} onChange={(e) => setVeilleNom(e.target.value)} placeholder="Nommer la recherche courante…"
                  className="min-w-0 flex-1 rounded border border-line-2 bg-surface-3 px-2 py-1 text-[11px] text-txt focus:border-mint focus:outline-none" />
                <button onClick={() => veilleNom.trim() && addVeille.mutate()} disabled={!veilleNom.trim()}
                  className="rounded bg-mint px-2 text-[11px] font-medium text-mint-ink transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">+ Veille</button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export function Header() {
  // M12-D4 : « Scorer une adresse » a quitté l'en-tête pour le tiroir Outils (registry).
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
        <NotifBell />
        <span className="flex h-8 w-8 items-center justify-center rounded-full border border-line-2 bg-surface-3 font-mono text-[11px] text-mint">VL</span>
      </div>
    </header>
  )
}
