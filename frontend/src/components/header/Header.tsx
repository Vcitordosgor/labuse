import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Fragment, useEffect, useState } from 'react'
import { banAutocomplete, deleteLogo, getCommunes, getEnteteCloche, getEvents, getMarque, getMoi, getNotifPrefs, getParcelsGeojson, getProjets, markAllEventsRead, markEventRead, modPatrimoineSearch, parcelAt, patchNotifPref, postLogo, postMarque, postRetour, searchParcels, type LabuseEvent } from '../../lib/api'
import { estIdu, estSectionNumero, iduComplet, normSectionNumero } from '../../lib/format'

// M87 P5.1 — REGROUPER les notifications : une ligne par commune quand plusieurs événements de même
// nature s'y produisent (« 8 nouveaux permis à Saint-Louis » + « Voir les 8 → »), au lieu de N lignes
// qui noient la cloche. Les événements sans commune (veilles de zone, système) restent en ligne propre.
const _NOM_KIND: Record<string, string> = {
  permis: 'permis', bascule: 'basculements de statut', bodacc: 'procédures BODACC',
  veille: 'alertes de vos secteurs et critères', parcelle_suivie: 'changements', veille_zone: 'alertes de vos secteurs et critères',
  // RETOURS-11 A5 — les événements Radar (pige) portaient une clé brute (`pige.statut_change`) et un
  // libellé technique ; on les regroupe sous des noms humains.
  'pige.statut_change': 'changements d’annonce', 'pige.vendue_dvf': 'ventes constatées',
  'pige.baisse_prix': 'baisses de prix', 'pige.nouvelle': 'nouvelles annonces',
  'pige.signalement_client': 'signalements', match: 'correspondances de veille',
}

// RETOURS-11 A5 — HUMANISATION des libellés bruts servis à la cloche. Deux sources de « clés brutes » :
//   · le STATUT interne du Radar (`en_vente_longue`, `a_reverifier`, `retiree_sans_vente`…) inséré tel
//     quel dans le titre par pige/cycle.py (« Statut → en_vente_longue — bien #58 (Saint-Denis) ») ;
//   · la RÉFÉRENCE technique « bien #58 » (id interne, aucun sens pour le client).
// On traduit ce qu'on SAIT lire, sans rien inventer : le statut → phrase française, « bien #N » retiré.
// La commune (entre parenthèses dans le titre d'origine, ou e.commune) est conservée quand présente.
const _STATUT_HUMAIN: Record<string, string> = {
  en_vente_longue: 'En vente depuis plus de 90 jours',
  a_reverifier: 'Annonce à revérifier (plus de 60 jours sans confirmation)',
  retiree_sans_vente: 'Retirée sans vente constatée',
  retiree: 'Annonce retirée',
  vendue: 'Vendue (mutation DVF constatée)',
  active: 'Remise en vente',
}
// remplace toute clé brute résiduelle qui apparaîtrait dans un texte libre (défense en profondeur).
const _CLE_BRUTE = /\b(en_vente_longue|retiree_sans_vente|a_reverifier|retiree|vendue|active)\b/g
function _detechnifier(s: string): string {
  // retire « bien #58 » et «  — bien #58 » (référence interne) puis toute clé brute restante.
  return s.replace(/\s*[—-]?\s*bien\s*#\d+/gi, '').replace(_CLE_BRUTE, (k) => _STATUT_HUMAIN[k] ?? k).trim()
}
// Titre HUMAIN d'un événement : reconstruit les titres Radar « Statut → <clé> — bien #N (Commune) »
// en « <phrase française> — <Commune> » ; sinon nettoie le titre existant (retrait clé/technique).
function titreHumain(e: LabuseEvent): string {
  const t = e.titre ?? ''
  const m = t.match(/statut\s*[→:>-]+\s*([a-z_]+)/i)   // « Statut → en_vente_longue … »
  if (m && _STATUT_HUMAIN[m[1]]) {
    const commune = e.commune ?? (t.match(/\(([^)]+)\)\s*$/)?.[1] ?? '')
    return commune ? `${_STATUT_HUMAIN[m[1]]} — ${commune}` : _STATUT_HUMAIN[m[1]]
  }
  return _detechnifier(t) || t
}
type Bloc =
  | { type: 'single'; e: LabuseEvent }
  | { type: 'groupe'; cle: string; nature: string; commune: string; items: LabuseEvent[] }
function grouperEvents(items: LabuseEvent[]): Bloc[] {
  const par = new Map<string, LabuseEvent[]>()
  for (const e of items) {
    const cle = e.commune ? `${e.kind}|${e.commune}` : `__solo__${e.id}`
    if (!par.has(cle)) par.set(cle, [])
    par.get(cle)!.push(e)
  }
  const out: Bloc[] = []
  for (const [cle, es] of par) {
    if (es.length >= 2 && es[0].commune)
      out.push({ type: 'groupe', cle, nature: _NOM_KIND[es[0].kind] ?? 'événements', commune: es[0].commune, items: es })
    else for (const e of es) out.push({ type: 'single', e })
  }
  return out
}
import { useApp } from '../../store/useApp'
import { ListPaginationFooter, PAGE_SIZE } from '../ListPagination'
import { AddressAutocomplete, type AddressSelection } from '../AddressAutocomplete'
import { CP_COMMUNES } from '../panel/FiltreLabuse'

// RETOURS-1 R2 (Vic) — le retrait du CP par M65 P7 est ANNULÉ : le sélecteur de communes
// ré-affiche le code postal (source unique CP_COMMUNES, table mesurée du panneau).
const CP_PAR_COMMUNE: Record<string, string> = Object.fromEntries(CP_COMMUNES.map(([cp, nom]) => [nom, cp]))

