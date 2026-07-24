import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { banAutocomplete, type BanFeature } from '../lib/api'

// M12-D1 — COMPOSANT D'AUTOCOMPLÉTION D'ADRESSE RÉUTILISABLE (mutualisé D2 + D3).
// Suggestions au fil de la frappe, adossées à la BAN (api-adresse.data.gouv.fr, publique).
// Sélectionner une suggestion renvoie TOUJOURS une adresse normalisée + coordonnées
// (jamais une chaîne libre) via onSelect. Navigation clavier (↑ ↓ Entrée Échap) + a11y
// (combobox / listbox ARIA). Debounce + annulation de la requête précédente.

export interface AddressSelection {
  label: string  // adresse normalisée BAN
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
  'data-testid'?: string
}

export function AddressAutocomplete({
  onSelect, placeholder = 'Saisissez une adresse…', autoFocus, className,
  onClear, onEnterRaw, ...rest
}: Props) {
  const [text, setText] = useState('')
  const [items, setItems] = useState<BanFeature[]>([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const [loading, setLoading] = useState(false)
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

  // Debounce + annulation : on ne garde que le dernier appel en vol.
  useEffect(() => {
    const needle = text.trim()
    if (needle.length < 3) { setItems([]); setOpen(false); setLoading(false); return }
    const ctrl = new AbortController()
    setLoading(true)
    const t = setTimeout(() => {
      banAutocomplete(needle, ctrl.signal)
        .then((r) => { setItems(r); setOpen(r.length > 0); setActive(-1) })
        .catch(() => { /* abort ou réseau : on n'affiche pas d'erreur bloquante */ })
        .finally(() => setLoading(false))
    }, 220)
    return () => { clearTimeout(t); ctrl.abort() }
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

  const pick = (f: BanFeature) => {
    setText(f.label)
    setItems([])
    setOpen(false)
    setActive(-1)
    onSelect({ label: f.label, lon: f.lon, lat: f.lat, idu: f.idu })
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
      if (open && active >= 0 && items[active]) pick(items[active])
      else if (open && items[0]) pick(items[0])   // Entrée sans surlignage → 1re suggestion
      else if (onEnterRaw) onEnterRaw(text.trim())
    } else if (e.key === 'Escape') {
      if (open) { e.stopPropagation(); setOpen(false) }
    }
  }

  return (
    <div ref={boxRef} className="relative min-w-0 flex-1">
      <input
        {...rest}
        ref={inputRef}
        autoFocus={autoFocus}
        value={text}
        onChange={(e) => {
          setText(e.target.value)
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
      {open && items.length > 0 && pos && createPortal(
        <ul
          ref={listRef}
          id={listId}
          role="listbox"
          style={{ position: 'fixed', left: pos.left, top: pos.top, minWidth: pos.width, maxWidth: Math.max(pos.width, 320) }}
          className="floating z-[1000] max-h-64 w-max overflow-y-auto p-1"
        >
          {items.map((f, i) => (
            <li
              key={`${f.lon},${f.lat},${i}`}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              onMouseDown={(e) => { e.preventDefault(); pick(f) }}
              onMouseEnter={() => setActive(i)}
              className={`cursor-pointer whitespace-nowrap rounded-md px-2.5 py-1.5 text-[11.5px] ${
                i === active ? 'bg-mint/15 text-txt-hi' : 'text-txt hover:bg-surface-3'
              }`}
            >
              <span>{f.label}</span>
              {f.type && f.type !== 'housenumber' && (
                <span className="ml-1.5 text-[9.5px] text-txt-dim">
                  {f.type === 'street' ? 'voie' : f.type === 'municipality' ? 'commune' : f.type === 'locality' ? 'lieu-dit' : f.type}
                </span>
              )}
            </li>
          ))}
        </ul>,
        document.body,
      )}
    </div>
  )
}
