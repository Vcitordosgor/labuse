import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { rechercheSuggest, type SuggestItem, type SuggestType } from '../lib/api'

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
  'data-testid'?: string
}

const TYPE_LBL: Record<SuggestType, string> = {
  adresse: 'adresse', cadastre: 'parcelle', proprietaire: 'propriétaire',
  siren: 'SIREN', commune: 'commune', projet: 'projet',
}
const TYPE_FORMAT: Record<SuggestType, string> = {
  adresse: 'adresse', cadastre: 'IDU ou référence courte (BZ1065)', proprietaire: 'nom de propriétaire',
  siren: 'SIREN', commune: 'commune', projet: 'nom de projet',
}
const DEFAUT: SuggestType[] = ['adresse', 'cadastre']

export function AddressAutocomplete({
  onSelect, placeholder = 'Saisissez une adresse…', autoFocus, className,
  onClear, onEnterRaw, grammaires = DEFAUT, onPick, onTextChange, ...rest
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

  const pick = (it: SuggestItem) => {
    skipSearchRef.current = true   // le setText ci-dessous ne doit PAS relancer la recherche
    setText(it.label)
    onTextChange?.(it.label)
    setItems([])
    setOpen(false)
    setActive(-1)
    setNoResults(false)
    // adresse + cadastre passent par onSelect (contrat historique : label/lon/lat/idu — tous les
    // appelants parcelle le consomment déjà) ; les types étendus vont à onPick, avec un repli
    // raisonnable pour commune (recadrage par coordonnées).
    if (it.type === 'adresse' || it.type === 'cadastre') {
      onSelect({ label: it.label, lon: it.lon ?? 0, lat: it.lat ?? 0, idu: it.idu ?? null })
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
        className={className ?? 'w-full rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-xs text-txt placeholder:text-txt-dim focus:border-mint focus:outline-none'}
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
              data-suggest-item={it.type}
              onMouseDown={(e) => { e.preventDefault(); pick(it) }}
              onMouseEnter={() => setActive(i)}
              // survol/actif : la règle de l'app — VERT OPAQUE, contenu inversé (V5.3).
              className={`flex cursor-pointer items-baseline gap-2 whitespace-nowrap rounded-md px-2.5 py-1.5 text-[11.5px] ${
                i === active ? 'bg-mint text-mint-ink' : 'text-txt'
              }`}
            >
              {/* le TYPE en libellé discret à gauche, l'essentiel en clair (V5.3) */}
              <span className={`w-[74px] shrink-0 text-[9.5px] uppercase tracking-wide ${i === active ? 'text-mint-ink/70' : 'text-txt-dim'}`}>
                {TYPE_LBL[it.type]}
              </span>
              <span className="min-w-0 truncate">{it.label}</span>
              {it.sub && <span className={`text-[10px] ${i === active ? 'text-mint-ink/70' : 'text-txt-dim'}`}>{it.sub}</span>}
            </li>
          ))}
        </ul>,
        document.body,
      )}
    </div>
  )
}
