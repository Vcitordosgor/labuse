import { useState } from 'react'
import { estIdu, iduComplet } from '../lib/format'
import { useApp } from '../store/useApp'
import { AddressAutocomplete } from './AddressAutocomplete'

// PATRON OMNIBOX (M137) — UN SEUL champ pour désigner une parcelle : adresse (autocomplétion BAN)
// ET IDU cadastral (reconnu par `estIdu` → on n'interroge pas la BAN dessus), comme l'omnibox de la
// carte. Chemin UNIQUE partagé par tous les outils (Étudier un bien, Courrier, Remonter le temps,
// Faisabilité via ParcelPicker, Risques…) — plus jamais deux champs ni deux onglets, plus de regex
// IDU recopiée par écran. Validation-legere en Enter (comme l'omnibox) ; le backend valide l'IDU.
//   • onPick(idu)   : une parcelle est désignée (adresse rattachée, IDU saisi/collé, ou clic carte).
//   • onAddress(q)  : une adresse SANS parcelle rattachée → repli géocodage (ex. Étudier un bien).
//                     Absent → on affiche le message honnête « aucune parcelle rattachée ».
export function ParcelInput({ onPick, onAddress, placeholder, autoFocus, withCarte = true, dataAttr }: {
  onPick: (idu: string) => void
  onAddress?: (label: string) => void
  placeholder?: string
  autoFocus?: boolean
  withCarte?: boolean
  dataAttr?: string                 // hook QA : pose data-<dataAttr> sur le champ (ex. « courrier-idu »)
}) {
  const selectedIdu = useApp((s) => s.selectedIdu)
  const [msg, setMsg] = useState<string | null>(null)
  const attr = dataAttr ? { [`data-${dataAttr}`]: '' } : {}
  return (
    <div className="flex flex-col gap-1.5">
      <AddressAutocomplete
        {...attr}
        autoFocus={autoFocus}
        placeholder={placeholder ?? 'Adresse ou IDU cadastral…'}
        onClear={() => setMsg(null)}
        onSelect={(sel) => {
          setMsg(null)
          if (sel.idu) onPick(iduComplet(sel.idu))
          else if (onAddress) onAddress(sel.label)
          else setMsg("Adresse trouvée, mais aucune parcelle cadastrale rattachée — saisissez l'IDU.")
        }}
        onEnterRaw={(raw) => {
          const qn = iduComplet(raw).toUpperCase()
          if (estIdu(qn)) { setMsg(null); onPick(qn) }
          else if (onAddress) { setMsg(null); onAddress(raw) }
          // sinon (adresse en cours) : l'autocomplétion guide déjà — pas de commit hasardeux.
        }}
      />
      {msg && <p data-parcelinput-msg className="text-[10.5px] text-st-creuser">{msg}</p>}
      {withCarte && selectedIdu && (
        <button data-parcelinput-carte onClick={() => { setMsg(null); onPick(selectedIdu) }}
          className="self-start text-[10.5px] text-mint hover:underline">
          utiliser la parcelle sélectionnée sur la carte ({selectedIdu.slice(8)})
        </button>
      )}
    </div>
  )
}
