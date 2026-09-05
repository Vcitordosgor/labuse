import { useState } from 'react'
import { estIdu, estSectionNumero, iduComplet, iduCourt, normSectionNumero } from '../lib/format'
import { fmtM2 } from '../lib/format'
import { searchParcels } from '../lib/api'
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
//
// RETOURS-12 T1 — RÉFÉRENCE CADASTRALE COURTE (« BW0917 »). Ce champ, partagé par la quasi-totalité
// des outils, refusait tout ce qui n'était ni un IDU 14 ni une adresse : la référence courte que les
// pros citent le plus tombait dans le vide. Désormais on la reconnaît (estSectionNumero), on résout via
// /parcels/search (fin d'IDU, île entière), et on DÉSAMBIGUÏSE : une même section+numéro existe dans
// plusieurs communes → on rend la liste (commune + surface), l'utilisateur tranche ; la commune du
// contexte (si connue) est présélectionnée en tête sans masquer les autres. Jamais de choix au hasard,
// jamais un zéro muet.
type Candidate = { idu: string; commune: string; surface_m2: number | null }

export function ParcelInput({ onPick, onAddress, placeholder, autoFocus, withCarte = true, dataAttr }: {
  onPick: (idu: string) => void
  onAddress?: (label: string) => void
  placeholder?: string
  autoFocus?: boolean
  withCarte?: boolean
  dataAttr?: string                 // hook QA : pose data-<dataAttr> sur le champ (ex. « courrier-idu »)
}) {
  const selectedIdu = useApp((s) => s.selectedIdu)
  const commune = useApp((s) => s.commune)
  const [msg, setMsg] = useState<string | null>(null)
  const [candidats, setCandidats] = useState<Candidate[] | null>(null)
  const [ref, setRef] = useState<string>('')      // la référence courte cherchée (pour le message)
  const attr = dataAttr ? { [`data-${dataAttr}`]: '' } : {}

  // Résout une référence courte (section+numéro) via /parcels/search. Présélectionne la commune
  // du contexte en tête. 0 → message honnête ; 1 → onPick direct ; N → liste de désambiguïsation.
  const resoudreRef = async (raw: string) => {
    const needle = normSectionNumero(raw)
    setRef(raw.trim().toUpperCase())
    setCandidats(null)
    try {
      const rows = await searchParcels(needle, { ileEntiere: true })
      const exacts = rows.filter((r) => iduComplet(r.idu).toUpperCase().endsWith(needle))
      if (exacts.length === 0) {
        setMsg(`Aucune parcelle « ${raw.trim().toUpperCase()} » (référence section + numéro) sur l'île.`)
        return
      }
      if (exacts.length === 1) { setMsg(null); onPick(iduComplet(exacts[0].idu)); return }
      // désambiguïsation : commune du contexte d'abord, puis les autres
      const tri = [...exacts].sort((a, b) =>
        (b.commune === commune ? 1 : 0) - (a.commune === commune ? 1 : 0) || a.commune.localeCompare(b.commune))
      setMsg(null)
      setCandidats(tri.map((r) => ({ idu: iduComplet(r.idu), commune: r.commune, surface_m2: r.surface_m2 })))
    } catch {
      setMsg('Recherche indisponible pour le moment — réessayez.')
    }
  }

  return (
    <div className="flex flex-col gap-1.5">
      <AddressAutocomplete
        {...attr}
        autoFocus={autoFocus}
        placeholder={placeholder ?? 'Adresse, IDU ou référence cadastrale (BW0917)…'}
        onClear={() => { setMsg(null); setCandidats(null) }}
        onSelect={(sel) => {
          setMsg(null); setCandidats(null)
          if (sel.idu) onPick(iduComplet(sel.idu))
          else if (onAddress) onAddress(sel.label)
          else setMsg("Adresse trouvée, mais aucune parcelle cadastrale rattachée — saisissez l'IDU.")
        }}
        onEnterRaw={(raw) => {
          const qn = iduComplet(raw).toUpperCase()
          if (estIdu(qn)) { setMsg(null); setCandidats(null); onPick(qn) }
          // RETOURS-12 T1 — référence courte reconnue AVANT le repli adresse (sinon la BAN
          // répondrait « aucune adresse » à tort et l'utilisateur resterait dans le vide).
          else if (estSectionNumero(raw)) { void resoudreRef(raw) }
          else if (onAddress) { setMsg(null); setCandidats(null); onAddress(raw) }
          // sinon (adresse en cours) : l'autocomplétion guide déjà — pas de commit hasardeux.
        }}
      />
      {msg && <p data-parcelinput-msg className="text-[10.5px] text-st-creuser">{msg}</p>}
      {candidats && candidats.length > 0 && (
        <div data-parcelinput-candidats className="flex flex-col gap-0.5 rounded-md border border-line-2 bg-surface-2 p-1.5">
          <p className="px-1 pb-0.5 text-[10px] text-txt-dim">
            « {ref} » existe dans {candidats.length} communes — choisissez :
          </p>
          {candidats.map((c) => (
            <button key={c.idu} data-parcelinput-candidat
              onClick={() => { setCandidats(null); setMsg(null); onPick(c.idu) }}
              className="hover-fill flex items-baseline justify-between gap-2 rounded px-2 py-1 text-left text-[11px] text-txt transition-colors duration-quick">
              <span className="font-medium text-txt-hi">{c.commune}</span>
              <span className="flex items-baseline gap-2 text-[10px] text-txt-dim">
                <span>{fmtM2(c.surface_m2)}</span>
                <span className="font-mono">{iduCourt(c.idu)}</span>
              </span>
            </button>
          ))}
        </div>
      )}
      {withCarte && selectedIdu && (
        <button data-parcelinput-carte onClick={() => { setMsg(null); setCandidats(null); onPick(selectedIdu) }}
          className="self-start text-[10.5px] text-mint hover:underline">
          utiliser la parcelle sélectionnée sur la carte ({selectedIdu.slice(8)})
        </button>
      )}
    </div>
  )
}
