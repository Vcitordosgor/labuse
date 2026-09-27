import { useEffect, useRef, useState } from 'react'
import { estIdu, estSectionNumero, iduComplet, iduCourt, normSectionNumero } from '../lib/format'
import { fmtM2 } from '../lib/format'
import { searchParcels, type SuggestItem, type SuggestType } from '../lib/api'
import { useApp } from '../store/useApp'
import { AddressAutocomplete } from './AddressAutocomplete'
import { OwnerParcelles } from './OwnerParcelles'

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
//
// RECHERCHE-2 Lot 1 (décision Vic) — LES QUATRE FAMILLES PAR DÉFAUT. Toute barre de recherche de
// l'app doit accepter et résoudre les trois familles (propriétaire nom/SIREN · parcelle IDU/réf ·
// adresse) et les PROPOSER à la frappe. `ParcelInput` déclare donc désormais les 4 grammaires
// (adresse, cadastre, propriétaire, SIREN) SANS exception (l'ancienne prop `grammaireProprietaire`
// disparaît). Un outil qui part d'une PARCELLE reçoit un pick propriétaire non pas comme une impasse
// mais comme un SOUS-PANNEAU qui liste ses parcelles (IDU · commune · surface, « voir N de plus »
// au-delà de 200) : l'utilisateur en choisit une, `onPick(idu)` est appelé comme un clic carte.
//   • onProprietaire(siren) : un outil qui part du PROPRIÉTAIRE (Scan patrimoine) le fournit → le
//     pick propriétaire lui est remonté DIRECTEMENT (pas de sous-panneau parcelle). Absent → sous-panneau.
type Candidate = { idu: string; commune: string; surface_m2: number | null }

// Les 4 grammaires du mandat, en CONSTANTE de module (référence stable → pas de relance d'effet).
// GEOPF-3 — 5ᵉ grammaire « lieu_dit » (BD NYME) active par défaut dans toutes les barres.
const GRAMMAIRES_DEFAUT: SuggestType[] = ['adresse', 'cadastre', 'proprietaire', 'siren', 'lieu_dit']