export function Omnibox() {
  // CONNEXIONS-2 Lot 8 (C1) — la barre résout, dans l'ordre : IDU · SIREN/SIRET · nom de propriétaire ·
  // projet du compte · commune · adresse. Nom et SIREN ouvrent Scan patrimoine à l'ÉTAT 2 (propriétaire
  // posé, via setM02Prefill) ; un projet ouvre le projet (setOpenProjet). La résolution propriétaire
  // RÉUTILISE la recherche self-contained de Scan patrimoine (modPatrimoineSearch) — pas une 4e impl.
  const { select, setView, setCommune, commune, setToast, setM02Prefill, setModule, setOpenProjet } = useApp()
  const qc = useQueryClient()
  const geo = useQuery({ queryKey: ['geojson', commune], queryFn: getParcelsGeojson, enabled: commune != null })
  const communes = useQuery({ queryKey: ['communes'], queryFn: getCommunes })
  const ouvrirScan = (siren: string) => { setM02Prefill(siren); setModule('patrimoine') }
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

  // CONNEXIONS-2 Lot 8 (C1) — résolution multi-type par la barre du bandeau. Ordre : IDU · SIREN/SIRET ·
  // nom de propriétaire · projet · commune · adresse. (Commune AVANT adresse : sinon « Saint-Paul »
  // serait géocodé en une parcelle au lieu d'ouvrir le périmètre de la commune — écart assumé.)
  const onEnterRaw = async (raw: string) => {
    if (!raw) return
    setSearching(true)
    try {
      const val = raw.trim()
      const low = val.toLowerCase()
      const dg = val.replace(/\s+/g, '')

      // 1. IDU explicite → fiche
      if (estIdu(val)) {
        const idu = iduComplet(dg.toUpperCase())
        const localHit = geo.data?.features.find((f) => String(f.properties?.idu ?? '').toUpperCase() === idu)
        if (localHit) { setView('cartes'); select(idu); return }
        const rem = await searchParcels(idu, { ileEntiere: true }).catch(() => [])
        if (rem[0]) { setView('cartes'); select(rem[0].idu); return }
      }

      // 2. SIREN (9) / SIRET (14) → Scan patrimoine à l'état 2 (propriétaire posé)
      if (/^\d{9}$/.test(dg) || /^\d{14}$/.test(dg)) { ouvrirScan(dg.slice(0, 9)); return }

      // 2bis. RÉFÉRENCE CADASTRALE COURTE (section + numéro, ex. « BW0917 ») — RETOURS-12 T1.
      // Grammaire UNIQUE (estSectionNumero/normSectionNumero, LOI-3), résolue AVANT le nom de
      // propriétaire (sinon « BW0917 » — qui contient des lettres — filerait en recherche d'owner).
      // Jamais de choix au hasard : plusieurs communes → on présélectionne celle du contexte si elle
      // correspond, sinon on nomme les communes et on demande de préciser (jamais muet).
      if (estSectionNumero(val)) {
        const needle = normSectionNumero(val)
        const cands = (await searchParcels(needle, { ileEntiere: true }).catch(() => []))
          .filter((r) => iduComplet(r.idu).toUpperCase().endsWith(needle))
        if (cands.length === 1) { setView('cartes'); select(cands[0].idu); return }
        if (cands.length > 1) {
          const daccord = commune ? cands.find((c) => c.commune === commune) : undefined
          if (daccord) { setView('cartes'); select(daccord.idu); return }
          const comms = [...new Set(cands.map((c) => c.commune))]
          setToast(`« ${val.toUpperCase()} » existe dans ${comms.length} communes (${comms.slice(0, 4).join(', ')}${comms.length > 4 ? '…' : ''}) — ouvrez la commune, puis ressaisissez la référence.`)
          return
        }
        setToast(`Aucune parcelle « ${val.toUpperCase()} » (référence section + numéro) sur l'île.`)
        return
      }

      // 3. NOM de propriétaire → Scan patrimoine état 2 (réutilise la recherche de Scan patrimoine)
      if (/[a-zA-Zà-ÿ]/.test(val)) {
        const owners = await modPatrimoineSearch(val).catch(() => [])
        if (owners[0]) { ouvrirScan(owners[0].siren); return }
      }

      // 4. PROJET du compte (nom exact puis contient) → ouvre le projet
      const projets = await qc.fetchQuery({ queryKey: ['projets'], queryFn: getProjets }).catch(() => [])
      const proj = projets.find((p) => p.nom.toLowerCase() === low)
        ?? (val.length >= 3 ? projets.find((p) => p.nom.toLowerCase().includes(low)) : undefined)
      if (proj) { setOpenProjet({ id: proj.id, nom: proj.nom }); return }

      // 5. COMMUNE (exacte ou préfixe) → périmètre. Robuste au timing : si la liste n'est pas encore en
      // cache (recherche juste après le chargement), on la résout à la demande (même query key).
      if (!/\d/.test(val)) {
        const comList = communes.data ?? await qc.fetchQuery({ queryKey: ['communes'], queryFn: getCommunes }).catch(() => [])
        const c = comList.find((x) => x.commune.toLowerCase() === low)
          ?? (val.length >= 3 ? comList.find((x) => x.commune.toLowerCase().startsWith(low)) : undefined)
        if (c) { setCommune(c.commune); setView('cartes'); return }
      }

      // 6. IDU partiel / recherche parcelle
      const qn = val.toUpperCase().replace(/\s+/g, '')
      const hit = geo.data?.features.find((f) => {
        const idu = String(f.properties?.idu ?? '').toUpperCase()
        return idu.includes(qn) || idu.slice(8).includes(qn)
      })
      if (hit) { setView('cartes'); select(String(hit.properties?.idu)); return }
      const remote = await searchParcels(qn, { ileEntiere: true }).catch(() => [])
      if (remote[0]) { setView('cartes'); select(remote[0].idu); return }

      // 7. ADRESSE libre → 1re suggestion interne → parcelle
      if (/[a-zA-Zà-ÿ]/.test(val)) {
        const feats = await banAutocomplete(val).catch(() => [])
        if (feats[0]) { await onPickAddress({ label: feats[0].label, lon: feats[0].lon, lat: feats[0].lat, idu: feats[0].idu }); return }
      }
      setToast(`Aucun résultat (IDU, SIREN, propriétaire, projet, commune ou adresse) pour « ${val} »`)
    } finally {
      setSearching(false)
    }
  }

  return (
    <div className="flex h-8 w-[360px] items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 transition-colors duration-quick focus-within:border-mint">
      {/* DA §10 — LA LOUPE EST DANS LE CHAMP (leading). Elle reste cliquable (lance la recherche
          sur le texte courant) ; pendant la résolution elle devient un spinner sobre (M55-B). */}
      <button
        disabled={searching}
        onClick={() => {
          const el = document.querySelector<HTMLInputElement>('[data-omnibox]')
          if (el) onEnterRaw(el.value.trim())
        }}
        title="Lancer la recherche" aria-label="Lancer la recherche" aria-busy={searching}
        className="flex h-5 w-5 shrink-0 items-center justify-center text-txt-faint transition-colors duration-quick hover:text-mint disabled:cursor-wait">
        {searching ? (
          <svg viewBox="0 0 20 20" className="h-[15px] w-[15px] animate-spin" aria-hidden>
            <circle cx="10" cy="10" r="6.5" fill="none" stroke="currentColor" strokeWidth="2" strokeOpacity="0.3" />
            <path d="M10 3.5 a6.5 6.5 0 0 1 6.5 6.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        ) : (
          <svg viewBox="0 0 20 20" className="h-[15px] w-[15px]">
            <circle cx="9" cy="9" r="5.5" fill="none" stroke="currentColor" strokeWidth="1.7" />
            <line x1="13" y1="13" x2="17.5" y2="17.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
          </svg>
        )}
      </button>
      <AddressAutocomplete
        data-omnibox
        onSelect={onPickAddress}
        onEnterRaw={onEnterRaw}
        placeholder="Rechercher : IDU, SIREN, propriétaire, projet, adresse…"
        className="w-full min-w-0 bg-transparent text-xs text-txt placeholder:text-txt-mut focus:outline-none"
      />
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
          {/* M55-H point 7, RESTAURÉ par RETOURS-1 R2 (Vic) : le retrait du CP (M65 P7, commit
              61dde68b) est ANNULÉ — menu 320 px, nom + code postal (CP_COMMUNES, source unique
              mesurée du panneau — l'INSEE ressemblait à un CP sans l'être) + « voir la fiche → »
              sur UNE ligne, et le NOM ENTIER de la commune au survol (title). */}
          <div className="floating absolute left-0 top-9 z-20 flex max-h-[70vh] w-[320px] flex-col overflow-y-auto p-1.5">
            {/* RETOURS-5 T8 — survol PLEIN (dégradé vert, encre sombre) sur chaque ligne, comme partout. */}
            <button onClick={() => pick(null)}
              className={`hover-fill rounded-md px-3 py-2 text-left text-xs ${n === 0 ? 'bg-surface-3 text-mint' : 'text-txt'}`}>
              Toute l’île
            </button>
            <div className="mx-3 my-1 border-t border-line" />
            {/* M55-D stage 9 ter point 2 (correction Vic) : le LIEN TEXTE d'origine (pattern
                M55-C) — « voir la fiche → » à droite du nom. Le NOM sélectionne (zoom +
                pré-coche, bloc 3 inchangé) ; le lien ouvre la fiche de CETTE commune SANS
                changer le périmètre (stopPropagation). RETOURS-5 T8 — la LIGNE ENTIÈRE reçoit
                l'aplat plein vert (nom + code postal + « voir la fiche → » inversés en encre sombre). */}
            {(communes.data ?? []).map((c) => (
              <div key={c.insee} className="hover-fill flex items-center rounded-md">
                <button onClick={() => pick(c.commune)} title={c.commune}
                  className={`min-w-0 flex-1 truncate whitespace-nowrap px-3 py-1.5 text-left text-xs ${filters.communes.includes(c.commune) ? 'text-mint' : 'text-txt'}`}>
                  {c.commune} <span className="font-mono text-[11px] tabular-nums text-txt-dim">{CP_PAR_COMMUNE[c.commune] ?? c.insee}</span>
                </button>
                {/* M62-P1 (k) : « voir la fiche → » FIXE et VERT sur chaque ligne (plus au survol seul). */}
                <button data-fiche-commune onClick={(e) => { e.stopPropagation(); setContexteCommune(c.commune); setOpen(false) }}
                  title={`Fiche de ${c.commune} — SRU, ANRU, PLH, marché logement (n'affecte pas le périmètre)`}
                  className="shrink-0 whitespace-nowrap px-2.5 py-1.5 text-[11px] text-mint transition-opacity duration-quick hover:underline">
                  voir la fiche →
                </button>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

// bouton FICHE COMMUNE — visible quand une commune est active : le volet SRU/ANRU/PLH/marché.
// RETOURS-3 R7 (Vic 31/08) : « Contexte » ne disait rien à l'utilisateur → « Fiche commune » (ce que
// le clic ouvre). Couleur passée du mauve (réservé IA) à l'AMBRE des chips d'information (ex. « drapeau
// fermé ») — ce n'est pas une surface IA.
function ContexteButton() {
  const { commune, focusCommune } = useApp()
  if (!commune) return null
  return (
    <button onClick={() => focusCommune(commune)} data-contexte-btn
      className="flex h-[26px] shrink-0 items-center gap-1 rounded-full border border-amber/40 bg-amber/[0.08] px-2.5 text-[11px] text-amber transition-colors duration-quick hover:border-amber"
      title="Fiche commune — SRU, ANRU, PLH, marché logement (sources officielles)">
      ⓘ Fiche commune
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

// M85 — date relative sobre (sans dépendance) : « à l'instant / il y a 3 h / il y a 2 j / 14 août ».
function tempsRelatif(iso: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  const s = Math.floor((Date.now() - d.getTime()) / 1000)
  if (s < 60) return "à l'instant"
  if (s < 3600) return `il y a ${Math.floor(s / 60)} min`
  if (s < 86400) return `il y a ${Math.floor(s / 3600)} h`
  if (s < 7 * 86400) return `il y a ${Math.floor(s / 86400)} j`
  return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })
}

// RETOURS-11 A6 — date ISO (jour) → « 4 septembre 2026 » (échéances du compte).
function dateFr(iso: string): string {
  const d = new Date(iso)
  return isNaN(d.getTime()) ? iso : d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })
}

function NotifBell() {
  const [open, setOpen] = useState(false)
  // M104 P3 — la config des recherches sauvegardées (NL, exemples, liste) a déménagé dans la
  // section Surveillance (volet Critères) : la cloche affiche des événements, rien d'autre.
  const qc = useQueryClient()
  const { select, setView, openSources, openSurveillance } = useApp()
  // RETOURS-11 A5 (T4) — pagination par 200 (ListPaginationFooter). `limite` grandit au clic ; la
  // clé de query l'inclut pour refetch. « Voir plus » n'apparaît que si la fenêtre est pleine.
  const [limite, setLimite] = useState(PAGE_SIZE)
  const ev = useQuery({ queryKey: ['events', limite], queryFn: () => getEvents(limite), refetchInterval: 60_000 })
  // M87 P5 — l'en-tête est DÉRIVÉ du registre (jamais écrit à la main) : on ne promet que le détectable.
  const entete = useQuery({ queryKey: ['entete-cloche'], queryFn: getEnteteCloche, enabled: open, staleTime: 3_600_000 })
  const invalidate = () => { qc.invalidateQueries({ queryKey: ['events'] }); qc.invalidateQueries({ queryKey: ['events-count'] }) }
  const readOne = useMutation({ mutationFn: markEventRead, onSuccess: invalidate })
  const readAll = useMutation({ mutationFn: markAllEventsRead, onSuccess: invalidate })
  // M87 P5.1 — la carte d'un événement, réutilisée en ligne seule ET dans un groupe déplié.
  const carte = (e: LabuseEvent) => (
    <div key={e.id} className={`hover-fill rounded-lg border px-3 py-2 ${e.lu ? 'border-line-2 opacity-55' : 'border-line-2 bg-bg-2'}`}>
      {/* DA §15 — non-lue en PORTE (fond bg-2) + pastille AMBRE ; lues estompées à 55 %. */}
      <div className="flex items-center gap-2">
        <span className="dot shrink-0" style={{ background: e.lu ? 'var(--line-3)' : 'var(--amber)' }} />
        {e.demo && <span className="rounded-full bg-surface-3 px-1.5 py-0.5 text-[8.5px] font-medium text-txt-dim" title="Événement de démonstration (run q_v2_demo)">DÉMO</span>}
        <button onClick={() => {
            if (e.idu) { setView('cartes'); select(e.idu) }
            else if (e.lien?.startsWith('/sources')) openSources()
            else if (e.lien?.startsWith('/copilote')) setView('copilote')
            // GB-026 — notif de SECTEUR (veille_zone) : lien « …#surveillance=secteurs » ouvre le
            // bon volet de la Surveillance (avant : handler absent → le clic ne menait nulle part).
            else if (e.lien?.includes('#surveillance=')) {
              const t = e.lien.split('#surveillance=')[1]
              openSurveillance(t === 'parcelles' || t === 'criteres' ? t : 'secteurs')
            }
            setOpen(false)
          }}
          className="min-w-0 flex-1 truncate text-left text-xs text-txt hover:text-txt-hi">{titreHumain(e)}</button>
        {!e.lu && <button onClick={() => readOne.mutate(e.id)} className="shrink-0 text-[11px] text-txt-dim hover:text-mint" title="Marquer lu" aria-label="Marquer comme lu">✓</button>}
      </div>
      {e.detail && <p className="mt-0.5 whitespace-pre-line text-[11px] leading-snug text-txt-dim">{_detechnifier(e.detail)}</p>}
      <p className="mt-0.5 flex items-center gap-1.5 text-[9px] text-txt-dim">
        {e.source && <><span className="font-medium text-txt-mut">{e.source}</span><span>·</span></>}
        <span className="font-mono" title={e.date}>{tempsRelatif(e.ts ?? e.date)}</span>
      </p>
    </div>
  )
  // M85 — préférences par type et par canal (cloche / e-mail), l'écran minimal in-app.
  const [prefsOpen, setPrefsOpen] = useState(false)
  const [ouverts, setOuverts] = useState<Set<string>>(() => new Set())   // M87 P5.1 — groupes dépliés
  const notifPrefs = useQuery({ queryKey: ['notif-prefs'], queryFn: getNotifPrefs, enabled: open && prefsOpen })
  const setPref = useMutation({ mutationFn: patchNotifPref, onSuccess: () => { invalidate(); qc.invalidateQueries({ queryKey: ['notif-prefs'] }) } })
  const unread = ev.data?.unread ?? 0
  // GB-004 : Escape ferme le dropdown Notifications (il n'avait aucun handler clavier — seul le clic sur
  // le backdrop fermait). Aligné sur le patron des overlays. Listener actif uniquement quand ouvert.
  useEffect(() => {
    if (!open) return
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [open])
  // RETOURS-11 A6 — « Préférences de notifications » (menu Mon compte) ouvre la cloche sur son volet
  // Préférences (les réglages cloche/e-mail par type vivent ICI ; pas de duplication d'écran).
  useEffect(() => {
    const h = () => { setOpen(true); setPrefsOpen(true) }
    window.addEventListener('labuse:open-notif-prefs', h)
    return () => window.removeEventListener('labuse:open-notif-prefs', h)
  }, [])
  return (
    <div className="relative">
      {/* RETOURS-9 (Q9) — la cloche OUVERTE devient pleine de sa couleur (vert, encre sombre), pas un liseré. */}
      <button onClick={() => setOpen((o) => !o)} title="Notifications" aria-label="Notifications" aria-pressed={open}
        className={`relative flex h-9 w-9 items-center justify-center rounded-full border transition-colors duration-quick ${
          open ? 'border-mint bg-mint text-mint-ink' : 'border-line-2 bg-surface-3 text-txt-mut hover:text-txt'}`}>
        <svg viewBox="0 0 20 20" className="h-[18px] w-[18px]">
          <path d="M10 3 a4 4 0 0 1 4 4 v3 l1.5 2.5 h-11 L6 10 V7 a4 4 0 0 1 4-4Z" fill="none" stroke="currentColor" strokeWidth="1.4" />
          <path d="M8.5 15 a1.5 1.5 0 0 0 3 0" fill="none" stroke="currentColor" strokeWidth="1.4" />
        </svg>
        {unread > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-amber px-1 font-mono text-[9px] font-bold text-[#2A2113]">
            {unread > 99 ? '99+' : unread}{/* GB-002 : badge capé (le dropdown garde le vrai compte) */}
          </span>
        )}
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="floating absolute right-0 top-11 z-20 flex max-h-[70vh] w-[min(440px,92vw)] flex-col overflow-hidden">
            {/* M104 P3 — en-tête refondu : classes du panneau brief (DA-ACCUEIL-BRIEF-v1, même
                famille de surface) — titre mono capitales + actions à droite, UNE ligne. */}
            <header data-notif-entete className="flex shrink-0 items-center gap-3 border-b border-line px-[22px] py-4">
              {/* M16-B5 : plus d'incohérence « 0 non lue » sur liste pleine — « à jour » quand tout est lu */}
              <h2 className="m-0 whitespace-nowrap font-mono text-[11px] uppercase tracking-[.16em] text-txt-mut">
                Notifications{unread > 0 ? ` · ${unread}` : ''}
              </h2>
              <div className="ml-auto flex items-center gap-3 whitespace-nowrap">
                {/* RECETTE-2 LOT D2 — l'entrée « Le point du jour » est RETIRÉE de l'en-tête Notifications.
                    Retrait de surface : la page /events/digest.html (aperçu du digest) et les envois Brevo
                    restent INTACTS (atteignables par e-mail / URL directe) — plus aucun lien in-app n'y mène. */}
                {/* M85 — préférences par type et par canal (l'écran minimal in-app) */}
                <button data-notif-prefs-toggle onClick={() => setPrefsOpen((o) => !o)} className="text-[11px] text-txt-mut hover:text-txt" title="Préférences de notification">{prefsOpen ? 'fermer' : 'préférences'}</button>
                {unread > 0 && <button onClick={() => readAll.mutate()} className="text-[11px] text-txt-mut hover:text-txt">tout lire</button>}
              </div>
            </header>
            {/* M85 — l'écran minimal : par type, cloche / e-mail / les deux / rien. */}
            {prefsOpen ? (
              <div data-notif-prefs className="shrink-0 border-b border-line bg-surface-2 px-4 py-3">
                <p className="mb-2 text-[11px] font-medium text-txt">Que recevoir, et où ?</p>
                {/* RETOURS-11F3 A5 — TROIS canaux : cloche · brief (du matin) · e-mail, par type. */}
                <div className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-x-4 gap-y-2 text-[11px]">
                  <span className="text-txt-dim">Type</span>
                  <span className="text-center text-txt-dim">Cloche</span>
                  <span className="text-center text-txt-dim" title="Le résumé du matin (Copilote)">Brief</span>
                  <span className="text-center text-txt-dim">E-mail</span>
                  {(notifPrefs.data?.types ?? []).map((t) => (
                    <Fragment key={t.key}>
                      <span className="text-txt">{t.label}{t.verrou && <span className="text-txt-dim"> · toujours actif</span>}</span>
                      <input type="checkbox" checked={t.cloche} aria-label={`${t.label} — cloche`} data-pref={`${t.key}-cloche`}
                        onChange={(e) => setPref.mutate({ pref_type: t.key, cloche: e.target.checked, email: t.email, brief: t.brief })}
                        className="mx-auto h-3.5 w-3.5 accent-mint" />
                      {/* BRIEF — canal du matin, applicable aux chaînes 1+2 seulement (chaîne 3 = immédiat → grisé). */}
                      <input type="checkbox" checked={t.brief && !t.brief_na} disabled={t.brief_na} aria-label={`${t.label} — brief`} data-pref={`${t.key}-brief`}
                        title={t.brief_na ? 'Envoi immédiat — pas un brief du matin' : 'Apparaît dans le brief du matin'}
                        onChange={(e) => setPref.mutate({ pref_type: t.key, cloche: t.cloche, email: t.email, brief: e.target.checked })}
                        className="mx-auto h-3.5 w-3.5 accent-mint disabled:opacity-30" />
                      {/* M85-B — maintenance : e-mail VERROUILLÉ (non désactivable, conséquences réelles). */}
                      <input type="checkbox" checked={t.email} disabled={t.verrou} aria-label={`${t.label} — e-mail`} data-pref={`${t.key}-email`}
                        title={t.verrou ? 'Non désactivable — conséquences réelles (maintenance, compte)' : undefined}
                        onChange={(e) => setPref.mutate({ pref_type: t.key, cloche: t.cloche, email: e.target.checked, brief: t.brief })}
                        className="mx-auto h-3.5 w-3.5 accent-mint disabled:opacity-40" />
                    </Fragment>
                  ))}
                </div>
                <p className="mt-2 text-[10px] leading-snug text-txt-dim">La cloche est instantanée · le brief est le résumé du matin (Copilote) · l'e-mail est un résumé quotidien (7h, heure Réunion). Tout décocher = ne rien recevoir.</p>
              </div>
            ) : (
            /* M87 P5 : intro DÉRIVÉE du registre (libelles_entete_cloche) — maille SUR la parcelle,
               jamais « à proximité » figé ; un déclencheur ajouté au registre met la phrase à jour
               SEUL. M104 : vocabulaire aligné (« vos secteurs », plus jamais « veille »). */
            <p className="shrink-0 border-b border-line px-[22px] py-3 text-[12.5px] leading-snug text-txt-mut">
              Ce qui bouge sur <b className="font-semibold text-txt">vos parcelles suivies</b>
              {entete.data?.libelles?.length ? <> — {entete.data.libelles.join(', ')} — </> : ' '}
              dans <b className="font-semibold text-txt">vos secteurs</b> et sur
              <b className="font-semibold text-txt"> vos critères</b>. On ne vous prévient que sur ce
              qu'on sait réellement détecter.
            </p>
            )}
            <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto p-2">
              {(ev.data?.items ?? []).length === 0 && <p className="p-3 text-xs leading-snug text-txt-dim">Aucune notification pour l'instant — nous vous préviendrons dès qu'une parcelle suivie change ou qu'une de vos veilles se déclenche.</p>}
              {/* M87 P5.1 — REGROUPÉ par commune (une ligne + « Voir les N → ») ; sinon carte simple. */}
              {grouperEvents(ev.data?.items ?? []).map((b) => {
                if (b.type === 'single') return carte(b.e)
                const ouvert = ouverts.has(b.cle)
                const nonLus = b.items.filter((e) => !e.lu).length
                return (
                  <div key={b.cle} className={`rounded-lg border ${nonLus ? 'border-line-2 bg-bg-2' : 'border-line-2 opacity-55'}`}>
                    <div className="hover-fill flex items-center gap-2 rounded-lg px-3 py-2">
                      <span className="dot shrink-0" style={{ background: nonLus ? 'var(--amber)' : 'var(--line-3)' }} />
                      <span className="min-w-0 flex-1 truncate text-xs text-txt">
                        <b className="font-semibold">{b.items.length}</b> {b.nature} à {b.commune}
                      </span>
                      <button onClick={() => setOuverts((s) => { const n = new Set(s); n.has(b.cle) ? n.delete(b.cle) : n.add(b.cle); return n })}
                        className="shrink-0 text-[11px] text-txt-dim hover:text-mint">{ouvert ? 'Réduire ↑' : `Voir les ${b.items.length} →`}</button>
                    </div>
                    {ouvert && <div className="flex flex-col gap-1 px-2 pb-2">{b.items.map(carte)}</div>}
                  </div>
                )
              })}
              {/* RETOURS-11 A5 (T4) — « Voir plus » par 200. Le back ne renvoie pas de total ; on
                  n'affiche l'action QUE si la fenêtre est PLEINE (donc probablement d'autres après),
                  et « Voir plus » remonte la limite d'un cran. Compteur honnête : N chargées. */}
              {(ev.data?.items?.length ?? 0) >= limite && (
                <ListPaginationFooter shown={ev.data?.items?.length ?? 0} total={(ev.data?.items?.length ?? 0) + PAGE_SIZE}
                  onMore={() => setLimite((l) => l + PAGE_SIZE)} className="flex flex-wrap items-center gap-3 border-t border-line px-3 pt-2 text-[11px] text-txt-mut" />
              )}
            </div>
            {/* M104 P3 — l'encart « Vos veilles — alertes sur mesure » a DÉMÉNAGÉ dans la section
                Surveillance (volet Critères) : la cloche affiche des ÉVÉNEMENTS, rien d'autre.
                Un renvoi garde la boucle visible depuis ici — aucune régression, tout est là-bas. */}
            <div className="shrink-0 border-t border-line px-[22px] py-2.5">
              <button data-notif-vers-surveillance onClick={() => { openSurveillance('criteres'); setOpen(false) }}
                className="text-[11px] text-mint hover:underline">
                Régler ce que vous surveillez (parcelles, secteurs, critères) →
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

// RETOURS-1 R1 (Vic) : « Proposer une amélioration » (SuggestionForm) est RETIRÉ du menu compte —
// doublon du bouton « Signaler » de la barre (SignalerButton → /retours). L'endpoint /suggestions
// reste au backend (réversible).

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


/** M16-C — menu compte (avatar VL). RETOURS-1 R1 (Vic) : STATUT RÉEL du compte connecté — plan
 *  réel (comptes.plan, libellé/prix source unique offres.py via /moi) + e-mail. Compte interne =
 *  « Compte interne », jamais un prix. Plus aucune mention de l'ère pilote. */
function AccountMenu() {
  const [open, setOpen] = useState(false)
  const [marqueOpen, setMarqueOpen] = useState(false)   // M54-EXPO-2 A6
  const moi = useQuery({ queryKey: ['moi'], queryFn: getMoi, enabled: open })
  const d = moi.data
  const close = () => { setOpen(false); setMarqueOpen(false) }
  return (
    <div className="relative">
      <button data-account-btn onClick={() => setOpen((o) => !o)} title="Mon compte" aria-label="Mon compte"
        className="flex h-8 w-8 items-center justify-center rounded-full border border-line-2 bg-surface-3 font-mono text-[11px] text-mint transition-colors duration-quick hover:border-mint/50">VL</button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={close} />
          <div data-account-menu className="floating absolute right-0 top-11 z-20 flex w-[300px] flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
              <p className="label-caps">{marqueOpen ? 'Marque blanche' : 'Mon compte'}</p>
              {marqueOpen && <button onClick={() => setMarqueOpen(false)} className="text-[11px] text-txt-mut hover:text-txt">← retour</button>}
            </div>
            {marqueOpen ? (
              <MarqueForm />
            ) : (
              <div className="flex flex-col p-2 text-[12px]">
                {/* RETOURS-11 A6 — IDENTITÉ : e-mail + nom du compte. « Session locale (dev) » n'est
                    montrée QUE si le back dit mode !== 'compte' (jamais en prod, où le rideau d'auth
                    impose une session). */}
                <div className="rounded-lg bg-surface-2 px-3 py-2">
                  <p className="text-[10px] uppercase tracking-wide text-txt-dim">Compte</p>
                  {d?.mode === 'compte' ? (
                    <>
                      {d.email && <p className="mt-0.5 truncate text-txt" title={d.email}>{d.email}</p>}
                      {d.nom && d.nom !== d.email && <p className="mt-0.5 truncate text-[11px] text-txt-mut" title={d.nom}>{d.nom}</p>}
                    </>
                  ) : d ? (
                    <p className="mt-0.5 text-txt-dim">Session locale (dev) — aucun compte connecté.</p>
                  ) : (
                    <p className="mt-0.5 text-txt-dim">…</p>
                  )}
                </div>
                {/* ABONNEMENT + ÉCHÉANCE — « Intégral depuis le … » (depuis) ou « Essai jusqu'au … »
                    (essai_jusqu) ; compte interne sans prix. Dates lues du back, jamais inventées. */}
                <div className="mt-1.5 rounded-lg bg-surface-2 px-3 py-2">
                  <p className="text-[10px] uppercase tracking-wide text-txt-dim">Abonnement</p>
                  {d?.plan === 'interne' ? (
                    <p className="mt-0.5 text-txt">Compte interne</p>
                  ) : (
                    <>
                      <p className="mt-0.5 text-txt">Plan <b className="text-mint">{d?.plan_label ?? '…'}</b>
                        {d?.plan_eur_mois != null && <span className="text-txt-dim"> · {d.plan_eur_mois} €/mois</span>}</p>
                      {d?.essai_jusqu
                        ? <p className="mt-0.5 text-[10.5px] text-amber">Essai jusqu'au {dateFr(d.essai_jusqu)}</p>
                        : d?.depuis
                          ? <p className="mt-0.5 text-[10.5px] text-txt-dim">{d.plan_label ?? 'Abonné'} depuis le {dateFr(d.depuis)}</p>
                          : null}
                    </>
                  )}
                </div>
                {/* ACTIONS — compte réel uniquement (mot de passe, préférences, marque blanche). */}
                {d?.mode === 'compte' && (
                  <>
                    {/* CHANGER MON MOT DE PASSE — self-service existant (/reset envoie un lien) */}
                    <a data-account-motdepasse href="/reset"
                      className="mt-1.5 flex items-center gap-2 rounded-lg px-3 py-2 text-left text-txt transition-colors duration-quick hover:bg-surface-3">
                      <svg viewBox="0 0 20 20" className="h-4 w-4 text-mint" fill="none" stroke="currentColor" strokeWidth="1.4"><rect x="4" y="9" width="12" height="8" rx="1.5" /><path d="M7 9V6.5a3 3 0 0 1 6 0V9" /></svg>
                      Changer mon mot de passe
                    </a>
                    {/* PRÉFÉRENCES DE NOTIFICATIONS — ouvre la cloche sur son volet Préférences */}
                    <button data-account-prefs onClick={() => { close(); window.dispatchEvent(new Event('labuse:open-notif-prefs')) }}
                      className="flex items-center gap-2 rounded-lg px-3 py-2 text-left text-txt transition-colors duration-quick hover:bg-surface-3">
                      <svg viewBox="0 0 20 20" className="h-4 w-4 text-mint" fill="none" stroke="currentColor" strokeWidth="1.4"><path d="M10 3a3.5 3.5 0 0 1 3.5 3.5v3l1.5 2.5h-10L6 9.5v-3A3.5 3.5 0 0 1 10 3Z" /><path d="M8.5 16a1.5 1.5 0 0 0 3 0" /></svg>
                      Préférences de notifications
                    </button>
                    {/* MARQUE BLANCHE (M54-EXPO-2 A6) */}
                    <button data-account-marque onClick={() => setMarqueOpen(true)}
                      className="flex items-center gap-2 rounded-lg px-3 py-2 text-left text-txt transition-colors duration-quick hover:bg-surface-3">
                      <svg viewBox="0 0 20 20" className="h-4 w-4 text-mint" fill="none" stroke="currentColor" strokeWidth="1.4"><rect x="3" y="4" width="14" height="12" rx="2" /><path d="M3 8h14M7 12h6" strokeLinecap="round" /></svg>
                      Marque blanche <span className="ml-auto text-[10px] text-txt-dim">logo · coordonnées</span>
                    </button>
                  </>
                )}
                {/* RETOURS-11 R4 — « Contact » : mailto contact@labuse.immo, sujet pré-rempli avec le
                    compte (le bouton « Signaler » de la barre reste, distinct). */}
                <a data-account-ecrire href={`mailto:contact@labuse.immo?subject=${encodeURIComponent(`Contact LABUSE — ${d?.email ?? d?.nom ?? 'compte'}`)}`}
                  className="mt-0.5 flex items-center gap-2 rounded-lg px-3 py-2 text-left text-txt transition-colors duration-quick hover:bg-surface-3">
                  <svg viewBox="0 0 20 20" className="h-4 w-4 text-mint" fill="none" stroke="currentColor" strokeWidth="1.4"><rect x="3" y="5" width="14" height="10" rx="1.5" /><path d="M3.5 6l6.5 5 6.5-5" /></svg>
                  Contact
                </a>
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

// DASHBOARD-V1 · D1 — bouton « Signaler » (en haut à droite) : bug/idée/question + message →
// table retours, suivie au dashboard admin (statut nouveau/traité/répondu). RGPD-sobre : le
// client écrit ce qu'il veut transmettre, rien d'autre n'est capté ici.
const RETOUR_TYPES = [
  { key: 'bug' as const, label: 'Bug' },
  { key: 'idee' as const, label: 'Idée' },
  { key: 'question' as const, label: 'Question' },
]
function SignalerButton() {
  const [open, setOpen] = useState(false)
  const [type, setType] = useState<'bug' | 'idee' | 'question'>('bug')
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const setToast = useApp((s) => s.setToast)
  // Échap ferme le panneau (cohérence app — G6) ; le brouillon reste (fermeture ≠ abandon).
  useEffect(() => {
    if (!open) return
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [open])
  const envoyer = async () => {
    if (msg.trim().length < 3 || busy) return
    setBusy(true)
    try {
      await postRetour({ type, message: msg.trim() })
      setToast('Merci — votre retour est transmis.')
      setOpen(false)
      setMsg('')
    } catch {
      setToast('Envoi impossible pour le moment — réessayez.')
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="relative">
      {/* RETOURS-10 (T6) — bouton ACTIF = PLEIN vert, encre sombre (règle DA RETOURS-9), comme la
          cloche : plus de simple liseré quand le panneau est ouvert. */}
      <button data-signaler onClick={() => setOpen((o) => !o)} aria-pressed={open}
        title="Signaler un bug, proposer une idée, poser une question"
        className={`rounded-lg border px-3 py-1.5 text-xs transition-colors duration-quick ${
          open ? 'border-mint bg-mint font-medium text-mint-ink' : 'border-line-2 text-txt-mut hover:text-txt'}`}>
        Signaler
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="floating absolute right-0 top-10 z-20 w-80 p-4">
            <p className="label-caps">Signaler à l'équipe</p>
            <div className="mt-2 flex gap-1.5">
              {RETOUR_TYPES.map((t) => (
                <button key={t.key} data-retour-type={t.key} onClick={() => setType(t.key)}
                  className={`rounded-full border px-3 py-1 text-[11px] transition-colors duration-quick ${
                    type === t.key ? 'border-mint bg-mint/10 text-mint' : 'border-line-2 text-txt-mut hover:text-txt'}`}>
                  {t.label}
                </button>
              ))}
            </div>
            <textarea value={msg} onChange={(e) => setMsg(e.target.value)} rows={4} maxLength={2000}
              placeholder="Décrivez le bug, l'idée ou la question…" data-retour-message
              className="mt-3 w-full resize-none rounded-md border border-line-2 bg-bg p-2 text-xs text-txt outline-none focus:border-mint" />
            <div className="mt-2 flex items-center justify-between">
              <span className="text-[10px] text-txt-mut">Transmis avec votre licence — jamais anonyme.</span>
              <button data-retour-envoyer onClick={envoyer} disabled={msg.trim().length < 3 || busy}
                className="rounded-md border border-mint/40 bg-mint/10 px-3 py-1.5 text-xs text-mint transition-colors duration-quick disabled:opacity-40">
                {busy ? 'Envoi…' : 'Envoyer'}
              </button>
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
      {/* RETOURS-4 S6 — l'OISEAU part au sommet du rail ; le MOT-SYMBOLE reste ici, seul, AGRANDI (~29 px,
          gras) pour occuper l'espace libéré, et BICOLORE : « LA » blanc, « BUSE » vert. Un seul bloc de
          texte, aucun espace entre les deux moitiés. */}
      <div className="flex shrink-0 items-center pr-1" title="LABUSE — Radar foncier, La Réunion">
        <span data-logo className="font-display text-[29px] font-extrabold leading-none tracking-[.04em]">
          <span className="text-white">LA</span><span className="text-mint">BUSE</span>
        </span>
      </div>
      <Omnibox />
      <FilterChips />
      <div className="ml-auto flex items-center gap-3">
        <SignalerButton />
        <NotifBell />
        <AccountMenu />
      </div>
    </header>
  )
}
