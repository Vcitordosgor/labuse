import { useState } from 'react'
import { useApp } from '../../store/useApp'
import { AddressAutocomplete } from '../AddressAutocomplete'

/** M15-C — désignation d'UNE parcelle par 2 entrées : barre IDU/adresse + clic sur la carte.
 *  Émet onPick(idu) dès qu'une parcelle valide est choisie. Aucun calcul ici — c'est un sélecteur. */
export function ParcelPicker({ onPick, picked }: { onPick: (idu: string) => void; picked: string | null }) {
  const selectedIdu = useApp((s) => s.selectedIdu)
  const [idu, setIdu] = useState('')
  const [addrMsg, setAddrMsg] = useState<string | null>(null)
  const submit = (v: string) => { const t = v.trim(); if (t.length >= 10) { onPick(t); setIdu('') } }
  return (
    <div className="flex flex-col gap-1.5 rounded-lg border border-line-2 bg-surface-2 px-2.5 py-2">
      <p className="text-[10.5px] text-txt-mut">Désignez une parcelle — <b>IDU</b>, <b>adresse</b>, ou <b>clic sur la carte</b> :</p>
      <div className="flex gap-1.5">
        <input data-picker-idu value={idu} onChange={(e) => { setIdu(e.target.value.trim()); setAddrMsg(null) }}
          onKeyDown={(e) => { if (e.key === 'Enter') submit(idu) }}
          placeholder="IDU — 97415000CW0658"
          className="min-w-0 flex-1 rounded border border-line-2 bg-surface-3 px-2 py-1 font-mono text-[10.5px] text-txt focus:border-mint focus:outline-none" />
        <button data-picker-go onClick={() => submit(idu)} disabled={idu.trim().length < 10}
          className="shrink-0 rounded border border-mint/40 px-2 text-[11px] text-mint transition-colors duration-quick hover:bg-mint/10 disabled:opacity-40">voir</button>
      </div>
      {/* entrée « adresse » : autocomplétion → parcelle rattachée (source interne) */}
      <AddressAutocomplete placeholder="… ou une adresse"
        onSelect={(sel) => { if (sel.idu) { onPick(sel.idu); setAddrMsg(null) } else setAddrMsg("Adresse trouvée, mais aucune parcelle cadastrale rattachée — saisissez l'IDU.") }} />
      {addrMsg && <p data-picker-addrmsg className="text-[10.5px] text-st-creuser">{addrMsg}</p>}
      {/* entrée « clic carte » : la dernière parcelle sélectionnée sur la carte */}
      {selectedIdu && selectedIdu !== picked && (
        <button data-picker-sel onClick={() => onPick(selectedIdu)}
          className="self-start text-[10.5px] text-mint hover:underline">utiliser la parcelle sélectionnée sur la carte ({selectedIdu.slice(8)})</button>
      )}
    </div>
  )
}