export function ParcelInput({ onPick, onAddress, onProprietaire, placeholder, autoFocus, withCarte = true, dataAttr, grammaires = GRAMMAIRES_DEFAUT }: {
  onPick: (idu: string) => void
  onAddress?: (label: string) => void
  // RECHERCHE-2 Lot 1 — remonte un pick PROPRIÉTAIRE (SIREN) au niveau propriétaire (Scan patrimoine).
  // Sans lui, un pick propriétaire déroule le sous-panneau « ses parcelles → onPick(idu) ».
  onProprietaire?: (siren: string, nom?: string) => void
  placeholder?: string
  autoFocus?: boolean
  withCarte?: boolean
  dataAttr?: string                 // hook QA : pose data-<dataAttr> sur le champ (ex. « courrier-idu »)
  grammaires?: SuggestType[]        // défaut = les 4 familles ; un appelant peut restreindre/étendre.
}) {
  const selectedIdu = useApp((s) => s.selectedIdu)
  const commune = useApp((s) => s.commune)
  const [msg, setMsg] = useState<string | null>(null)
  const [candidats, setCandidats] = useState<Candidate[] | null>(null)
  const [ref, setRef] = useState<string>('')      // la référence courte cherchée (pour le message)
  // RECHERCHE-2 Lot 1 — un pick propriétaire ouvre le sous-panneau PARTAGÉ « ses parcelles » (OwnerParcelles).
  const [owner, setOwner] = useState<{ siren: string; nom: string } | null>(null)
  // RETOURS-15 S2 — une parcelle est-elle RÉSOLUE par la barre (adresse, IDU, réf, parcelle d'un
  // propriétaire, ou clic carte consommé) ? Si oui, l'invite « Cliquez une parcelle sur la carte »
  // DISPARAÎT (elle réapparaît quand le champ est vidé). `seed` impose le libellé affiché (S1).
  const [resolu, setResolu] = useState(false)
  const [seed, setSeed] = useState<string | undefined>(undefined)
  const attr = dataAttr ? { [`data-${dataAttr}`]: '' } : {}

  const clearRepliques = () => { setMsg(null); setCandidats(null); setOwner(null) }
  const oublier = () => { clearRepliques(); setResolu(false) }   // champ vidé → tout retombe

  // RETOURS-15 S2/S4 — chemin de résolution UNIQUE : marque « résolu », affiche le libellé, remonte
  // l'IDU. `seedText` alimente le champ pour les chemins HORS suggestion (le clic de suggestion
  // recopie déjà son libellé) ; sans lui on laisse le texte tel quel (IDU/adresse déjà saisi).
  const resoudre = (idu: string, seedText?: string) => {
    clearRepliques()
    setResolu(true)
    if (seedText != null) setSeed(seedText)
    onPick(idu)
  }

  // RETOURS-15 S4 — le CLIC CARTE agit directement : plus de bouton « Utiliser la parcelle
  // sélectionnée ». Quand cette barre accepte le clic carte (`withCarte`), une NOUVELLE sélection
  // sur la carte est consommée comme un pick. On n'agit que sur un CHANGEMENT postérieur au montage
  // (ref initialisée à la sélection courante) : ni Assemblage (setMsel, `selectedIdu` inchangé) ni
  // Comparer (withCarte=false) ne passent par ici.
  const dernierClic = useRef<string | null>(selectedIdu)
  useEffect(() => {
    if (!withCarte) return
    if (selectedIdu && selectedIdu !== dernierClic.current) {
      dernierClic.current = selectedIdu
      resoudre(selectedIdu, iduComplet(selectedIdu))
    } else if (!selectedIdu) {
      dernierClic.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIdu, withCarte])

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
      if (exacts.length === 1) { resoudre(iduComplet(exacts[0].idu), iduCourt(exacts[0].idu)); return }
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
        placeholder={placeholder ?? 'Propriétaire, adresse, IDU ou référence (BW0917)'}
        grammaires={grammaires}
        seed={seed}
        onClear={oublier}
        // Un pick PROPRIÉTAIRE / SIREN (type ≠ adresse/cadastre → onPick d'AddressAutocomplete) :
        // remonté à onProprietaire s'il existe (outil propriétaire), sinon sous-panneau de ses parcelles.
        onPick={(it: SuggestItem) => {
          if ((it.type === 'proprietaire' || it.type === 'siren') && it.siren) {
            setMsg(null); setCandidats(null)
            if (onProprietaire) onProprietaire(it.siren, it.label)
            else setOwner({ siren: it.siren, nom: it.label })
          }
        }}
        onSelect={(sel) => {
          // le clic de suggestion a déjà recopié le libellé (S1) → pas de seed ici.
          if (sel.idu) resoudre(iduComplet(sel.idu))
          else if (onAddress) { clearRepliques(); onAddress(sel.label) }
          else { clearRepliques(); setMsg("Adresse trouvée, mais aucune parcelle cadastrale rattachée — saisissez l'IDU.") }
        }}
        onEnterRaw={(raw) => {
          const qn = iduComplet(raw).toUpperCase()
          if (estIdu(qn)) { resoudre(qn, qn) }
          // RETOURS-12 T1 — référence courte reconnue AVANT le repli adresse (sinon la BAN
          // répondrait « aucune adresse » à tort et l'utilisateur resterait dans le vide).
          else if (estSectionNumero(raw)) { setOwner(null); void resoudreRef(raw) }
          else if (onAddress) { clearRepliques(); onAddress(raw) }
          // sinon (adresse/nom en cours) : l'autocomplétion guide déjà — pas de commit hasardeux.
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
              onClick={() => resoudre(c.idu, iduCourt(c.idu))}
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
      {/* RECHERCHE-2 Lot 1/2 — SOUS-PANNEAU propriétaire PARTAGÉ : ses parcelles, on en choisit une
          (→ onPick, comme un clic carte) ; « voir N de plus » au-delà de 200 ; « changer » ferme. */}
      {owner && (
        <OwnerParcelles siren={owner.siren} nom={owner.nom}
          onPick={(idu) => resoudre(idu, iduCourt(idu))}
          onChanger={clearRepliques} />
      )}
      {/* RETOURS-15 S2/S4 — plus de bouton « Utiliser la parcelle sélectionnée » : le clic carte agit
          directement (l'effet ci-dessus le consomme). Il ne reste qu'une INVITE discrète au second
          geste ; elle DISPARAÎT dès qu'une parcelle est résolue par la barre (réapparaît si vidé). */}
      {withCarte && !resolu && (
        <div data-parcelinput-carte className="flex items-center gap-2 rounded-md border border-dashed border-line-2 bg-surface-2/40 px-3 py-2 text-[11px] text-txt-dim">
          <span aria-hidden="true">◎</span> ou cliquez une parcelle sur la carte
        </div>
      )}
    </div>
  )
}
