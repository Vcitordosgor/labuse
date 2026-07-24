import { useEffect, useId, useRef, useState } from 'react'
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
  const listId = useId()

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

  // clic à l'extérieur → ferme la liste
  useEffect(() => {
    if (!open) return
    const h = (e: MouseEvent) => { if (!boxRef.current?.contains(e.target as Node)) setOpen(false) }
    window.addEventListener('mousedown', h)
    return () => window.removeEventListener('mousedown', h)
  }, [open])

  const pick = (f: BanFeature) => {
    setText(f.label)
    setItems([])
    setOpen(false)
    setActive(-1)
    onSelect({ label: f.label, lon: f.lon, lat: f.lat })
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
      {open && items.length > 0 && (
        <ul
          id={listId}
          role="listbox"
          className="floating absolute left-0 right-0 top-[calc(100%+4px)] z-50 max-h-64 overflow-y-auto p-1"
        >
          {items.map((f, i) => (
            <li
              key={`${f.lon},${f.lat},${i}`}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              onMouseDown={(e) => { e.preventDefault(); pick(f) }}
              onMouseEnter={() => setActive(i)}
              className={`cursor-pointer rounded-md px-2.5 py-1.5 text-[11.5px] ${
                i === active ? 'bg-mint/15 text-txt-hi' : 'text-txt hover:bg-surface-3'
              }`}
            >
              <span className="truncate">{f.label}</span>
              {f.type && f.type !== 'housenumber' && (
                <span className="ml-1.5 text-[9.5px] text-txt-dim">
                  {f.type === 'street' ? 'voie' : f.type === 'municipality' ? 'commune' : f.type === 'locality' ? 'lieu-dit' : f.type}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
