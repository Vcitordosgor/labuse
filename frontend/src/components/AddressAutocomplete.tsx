import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { rechercheSuggest, type SuggestItem, type SuggestType } from '../lib/api'

// DA-FIX-2 Lot 2 (DA-001) — rendu d'omnibox CANONIQUE (planche) : 40 px de haut, contour, rayon 6.
// C'est le rendu par défaut de TOUTES les barres parcelle (via ParcelInput). Le header garde son
// propre className (barre à loupe) mais la même métrique (son wrapper est passé à h-10).
const OMNIBOX_CLS = 'w-full h-10 rounded-md border border-line-2 bg-surface-3 px-3 text-[13px] text-txt placeholder:text-txt-dim focus:border-mint focus:outline-none'

// M12-D1 — LE composant de barre de recherche PARTAGÉ (mutualisé D2 + D3).
// RETOURS-16 V5 — il devient la SUGGESTION UNIFIÉE de l'app : un seul endpoint
// (/api/recherche/suggest, api/recherche.py), six grammaires typées (adresse · cadastre — IDU et
// référence courte · propriétaire · SIREN · commune · projet), groupées, 8 propositions max, le
// type en libellé discret à gauche. Chaque barre déclare via `grammaires` ce qu'elle sait
// consommer (défaut adresse+cadastre — les barres parcelle) ; AUCUNE barre ne garde son
// autocomplétion maison. Déclenchement à 2 caractères, anti-rebond 200 ms, annulation de la
// requête précédente. Navigation clavier (↑ ↓ Entrée Échap) + a11y (combobox/listbox ARIA).
// La frappe RESTE ce que l'utilisateur a tapé : une proposition ne se substitue qu'au CLIC ou à
// Entrée sur une ligne SÉLECTIONNÉE (l'auto-pick « Entrée → 1re suggestion » d'avant est retiré,
// doctrine V5.5 « ne jamais deviner à la place de l'utilisateur »).

export interface AddressSelection {
  label: string  // adresse normalisée BAN (ou libellé de la proposition choisie)
  lon: number
  lat: number
  idu: string | null  // M13-B1 : parcelle rattachée (source interne) — landing direct
}

interface Props {
  onSelect: (sel: AddressSelection) => void
  placeholder?: string
  autoFocus?: boolean
  className?: string           // classes de l'<input>
  /** appelé quand le champ est vidé / la sélection invalidée (l'appelant peut réinitialiser) */
  onClear?: () => void
  /** Entrée sur le champ SANS suggestion active (l'appelant décide : ex. géocoder la 1re) */
  onEnterRaw?: (text: string) => void
  /** V5 — grammaires que cette barre sait consommer (défaut : adresse + cadastre). */
  grammaires?: SuggestType[]
  /** V5 — sélection d'un type ÉTENDU (commune / propriétaire / SIREN / projet). Sans lui,
   *  commune retombe sur onSelect (recadrage lon/lat) ; les autres types ne devraient pas être
   *  demandés par une barre qui ne les gère pas. */
  onPick?: (item: SuggestItem) => void
  /** V5 — miroir de la frappe pour l'appelant (bouton « Chercher », blocs d'exemples…). */
  onTextChange?: (text: string) => void
  /** RETOURS-15 S1/S2 — l'appelant impose le texte du champ (parcelle résolue hors suggestion :
   *  clic carte, désambiguïsation, parcelle d'un propriétaire, IDU normalisé). Ne relance PAS la
   *  recherche. Les clics de suggestion recopient déjà leur libellé (pick) — seed sert aux AUTRES
   *  chemins de résolution, pour que « l'adresse/l'IDU choisi » s'affiche en entier dans la barre. */
  seed?: string
  'data-testid'?: string
}

const TYPE_LBL: Record<SuggestType, string> = {
  adresse: 'adresse', cadastre: 'parcelle', proprietaire: 'propriétaire',
  siren: 'SIREN', commune: 'commune', projet: 'projet', lieu_dit: 'lieu-dit',
}
const TYPE_FORMAT: Record<SuggestType, string> = {
  adresse: 'adresse', cadastre: 'IDU ou référence courte (BZ1065)', proprietaire: 'nom de propriétaire',
  siren: 'SIREN', commune: 'commune', projet: 'nom de projet', lieu_dit: 'lieu-dit',
}
const DEFAUT: SuggestType[] = ['adresse', 'cadastre']

