import { ParcelInput } from '../ParcelInput'

/** M15-C — désignation d'UNE parcelle. Depuis M137 (patron omnibox), c'est UN SEUL champ (adresse OU
 *  IDU) + le clic carte, via le composant partagé ParcelInput — plus de champ IDU séparé. Émet
 *  onPick(idu) dès qu'une parcelle est désignée. Aucun calcul ici — c'est un sélecteur. */
export function ParcelPicker({ onPick, picked }: { onPick: (idu: string) => void; picked: string | null }) {
  return (
    <div className="flex flex-col gap-1.5 rounded-lg border border-line-2 bg-surface-2 px-2.5 py-2">
      <p className="text-[10.5px] text-txt-mut">Désignez une parcelle — <b>adresse</b>, <b>IDU</b>, ou <b>clic sur la carte</b> :</p>
      <ParcelInput dataAttr="picker-idu" onPick={(idu) => { if (idu !== picked) onPick(idu) }}
        placeholder="Adresse ou IDU — 97415000CW0658" />
    </div>
  )
}
