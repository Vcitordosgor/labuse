// RECETTE-1 (F2, Vic 04/10) — LE composant d'entrée « une parcelle » des outils : UN champ
// « Adresse, IDU ou référence » OU « cliquez une parcelle sur la carte ». Dès qu'UNE entrée est
// utilisée, l'AUTRE se grise (non cliquable, opacité 40 %). Présentationnel : l'outil tient l'état
// (`picked`, `source`) — le champ émet `onPick(idu, 'adresse')`, et l'outil câble le clic carte en
// appelant `onPick(idu, 'carte')` (idiome parcelPrefill / selectedIdu partagé).
//
// RECETTE-OUTILS-1 (T4) + RETOURS-26 (pt 7) — dès qu'une parcelle est choisie (saisie OU clic carte), le
// champ de recherche RESTE rempli sous forme de BOÎTE PARCELLE (maquette 10-boite-parcelle, option A) :
// adresse entière en gras (jamais coupée) + « IDU · zone · surface » dessous, avec une CROIX (✕) à droite
// qui vide le champ (callback `onChanger`) et réaffiche la recherche. PLUS de bouton/lien « Changer de
// parcelle ». T4 : un clic carte passe par le MÊME chemin de pick que la saisie (l'outil adopte
// selectedIdu → `picked`), donc l'adresse de la parcelle cliquée s'affiche « comme si elle avait été
// saisie ». L'adresse complète (code postal), la zone PLU et la surface sont résolues ici même
// (searchParcels sur l'IDU) si l'outil ne les fournit pas.
import { useQuery } from '@tanstack/react-query'
import { ParcelInput } from '../ParcelInput'
import { searchParcels } from '../../lib/api'
import { iduCourt, fmtM2 } from '../../lib/format'

export type SourceParcelle = 'adresse' | 'carte' | null

export function EntreeParcelle({ source, onPick, placeholder, titre, picked, adresse, onChanger, viderApresPick }: {
  source: SourceParcelle
  onPick: (idu: string, src: 'adresse' | 'carte') => void
  placeholder?: string
  titre?: string
  /** RETOURS-17 — outil multi-parcelles (Comparer) : le champ se vide après chaque ajout. */
  viderApresPick?: boolean
  /** RETOURS-26 (pt 7) — IDU de la parcelle choisie : si fourni, on affiche la BOÎTE PARCELLE remplie
   *  (adresse + IDU · zone · surface + croix ✕) au lieu du bloc de recherche. */
  picked?: string | null
  /** adresse complète déjà connue de l'outil (sinon résolue ici via l'IDU). */
  adresse?: string | null
  /** la croix (✕) de la boîte vide le champ et réaffiche la recherche. */
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
    // RETOURS-26 (pt 7) — BOÎTE PARCELLE UNIQUE, option A (maquette 10-boite-parcelle) : le champ RESTE
    // rempli — adresse ENTIÈRE en gras (passe à la ligne si besoin, jamais coupée), puis « IDU · zone ·
    // surface » dessous — avec une CROIX à droite qui le vide (onChanger). Plus de bouton/lien « Changer
    // de parcelle ». La croix réaffiche le champ : on tape une autre adresse ou on clique la carte.
    const hit = addrQ.data?.[0]
    const adrPleine = adresse ?? hit?.adresse ?? null
    const idCourt = iduCourt(picked)
    const zone = hit?.zone_plu ?? null
    const surf = hit?.surface_terrain_m2 ?? hit?.surface_m2 ?? null
    const meta = [idCourt, zone, surf != null ? fmtM2(surf) : null].filter(Boolean).join(' · ')
    return (
      <div className="flex flex-col gap-1">
        {titre && <p className="text-[10.5px] text-txt-mut">{titre}</p>}
        <div data-entree-parcelle-choisie className="flex items-start gap-2 rounded-lg border border-mint/50 bg-surface-2 px-2.5 py-2">
          <span aria-hidden="true" className="mt-0.5 shrink-0 text-mint">◎</span>
          <div className="min-w-0 flex-1">
            <div className="break-words text-[12px] font-semibold leading-snug text-txt-hi">{adrPleine ?? idCourt}</div>
            <div data-entree-meta className="mt-0.5 break-words font-mono text-[10px] text-txt-dim">
              {adrPleine ? meta : [zone, surf != null ? fmtM2(surf) : null].filter(Boolean).join(' · ')}
            </div>
          </div>
          {onChanger && (
            <button data-entree-vider onClick={onChanger} aria-label="Vider le champ — choisir une autre parcelle"
              className="-mr-0.5 -mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-line-2 text-[11px] text-txt-mut transition-colors duration-quick hover:border-mint hover:text-txt-hi">
              ✕
            </button>
          )}
        </div>
        {onChanger && (
          <p className="px-0.5 text-[10px] leading-snug text-txt-dim">La croix vide le champ : tapez une autre adresse, ou cliquez une parcelle sur la carte.</p>
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
        <ParcelInput dataAttr="entree-parcelle" withCarte={false} viderApresPick={viderApresPick} onPick={(idu) => { if (!champGrise) onPick(idu, 'adresse') }}
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
