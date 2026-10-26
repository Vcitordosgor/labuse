// RECETTE-1 (F2, Vic 04/10) — LE composant d'entrée « une parcelle » des outils : UN champ
// « Adresse, IDU ou référence » OU « cliquez une parcelle sur la carte ». Dès qu'UNE entrée est
// utilisée, l'AUTRE se grise (non cliquable, opacité 40 %). Présentationnel : l'outil tient l'état
// (`picked`, `source`) — le champ émet `onPick(idu, 'adresse')`, et l'outil câble le clic carte en
// appelant `onPick(idu, 'carte')` (idiome parcelPrefill / selectedIdu partagé).
//
// RECETTE-OUTILS-1 (T4 + T5) — dès qu'une parcelle est choisie (saisie OU clic carte), le bloc de
// recherche DISPARAÎT et laisse place à UNE ligne : « adresse complète · Changer de parcelle » (lien
// secondaire jaune). C'est aussi la réponse à T4 : un clic carte passe par le MÊME chemin de pick que
// la saisie (l'outil adopte selectedIdu → `picked`), donc l'adresse de la parcelle cliquée s'affiche
// « comme si elle avait été saisie ». L'adresse complète (avec code postal) est résolue ici même
// (searchParcels sur l'IDU) si l'outil ne la fournit pas. « Changer de parcelle » vide l'outil
// (callback `onChanger`) et réaffiche le bloc de recherche — il REMPLACE l'ancien bouton « Réinitialiser ».
import { useQuery } from '@tanstack/react-query'
import { ParcelInput } from '../ParcelInput'
import { Bouton } from '../ui/Bouton'
import { searchParcels } from '../../lib/api'
import { iduCourt } from '../../lib/format'

export type SourceParcelle = 'adresse' | 'carte' | null

export function EntreeParcelle({ source, onPick, placeholder, titre, picked, adresse, onChanger }: {
  source: SourceParcelle
  onPick: (idu: string, src: 'adresse' | 'carte') => void
  placeholder?: string
  titre?: string
  /** RECETTE-OUTILS-1 (T5) — IDU de la parcelle choisie : si fourni, on affiche la ligne « adresse ·
   *  Changer de parcelle » au lieu du bloc de recherche. */
  picked?: string | null
  /** adresse complète déjà connue de l'outil (sinon résolue ici via l'IDU). */
  adresse?: string | null
  /** vide l'outil et réaffiche le bloc de recherche (remplace « Réinitialiser »). */
  onChanger?: () => void
}) {
  // T5 — résolution de l'adresse complète (avec code postal) quand l'outil ne la passe pas.
  const addrQ = useQuery({
    queryKey: ['entree-adresse', picked],
    queryFn: () => searchParcels(picked!, { ileEntiere: true }),
    enabled: !!picked && !adresse,
    staleTime: 5 * 60_000,
  })

  if (picked) {
    const adresseAffichee = adresse ?? addrQ.data?.[0]?.adresse ?? iduCourt(picked)
    return (
      <div data-entree-parcelle-choisie className="flex items-center justify-between gap-2 rounded-lg border border-line-2 bg-surface-2 px-2.5 py-2">
        <span className="min-w-0 flex-1 truncate text-[12px] text-txt" title={adresseAffichee}>{adresseAffichee}</span>
        {onChanger && (
          <Bouton niveau="lien" ton="ambre" data-entree-changer onClick={onChanger} className="shrink-0">
            Changer de parcelle
          </Bouton>
        )}
      </div>
    )
  }

  const champGrise = source === 'carte'    // la carte a désigné la parcelle → champ grisé
  const carteGrisee = source === 'adresse'  // le champ a désigné la parcelle → invite carte grisée
  return (
    <div data-entree-parcelle className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-2 px-2.5 py-2">
      {titre && <p className="text-[10.5px] text-txt-mut">{titre}</p>}
      <div className={champGrise ? 'pointer-events-none select-none opacity-40' : ''}
        aria-disabled={champGrise || undefined}>
        <ParcelInput dataAttr="entree-parcelle" withCarte={false} onPick={(idu) => { if (!champGrise) onPick(idu, 'adresse') }}
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
