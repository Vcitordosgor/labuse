import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { banAutocomplete, deleteLogo, deleteSearch, getCommunes, getEvents, getMarque, getMoi, getParcelsGeojson, getSavedSearches, markAllEventsRead, markEventRead, parcelAt, postLogo, postMarque, postSuggestion, saveSearch, searchParcels, veilleNL } from '../../lib/api'
import { filtersToHash } from '../../lib/filters'
import { EMPTY_FILTERS, useApp } from '../../store/useApp'
import { AddressAutocomplete, type AddressSelection } from '../AddressAutocomplete'

function Omnibox() {
  const { select, setView, setCommune, commune, setToast } = useApp()
  const geo = useQuery({ queryKey: ['geojson', commune], queryFn: getParcelsGeojson, enabled: commune != null })
  const communes = useQuery({ queryKey: ['communes'], queryFn: getCommunes })
  // M55-B point 3 : la recherche « lancée » (loupe ou Entrée sans suggestion) doit se VOIR —
  // spinner sobre dans le bouton pendant la résolution ; l'état vide reste le toast honnête.
  const [searching, setSearching] = useState(false)

  // raccourci « / » → focus de l'omnibox (le kbd a disparu mais le raccourci reste, pratique)
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault()
        document.querySelector<HTMLInputElement>('[data-omnibox]')?.focus()
      }
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [])

  // M13-B1 : la barre du HAUT est désormais une VRAIE autocomplétion d'adresse (source interne
  // /adresses/autocomplete). Choisir une suggestion → atterrissage DIRECT sur la parcelle
  // (l'idu accompagne la suggestion ; repli parcelAt si absent). Le champ reste polyvalent :
  // Entrée SANS suggestion sélectionnée retombe sur la recherche COMMUNE puis IDU (onEnterRaw).

  // atterrissage à partir d'une suggestion d'adresse choisie
  const onPickAddress = async (sel: AddressSelection) => {
    if (sel.idu) { setView('cartes'); select(sel.idu); return }
    const at = await parcelAt(sel.lon, sel.lat).catch(() => null)
    if (at?.idu) { setView('cartes'); select(at.idu); return }
    setToast(`« ${sel.label} » localisée, mais aucune parcelle en base à ce point.`)
  }

  // Entrée sans suggestion : COMMUNE (nom sans chiffre) → périmètre ; sinon IDU → fiche ;
  // en dernier ressort, une adresse libre est géocodée via la 1re suggestion interne.
  const onEnterRaw = async (raw: string) => {
    if (!raw) return
    setSearching(true)
    try {
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
      const remote = await searchParcels(qn, { ileEntiere: true }).catch(() => [])
      if (remote[0]) { setView('cartes'); select(remote[0].idu); return }
      // adresse libre → 1re suggestion interne
      if (/[a-zA-Zà-ÿ]/.test(raw)) {
        const feats = await banAutocomplete(raw).catch(() => [])
        if (feats[0]) { await onPickAddress({ label: feats[0].label, lon: feats[0].lon, lat: feats[0].lat, idu: feats[0].idu }); return }
      }
      setToast(`Aucune commune, parcelle ni adresse trouvée pour « ${raw} »`)
    } finally {
      setSearching(false)
    }
  }

  return (
    <div className="flex h-8 w-[360px] items-center gap-2 rounded-lg border border-line-2 bg-surface-3 pl-3 pr-0.5 transition-colors duration-quick focus-within:border-mint">
      <AddressAutocomplete
        data-omnibox
        onSelect={onPickAddress}
        onEnterRaw={onEnterRaw}
        placeholder="Rechercher : IDU, adresse exacte…"
        className="w-full min-w-0 bg-transparent text-xs text-txt placeholder:text-txt-mut focus:outline-none"
      />
      {/* A5 (post-revue) : la LOUPE cliquable — lance la recherche sur le texte courant.
          M55-B point 3 : pendant la résolution, la loupe devient un spinner sobre (bouton
          désactivé + curseur d'attente) — on VOIT que ça cherche. */}
      <button
        disabled={searching}
        onClick={() => {
          const el = document.querySelector<HTMLInputElement>('[data-omnibox]')
          if (el) onEnterRaw(el.value.trim())
        }}
        title="Lancer la recherche" aria-label="Lancer la recherche" aria-busy={searching}
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-mint text-mint-ink transition-[filter] duration-quick hover:brightness-110 disabled:cursor-wait disabled:brightness-95">
        {searching ? (
          <svg viewBox="0 0 20 20" className="h-[15px] w-[15px] animate-spin" aria-hidden>
            <circle cx="10" cy="10" r="6.5" fill="none" stroke="currentColor" strokeWidth="2" strokeOpacity="0.3" />
            <path d="M10 3.5 a6.5 6.5 0 0 1 6.5 6.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        ) : (
          <svg viewBox="0 0 20 20" className="h-[15px] w-[15px]">
            <circle cx="9" cy="9" r="5.5" fill="none" stroke="currentColor" strokeWidth="2" />
            <line x1="13" y1="13" x2="17.5" y2="17.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        )}
      </button>
    </div>
  )
}

// M55-D stage 3 : AddFilter (popover « Filtres (N) ») + NumField RETIRÉS du header — les filtres
// vivent désormais dans la section repliable « Filtres » du panneau gauche (LeftPanel).

// M55-D stage 9 bloc 3 — « le périmètre PROPOSE, le filtre DISPOSE » : le sélecteur du header
// est RESTAURÉ (mono-commune) — choisir « Saint-Leu » zoome la carte ET pré-coche son CP dans le
// filtre Communes (setCommune : vue + pré-coche) ; le client décoche librement au panneau (la
// carte reste où elle est — sens unique). « Toute l'île » dézoome ET décoche. En MULTI (≥2,
// posé au panneau), le header devient une VUE (« 3 communes ») dont le clic ouvre le panneau.
function CommuneSelect() {
  const { filters, setCommune, openFiltres, setContexteCommune } = useApp()
  const [open, setOpen] = useState(false)
  const communes = useQuery({ queryKey: ['communes'], queryFn: getCommunes })
  useEffect(() => {
    if (!open) return
    const h = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [open])
  const n = filters.communes.length
  const label = n === 0 ? 'Toute l’île' : n === 1 ? filters.communes[0] : `${n} communes`
  if (n >= 2) {
    return (
      <button onClick={openFiltres} data-commune-select
        title="Plusieurs communes filtrées — se règle dans Filtres › Communes (ouvre le panneau)"
        className="flex h-[26px] shrink-0 items-center gap-1.5 rounded-full border border-line-2 bg-surface-3 px-3 text-xs text-txt transition-colors duration-quick hover:border-mint/40">
        <span className="h-1.5 w-1.5 rounded-full bg-mint" />
        {label}
      </button>
    )
  }
  const pick = (c: string | null) => { setCommune(c); setOpen(false) }
  return (
    <div className="relative shrink-0">
      <button onClick={() => setOpen((o) => !o)} data-commune-select
        title="Périmètre — zoome la carte et pré-coche la commune dans le filtre (vous gardez la main)"
        className="flex h-[26px] shrink-0 items-center gap-1.5 rounded-full border border-line-2 bg-surface-3 px-3 text-xs text-txt transition-colors duration-quick hover:border-mint/40">
        <span className={`h-1.5 w-1.5 rounded-full ${n > 0 ? 'bg-mint' : 'bg-txt-dim'}`} />
        {label}
        <svg viewBox="0 0 10 10" className="h-2.5 w-2.5 text-txt-dim"><polyline points="2,4 5,7 8,4" fill="none" stroke="currentColor" strokeWidth="1.4" /></svg>
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="floating absolute left-0 top-9 z-20 flex max-h-[70vh] w-[240px] flex-col overflow-y-auto p-1.5">
            <button onClick={() => pick(null)}
              className={`rounded-md px-3 py-2 text-left text-xs hover:bg-surface-3 ${n === 0 ? 'bg-surface-3 text-mint' : 'text-txt'}`}>
              Toute l’île
            </button>
            <div className="mx-3 my-1 border-t border-line" />
            {/* M55-D stage 9 ter point 2 : chaque ligne porte à droite un « ⓘ » — le NOM
                sélectionne (zoom + pré-coche, bloc 3 inchangé), le « ⓘ » ouvre la fiche de CETTE
                commune SANS changer le périmètre (stopPropagation, zone de clic 28 px). */}
            {(communes.data ?? []).map((c) => (
              <div key={c.insee} className="flex items-center rounded-md hover:bg-surface-3">
                <button onClick={() => pick(c.commune)}
                  className={`min-w-0 flex-1 px-3 py-1.5 text-left text-xs ${filters.communes.includes(c.commune) ? 'text-mint' : 'text-txt'}`}>
                  {c.commune} <span className="font-mono text-[11px] text-txt-dim">{c.insee}</span>
                </button>
                <button data-fiche-commune onClick={(e) => { e.stopPropagation(); setContexteCommune(c.commune); setOpen(false) }}
                  title={`Fiche de ${c.commune} — SRU, ANRU, PLH, marché logement (n'affecte pas le périmètre)`}
                  aria-label={`Fiche commune de ${c.commune}`}
                  className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[12px] text-txt-dim transition-colors duration-quick hover:bg-surface-2 hover:text-mint">
                  ⓘ
                </button>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

// bouton CONTEXTE — visible quand une commune est active : le volet SRU/ANRU/PLH/marché
function ContexteButton() {
  const { commune, focusCommune } = useApp()
  if (!commune) return null
  return (
    <button onClick={() => focusCommune(commune)} data-contexte-btn
      className="flex h-[26px] shrink-0 items-center gap-1 rounded-full border border-violet/40 bg-violet/[0.08] px-2.5 text-[11px] text-violet transition-colors duration-quick hover:border-violet"
      title="Contexte commune — SRU, ANRU, PLH, marché logement (sources officielles)">
      ⓘ Contexte
    </button>
  )
}

// M55-D stage 3 : le header ne porte PLUS aucun filtre — le bouton « Filtres (N) » et les chips
// ont rejoint la section repliable « Filtres » du panneau gauche. Ne restent que le périmètre
// (commune) et le contexte commune, qui ne sont pas des filtres.
function FilterChips() {
  return (
    <div className="flex min-w-0 items-center gap-2">
      <CommuneSelect />
      <ContexteButton />
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
  const [nlText, setNlText] = useState('')          // M17-B : saisie veille en langage naturel
  const [nlResume, setNlResume] = useState<string | null>(null)
  const [nlRefus, setNlRefus] = useState<string | null>(null)
  const qc = useQueryClient()
  const { filters, zone, select, setView, setFilters } = useApp()
  const ev = useQuery({ queryKey: ['events'], queryFn: getEvents, refetchInterval: 60_000 })
  const veilles = useQuery({ queryKey: ['searches'], queryFn: getSavedSearches, enabled: open })
  const invalidate = () => { qc.invalidateQueries({ queryKey: ['events'] }); qc.invalidateQueries({ queryKey: ['events-count'] }) }
  const readOne = useMutation({ mutationFn: markEventRead, onSuccess: invalidate })
  const readAll = useMutation({ mutationFn: markAllEventsRead, onSuccess: invalidate })
  const addVeille = useMutation({ mutationFn: () => saveSearch(veilleNom, filtersToHash(filters, zone) || '#f=1'),
    onSuccess: () => { setVeilleNom(''); qc.invalidateQueries({ queryKey: ['searches'] }) } })
  const delVeille = useMutation({ mutationFn: deleteSearch, onSuccess: () => qc.invalidateQueries({ queryKey: ['searches'] }) })
  // M17-B : traduction NL → filtres VISIBLES (setFilters) OU refus honnête si non déclenchable
  const nlVeille = useMutation({
    mutationFn: () => veilleNL(nlText),
    onSuccess: (r) => {
      if (r.ok && r.filters) {
        setFilters({ ...EMPTY_FILTERS, ...(r.filters as Partial<typeof EMPTY_FILTERS>) })
        setVeilleNom(nlText.trim().slice(0, 80))
        setNlResume(r.resume ?? null); setNlRefus(null)
      } else {
        setNlRefus(r.refus ?? 'Veille non déclenchable.'); setNlResume(null)
      }
    },
  })
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
              {/* M16-B5 : plus d'incohérence « 0 non lue » sur liste pleine — « à jour » quand tout est lu */}
              <p className="label-caps">Notifications{unread > 0 ? ` · ${unread} non lue${unread > 1 ? 's' : ''}` : (ev.data?.items ?? []).length ? ' · à jour' : ''}</p>
              <div className="flex gap-3">
                {/* M16-B2 : « Digest » (jargon) → « Le point de la semaine » */}
                <a href="/events/digest.html" target="_blank" rel="noreferrer" className="text-[11px] text-mint hover:underline" title="Récapitulatif hebdomadaire (ce qui a bougé + top chaudes)">Le point de la semaine →</a>
                {unread > 0 && <button onClick={() => readAll.mutate()} className="text-[11px] text-txt-mut hover:text-txt">tout lire</button>}
              </div>
            </div>
            {/* M16-B1 : intro — ne décrit QUE les déclencheurs RÉELS (audit A1/A5) */}
            <div className="shrink-0 border-b border-line bg-surface-2 px-4 py-2 text-[10.5px] leading-snug text-txt-mut">
              Les <b className="text-txt">changements sur les parcelles que vous suivez</b> — bascule de
              statut, procédure BODACC, permis neuf à proximité — et les <b className="text-txt">alertes de
              vos veilles</b>. On ne vous prévient que sur ce qu'on sait réellement détecter.
            </div>
            <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto p-2">
              {(ev.data?.items ?? []).length === 0 && <p className="p-3 text-xs leading-snug text-txt-dim">Aucune notification pour l'instant — nous vous préviendrons dès qu'une parcelle suivie change ou qu'une de vos veilles se déclenche.</p>}
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
              {/* M16-B3 : « veilles » = alerte par filtres (fonctionnel) — renommé + expliqué */}
              <p className="label-caps">Vos veilles — alertes sur mesure</p>
              <p className="mt-0.5 text-[10.5px] leading-snug text-txt-dim">Enregistrez une recherche : on vous alerte dès qu'une parcelle <b>bascule</b> et correspond à vos critères.</p>
              {/* M17-B : décrire sa veille en français → filtres VISIBLES (ci-contre) ou refus honnête */}
              <div className="mt-2 flex gap-1.5">
                <input data-nl-veille value={nlText}
                  onChange={(e) => { setNlText(e.target.value); setNlRefus(null) }}
                  onKeyDown={(e) => { if (e.key === 'Enter' && nlText.trim().length >= 3) nlVeille.mutate() }}
                  placeholder="Décrivez : « les grandes parcelles à Saint-Paul qui deviennent chaudes »"
                  className="min-w-0 flex-1 rounded border border-line-2 bg-surface-3 px-2 py-1 text-[11px] text-txt focus:border-mint focus:outline-none" />
                <button data-nl-go onClick={() => nlText.trim().length >= 3 && nlVeille.mutate()} disabled={nlText.trim().length < 3 || nlVeille.isPending}
                  className="shrink-0 rounded border border-mint/50 px-2 text-[11px] text-mint transition-colors duration-quick hover:bg-mint/10 disabled:opacity-40">
                  {nlVeille.isPending ? '…' : 'Traduire'}</button>
              </div>
              {nlResume && (
                <p data-nl-resume className="mt-1 rounded-md border border-mint/40 bg-mint/[0.07] px-2 py-1 text-[10.5px] leading-snug text-mint">
                  ✓ {nlResume} <span className="text-txt-dim">— vérifiez/ajustez les filtres, puis « + Veille ».</span>
                </p>
              )}
              {nlRefus && (
                <p data-nl-refus className="mt-1 rounded-md border border-st-creuser/40 bg-st-creuser/10 px-2 py-1 text-[10.5px] leading-snug text-st-creuser">{nlRefus}</p>
              )}
              {(veilles.data ?? []).map((v) => (
                <div key={v.id} className="mt-1.5 flex items-center gap-2 text-[11px]">
                  <a href={'/socle/' + v.hash} className="min-w-0 flex-1 truncate text-txt hover:text-mint" title={v.hash}>{v.nom}</a>
                  <button onClick={() => delVeille.mutate(v.id)} aria-label="Supprimer la veille"
                  className="flex h-5 w-5 items-center justify-center rounded-full text-txt-dim transition-colors duration-quick hover:bg-surface-3 hover:text-st-ecartee">×</button>
                </div>
              ))}
              {/* M16-B4 : exemples de veilles UTILES = déclencheurs RÉELS (audit A5). Un clic pré-remplit
                  filtres + nom ; l'utilisateur nomme et « + Veille » enregistre. Aucune fausse saisie qui
                  ne déclencherait rien (pas de « changement de PLU » / « permis abandonné » : non détectables). */}
              <div className="mt-2 flex flex-wrap items-center gap-1">
                <span className="text-[10px] text-txt-dim">Suivre, par exemple :</span>
                <button data-veille-ex onClick={() => { setFilters({ ...EMPTY_FILTERS, tiers: ['chaude'] }); setVeilleNom('Parcelles qui basculent en chaude') }}
                  className="rounded-full border border-line-2 px-2 py-0.5 text-[10px] text-txt-mut transition-colors duration-quick hover:border-mint hover:text-mint">parcelles qui deviennent chaudes</button>
                <button data-veille-ex onClick={() => { setFilters({ ...EMPTY_FILTERS, evenement: true }); setVeilleNom('Nouvelles procédures BODACC') }}
                  className="rounded-full border border-line-2 px-2 py-0.5 text-[10px] text-txt-mut transition-colors duration-quick hover:border-mint hover:text-mint">nouvelle procédure BODACC</button>
              </div>
              <div className="mt-1.5 flex gap-1.5">
                <input value={veilleNom} onChange={(e) => setVeilleNom(e.target.value)} placeholder="Nommez cette veille…"
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

/** M16-C — formulaire « proposer une amélioration » : court, proche, destination RÉELLE (table
 *  `suggestions`, consultable par `labuse suggestions`). Aucun e-mail (pas d'infra e-mail, audit A3). */
function SuggestionForm({ onDone }: { onDone: () => void }) {
  const [cat, setCat] = useState('idee')
  const [texte, setTexte] = useState('')
  const [sent, setSent] = useState(false)
  const send = useMutation({
    mutationFn: () => postSuggestion({ categorie: cat, texte, contexte: (typeof location !== 'undefined' ? location.hash || location.pathname : '') }),
    onSuccess: () => setSent(true),
  })
  if (sent) return (
    <div data-sugg-ok className="p-4 text-center">
      <p className="text-sm font-medium text-mint">✓ Merci, c'est noté.</p>
      <p className="mt-1 text-[11px] leading-snug text-txt-mut">Votre retour est bien arrivé — on le lit vraiment.</p>
      <button onClick={onDone} className="mt-3 text-[11px] text-txt-mut hover:text-txt">Fermer</button>
    </div>
  )
  return (
    <div className="flex flex-col gap-2 p-3">
      <p className="text-[11px] leading-snug text-txt-mut">Une idée, un bug, un manque ? Dites-le en une phrase — ça compte vraiment pour la suite.</p>
      <div className="flex gap-1">
        {([['idee', 'Idée'], ['bug', 'Bug'], ['autre', 'Autre']] as const).map(([k, l]) => (
          <button key={k} data-sugg-cat={k} onClick={() => setCat(k)}
            className={`flex-1 rounded border py-1 text-[11px] transition-colors duration-quick ${cat === k ? 'border-mint text-mint' : 'border-line-2 text-txt-mut hover:text-txt'}`}>{l}</button>
        ))}
      </div>
      <textarea data-sugg-texte value={texte} onChange={(e) => setTexte(e.target.value)} rows={4} autoFocus
        placeholder="Votre suggestion…"
        className="rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 text-[11px] leading-snug text-txt focus:border-mint focus:outline-none" />
      <div className="flex gap-2">
        <button onClick={onDone} className="rounded-lg border border-line-2 px-3 py-1.5 text-[11px] text-txt-mut transition-colors duration-quick hover:text-txt">Annuler</button>
        <button data-sugg-send onClick={() => texte.trim().length >= 3 && send.mutate()} disabled={texte.trim().length < 3 || send.isPending}
          className="flex-1 rounded-lg bg-mint py-1.5 text-[11px] font-medium text-mint-ink transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
          {send.isPending ? 'Envoi…' : 'Envoyer'}</button>
      </div>
      {send.isError && <p className="text-[10.5px] text-st-ecartee">Échec de l'envoi — réessayez.</p>}
    </div>
  )
}

/** M54-EXPO-2 A6 — widget marque blanche : logo (upload body brut ≤512 Ko png/jpg/svg) + 3
 *  libellés. GET /moi/marque préremplit et prévisualise ; les documents brandés (dossier,
 *  briques…) portent déjà cette marque côté générateurs — on ne l'ajoute nulle part ailleurs. */
function MarqueForm() {
  const qc = useQueryClient()
  const m = useQuery({ queryKey: ['marque'], queryFn: getMarque })
  const [rs, setRs] = useState<string | null>(null)
  const [co, setCo] = useState<string | null>(null)
  const [me, setMe] = useState<string | null>(null)
  const d = m.data
  // valeurs affichées = édition locale si commencée, sinon la valeur serveur relue
  const vRs = rs ?? d?.raison_sociale ?? ''
  const vCo = co ?? d?.coordonnees ?? ''
  const vMe = me ?? d?.mention ?? ''
  const inval = () => qc.invalidateQueries({ queryKey: ['marque'] })
  const upLogo = useMutation({ mutationFn: (f: File) => postLogo(f), onSuccess: inval })
  const delLogo = useMutation({ mutationFn: () => deleteLogo(), onSuccess: inval })
  const save = useMutation({ mutationFn: () => postMarque({ raison_sociale: vRs, coordonnees: vCo, mention: vMe }), onSuccess: () => { inval(); setRs(null); setCo(null); setMe(null) } })
  const field = 'w-full rounded-md border border-line-2 bg-surface-3 px-2 py-1.5 text-[12px] text-txt placeholder:text-txt-dim'
  return (
    <div data-marque-form className="flex flex-col gap-2 p-3 text-[12px]">
      <div className="flex items-center gap-3">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-md border border-line-2 bg-surface-3">
          {d?.logo_data_uri ? <img data-marque-logo src={d.logo_data_uri} alt="logo" className="max-h-full max-w-full" /> : <span className="text-[9px] text-txt-dim">logo</span>}
        </div>
        <div className="flex flex-col gap-1">
          <label className="cursor-pointer text-[11px] text-mint hover:underline">
            {upLogo.isPending ? 'Envoi…' : d?.has_logo ? 'Remplacer le logo' : 'Ajouter un logo'}
            <input type="file" accept="image/png,image/jpeg,image/svg+xml" className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) upLogo.mutate(f) }} />
          </label>
          {d?.has_logo && <button onClick={() => delLogo.mutate()} className="text-left text-[10.5px] text-txt-dim hover:text-st-ecartee">Retirer</button>}
          <span className="text-[9.5px] text-txt-dim">png/jpg/svg · ≤ 512 Ko</span>
        </div>
      </div>
      {upLogo.isError && <p className="text-[10.5px] text-st-ecartee">Logo refusé (format ou taille).</p>}
      <input className={field} placeholder="Raison sociale" value={vRs} onChange={(e) => setRs(e.target.value)} />
      <input className={field} placeholder="Coordonnées (tél, email…)" value={vCo} onChange={(e) => setCo(e.target.value)} />
      <input className={field} placeholder="Mention libre (bas de page)" value={vMe} onChange={(e) => setMe(e.target.value)} />
      <button data-marque-save disabled={save.isPending} onClick={() => save.mutate()}
        className="mt-0.5 rounded-md bg-mint py-1.5 text-[12px] font-medium text-mint-ink hover:brightness-110 disabled:opacity-50">
        {save.isSuccess && rs === null ? '✓ Enregistré' : save.isPending ? 'Enregistrement…' : 'Enregistrer'}
      </button>
      <p className="text-[10px] leading-snug text-txt-dim">Apparaît sur vos documents brandés (Dossier, briques PDF). Champs vides = rien ne s’imprime.</p>
    </div>
  )
}


/** M16-C — menu compte (avatar VL). Palier RÉEL (via /moi + plan_courant), pas de faux « Pro ». */
function AccountMenu() {
  const [open, setOpen] = useState(false)
  const [suggOpen, setSuggOpen] = useState(false)
  const [marqueOpen, setMarqueOpen] = useState(false)   // M54-EXPO-2 A6
  const moi = useQuery({ queryKey: ['moi'], queryFn: getMoi, enabled: open })
  const d = moi.data
  const close = () => { setOpen(false); setSuggOpen(false); setMarqueOpen(false) }
  return (
    <div className="relative">
      <button data-account-btn onClick={() => setOpen((o) => !o)} title="Mon compte" aria-label="Mon compte"
        className="flex h-8 w-8 items-center justify-center rounded-full border border-line-2 bg-surface-3 font-mono text-[11px] text-mint transition-colors duration-quick hover:border-mint/50">VL</button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={close} />
          <div data-account-menu className="floating absolute right-0 top-11 z-20 flex w-[300px] flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
              <p className="label-caps">{marqueOpen ? 'Marque blanche' : suggOpen ? 'Proposer une amélioration' : 'Mon compte'}</p>
              {(suggOpen || marqueOpen) && <button onClick={() => { setSuggOpen(false); setMarqueOpen(false) }} className="text-[11px] text-txt-mut hover:text-txt">← retour</button>}
            </div>
            {marqueOpen ? (
              <MarqueForm />
            ) : suggOpen ? (
              <SuggestionForm onDone={close} />
            ) : (
              <div className="flex flex-col p-2 text-[12px]">
                {/* ABONNEMENT — palier réel */}
                <div className="rounded-lg bg-surface-2 px-3 py-2">
                  <p className="text-[10px] uppercase tracking-wide text-txt-dim">Abonnement</p>
                  <p className="mt-0.5 text-txt">Plan <b className="text-mint">{d?.plan_label ?? '…'}</b></p>
                  {d && !d.plan_par_compte && (
                    <p className="mt-0.5 text-[10.5px] leading-snug text-txt-dim">
                      Accès {d.mode === 'pilote' ? 'pilote' : 'du compte'} — l'abonnement par compte (facturation) arrive.
                    </p>
                  )}
                </div>
                {/* COMPTE */}
                <div className="mt-1.5 rounded-lg bg-surface-2 px-3 py-2">
                  <p className="text-[10px] uppercase tracking-wide text-txt-dim">Compte</p>
                  <p className="mt-0.5 text-txt">{d?.mode === 'compte' ? `Rôle : ${d.role}` : 'Session pilote'}</p>
                </div>
                {/* MARQUE BLANCHE (M54-EXPO-2 A6) — réservé aux comptes réels (les documents la portent) */}
                {d?.mode === 'compte' && (
                  <button data-account-marque onClick={() => setMarqueOpen(true)}
                    className="mt-1.5 flex items-center gap-2 rounded-lg px-3 py-2 text-left text-txt transition-colors duration-quick hover:bg-surface-3">
                    <svg viewBox="0 0 20 20" className="h-4 w-4 text-mint" fill="none" stroke="currentColor" strokeWidth="1.4"><rect x="3" y="4" width="14" height="12" rx="2" /><path d="M3 8h14M7 12h6" strokeLinecap="round" /></svg>
                    Marque blanche <span className="ml-auto text-[10px] text-txt-dim">logo · coordonnées</span>
                  </button>
                )}
                {/* PROPOSER UNE AMÉLIORATION */}
                <button data-account-suggest onClick={() => setSuggOpen(true)}
                  className="mt-1.5 flex items-center gap-2 rounded-lg px-3 py-2 text-left text-txt transition-colors duration-quick hover:bg-surface-3">
                  <svg viewBox="0 0 20 20" className="h-4 w-4 text-mint"><path d="M10 3.5 L11.6 8.4 L16.5 10 L11.6 11.6 L10 16.5 L8.4 11.6 L3.5 10 L8.4 8.4 Z" fill="currentColor" /></svg>
                  Proposer une amélioration
                </button>
                {/* DÉCONNEXION */}
                <a href="/logout" className="mt-0.5 flex items-center gap-2 rounded-lg px-3 py-2 text-txt-mut transition-colors duration-quick hover:bg-surface-3 hover:text-st-ecartee">
                  <svg viewBox="0 0 20 20" className="h-4 w-4"><path d="M7 3H4v14h3M13 14l4-4-4-4M17 10H8" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" /></svg>
                  Se déconnecter
                </a>
              </div>
            )}
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
        <AccountMenu />
      </div>
    </header>
  )
}
