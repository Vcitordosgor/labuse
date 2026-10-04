// RECETTE-1 (F2, Vic 04/10) — LE composant d'entrée « une parcelle » des outils : UN champ
// « Adresse, IDU ou référence » OU « cliquez une parcelle sur la carte ». Dès qu'UNE entrée est
// utilisée, l'AUTRE se grise (non cliquable, opacité 40 %) ; les deux reviennent avec Réinitialiser
// (F3). Présentationnel : l'outil tient l'état (`picked`, `source`) — le champ émet `onPick(idu,
// 'adresse')`, et l'outil câble le clic carte en appelant `onPick(idu, 'carte')` (idiome parcelPrefill
// / selectedIdu partagé). Remplace les doublons « champ + invite carte » recopiés dans chaque outil.
import { ParcelInput } from '../ParcelInput'

export type SourceParcelle = 'adresse' | 'carte' | null

export function EntreeParcelle({ source, onPick, placeholder, titre }: {
  source: SourceParcelle
  onPick: (idu: string, src: 'adresse' | 'carte') => void
  placeholder?: string
  titre?: string
}) {
  const champGrise = source === 'carte'    // la carte a désigné la parcelle → champ grisé
  const carteGrisee = source === 'adresse'  // le champ a désigné la parcelle → invite carte grisée
  return (
    <div data-entree-parcelle className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-2 px-2.5 py-2">
      {titre && <p className="text-[10.5px] text-txt-mut">{titre}</p>}
      <div className={champGrise ? 'pointer-events-none select-none opacity-40' : ''}
        aria-disabled={champGrise || undefined}>
        <ParcelInput dataAttr="entree-parcelle" onPick={(idu) => { if (!champGrise) onPick(idu, 'adresse') }}
          placeholder={placeholder ?? 'Adresse, IDU ou référence (BW0917)'} />
      </div>
      <div data-entree-carte
        className={`flex items-center gap-1.5 text-[10.5px] leading-snug ${carteGrisee ? 'select-none opacity-40' : 'text-txt-mut'}`}
        aria-disabled={carteGrisee || undefined}>
        <span className="font-mono text-txt-dim">— ou —</span>
        <span>cliquez une parcelle sur la carte</span>
      </div>
    </div>
  )
}

export default EntreeParcelle