export function AddressAutocomplete({
  onSelect, placeholder = 'Saisissez une adresse…', autoFocus, className,
  onClear, onEnterRaw, grammaires = DEFAUT, onPick, onTextChange, seed, ...rest
}: Props) {
  const [text, setText] = useState('')
  const [items, setItems] = useState<SuggestItem[]>([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const [loading, setLoading] = useState(false)
  // M55-B point 1 : la source a répondu 0 proposition → on le DIT (état vide honnête, avec les
  // formats acceptés — V5.6) au lieu du silence d'avant.
  const [noResults, setNoResults] = useState(false)
  // M137-R (bug scoreur) : une SÉLECTION recopie le libellé dans `text`, ce qui relance l'effet
  // de recherche — on saute la recherche qu'un pick provoque.
  const skipSearchRef = useRef(false)
  const boxRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const listId = useId()
  // M13-B1 : la liste est rendue en PORTAL (position: fixed) pour échapper aux ancêtres
  // `overflow-hidden` (le conteneur de contenu sous l'en-tête clippait le menu déroulant).
  const [pos, setPos] = useState<{ left: number; top: number; width: number } | null>(null)
  const measure = () => {
    const el = inputRef.current
    if (!el) return
    const r = el.getBoundingClientRect()
    setPos({ left: r.left, top: r.bottom + 4, width: r.width })
  }
  useEffect(() => {
    if (!open) return
    measure()
    const h = () => measure()
    window.addEventListener('resize', h)
    window.addEventListener('scroll', h, true)
    return () => { window.removeEventListener('resize', h); window.removeEventListener('scroll', h, true) }
  }, [open, items])

  // Anti-rebond 200 ms + annulation : on ne garde que le dernier appel en vol. Le serveur
  // aiguille par la FORME de la saisie (IDU/réf courte/SIREN/texte) — plus d'aiguillage local.
  useEffect(() => {
    if (skipSearchRef.current) { skipSearchRef.current = false; return }
    const needle = text.trim()
    if (needle.length < 2) { setItems([]); setOpen(false); setLoading(false); setNoResults(false); return }
    const ctrl = new AbortController()
    setLoading(true)
    const t = setTimeout(() => {
      rechercheSuggest(needle, grammaires, ctrl.signal)
        .then((r) => {
          const flat = r.groupes.flatMap((g) => g.items.map((i) => ({ ...i, type: g.type })))
          setItems(flat); setNoResults(flat.length === 0); setOpen(true); setActive(-1)
        })
        .catch(() => { /* abort ou réseau : on n'affiche pas d'erreur bloquante */ })
        .finally(() => setLoading(false))
    }, 200)
    return () => { clearTimeout(t); ctrl.abort() }
    // eslint-disable-next-line react-hooks/exhaustive-deps — `grammaires` est une constante d'appelant
  }, [text])

  // clic à l'extérieur (hors champ ET hors liste portée) → ferme la liste
  useEffect(() => {
    if (!open) return
    const h = (e: MouseEvent) => {
      const t = e.target as Node
      if (!boxRef.current?.contains(t) && !listRef.current?.contains(t)) setOpen(false)
    }
    window.addEventListener('mousedown', h)
    return () => window.removeEventListener('mousedown', h)
  }, [open])

  // RETOURS-15 S1/S2 — l'appelant impose le texte (résolution hors suggestion). On saute la
  // recherche que ce setText provoquerait, et on ferme toute liste ouverte.
  useEffect(() => {
    if (seed == null) return
    skipSearchRef.current = true
    setText(seed)
    setItems([]); setOpen(false); setActive(-1); setNoResults(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seed])

  const pick = (it: SuggestItem) => {
    if (it.note) return   // RECHERCHE-2 Lot 3 (b) — ligne d'information : rien à ouvrir, on ne fait rien.
    skipSearchRef.current = true   // le setText ci-dessous ne doit PAS relancer la recherche
    // RETOURS-15 S1/D5 — le champ reçoit l'adresse ENTIÈRE. Pour une adresse BAN, `label` ne porte que
    // le numéro + voie et `sub` le « code postal + commune » : les recoller (« 3 Chemin de la Citerne,
    // 97490 Saint-Denis ») pour que le libellé affiché ET remonté ne perde ni le CP ni la commune.
    const libelleComplet = it.type === 'adresse' && it.sub ? `${it.label}, ${it.sub}` : it.label
    setText(libelleComplet)
    onTextChange?.(libelleComplet)
    setItems([])
    setOpen(false)
    setActive(-1)
    setNoResults(false)
    // adresse + cadastre passent par onSelect (contrat historique : label/lon/lat/idu — tous les
    // appelants parcelle le consomment déjà) ; les types étendus vont à onPick, avec un repli
    // raisonnable pour commune (recadrage par coordonnées).
    if (it.type === 'adresse' || it.type === 'cadastre') {
      onSelect({ label: libelleComplet, lon: it.lon ?? 0, lat: it.lat ?? 0, idu: it.idu ?? null })
    } else if (it.type === 'lieu_dit' && it.lon != null && it.lat != null) {
      // GEOPF-3 — un lieu-dit n'est pas une parcelle : un clic ZOOME sur le secteur (recadrage lon/lat).
      onSelect({ label: it.label, lon: it.lon, lat: it.lat, idu: null })
    } else if (onPick) {
      onPick(it)
    } else if (it.type === 'commune' && it.lon != null && it.lat != null) {
      onSelect({ label: it.label, lon: it.lon, lat: it.lat, idu: null })
    }
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (!open && items.length) { setOpen(true); return }
      setActive((i) => Math.min(i + 1, items.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      // V5.5 — Entrée ne valide qu'une ligne SÉLECTIONNÉE ; sinon la saisie brute part à
      // l'appelant (résolution Entrée) : jamais la 1re suggestion à la place de l'utilisateur.
      if (open && active >= 0 && items[active]) pick(items[active])
      else if (onEnterRaw) onEnterRaw(text.trim())
    } else if (e.key === 'Escape') {
      if (open) { e.stopPropagation(); setOpen(false) }
    }
  }

  const formats = grammaires.map((g) => TYPE_FORMAT[g]).join(', ')
  return (
    <div ref={boxRef} className="relative min-w-0 flex-1">
      <input
        {...rest}
        data-suggest-input
        ref={inputRef}
        autoFocus={autoFocus}
        value={text}
        onChange={(e) => {
          setText(e.target.value)
          onTextChange?.(e.target.value)
          if (e.target.value.trim() === '') onClear?.()
        }}
        onKeyDown={onKeyDown}
        onFocus={() => { if (items.length) setOpen(true) }}
        placeholder={placeholder}
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={open && active >= 0 ? `${listId}-${active}` : undefined}
        autoComplete="off"
        spellCheck={false}
        className={className ?? OMNIBOX_CLS}
      />
      {loading && (
        <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-txt-dim" aria-hidden>…</span>
      )}
      {open && pos && (items.length > 0 || noResults) && createPortal(
        <ul
          ref={listRef}
          id={listId}
          role="listbox"
          style={{ position: 'fixed', left: pos.left, top: pos.top, minWidth: pos.width, maxWidth: Math.max(pos.width, 360) }}
          className="floating z-[1000] max-h-72 w-max overflow-y-auto p-1"
        >
          {/* V5.6 — zéro proposition n'est pas muet : les formats ACCEPTÉS par cette barre. */}
          {noResults && (
            <li role="option" aria-disabled data-suggest-vide className="max-w-[340px] px-2.5 py-1.5 text-[11.5px] leading-snug text-txt-dim">
              Aucune correspondance pour « {text.trim()} » — formats acceptés : {formats}.
            </li>
          )}
          {items.map((it, i) => (
            <li
              key={`${it.type}-${it.idu ?? it.siren ?? it.projet_id ?? it.label}-${i}`}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              aria-disabled={it.note || undefined}
              data-suggest-item={it.type}
              data-suggest-note={it.note || undefined}
              onMouseDown={(e) => { e.preventDefault(); pick(it) }}
              onMouseEnter={() => { if (!it.note) setActive(i) }}
              // survol/actif : la règle de l'app — VERT OPAQUE, contenu inversé (V5.3). Une ligne
              // d'information (note) reste grisée, non cliquable (curseur défaut, pas de vert).
              className={`flex items-baseline gap-2 whitespace-nowrap rounded-md px-2.5 py-1.5 text-[11.5px] ${
                it.note ? 'cursor-default text-txt-dim' : i === active ? 'cursor-pointer bg-mint text-mint-ink' : 'cursor-pointer text-txt'
              }`}
            >
              {/* le TYPE en libellé discret à gauche, l'essentiel en clair (V5.3) */}
              <span className={`w-[74px] shrink-0 text-[9.5px] uppercase tracking-wide ${!it.note && i === active ? 'text-mint-ink/70' : 'text-txt-dim'}`}>
                {TYPE_LBL[it.type]}
              </span>
              <span className="min-w-0 truncate">{it.label}</span>
              {it.sub && <span className={`text-[10px] ${!it.note && i === active ? 'text-mint-ink/70' : 'text-txt-dim'}`}>{it.sub}</span>}
            </li>
          ))}
        </ul>,
        document.body,
      )}
    </div>
  )
}
