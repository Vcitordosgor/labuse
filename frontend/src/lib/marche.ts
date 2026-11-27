// OUTIL-COMMUNES-FIX-11 LOT 1 — en-tête Marché COHÉRENT : prix + type + effectif + périmètre d'UNE
// SEULE série. Extrait en fonction PURE (testable) pour garantir qu'on ne mélange plus le prix du bâti
// avec l'effectif/périmètre du terrain (défaut ASTRA-8 §1 : « 2947 €/m² · 1 vente · section cadastrale »
// où 2947 = maisons sur 10 ventes à 500 m).
import { fmtInt } from './format'

/** Secteur TERRAIN NU servi par la fiche (`dvf_parcelle.secteur[type='terrain']`). */
export interface TerrainSecteur { mediane_prix_m2: number | null; n_ventes: number | null; perimetre?: string | null }
/** Série « ancien » (bâti) de `faisa.marche` : même type/effectif/rayon que la médiane servie. */
export interface MarcheAncien {
  median?: number | null; n?: number | null; radius_m?: number | null
  commune_fallback?: boolean; type_prix?: string | null
}
export interface EnteteMarche {
  serie: 'terrain' | 'ancien' | 'aucune'; valeur: string; contexte: string
  terrainInsuffisant: string | null
  // OUTIL-COMMUNES-FIX-13 LOT 5 — la MÉTHODE (« recherche mixte ») descend dans le DÉTAIL : l'en-tête
  // dit ce qui est RETENU (« 10 maisons »), le détail dit comment ça a été cherché. null si rien à dire.
  methode: string | null
}

const _vent = (n: number) => `${n} vente${n > 1 ? 's' : ''}`

/** OUTIL-COMMUNES-FIX-13 LOT 5 — décompose un `type_prix` servi (« maisons (recherche mixte) ») en
 *  TYPE retenu nu (« maisons ») + MÉTHODE (« recherche mixte »). Le back nomme déjà le lot RÉELLEMENT
 *  retenu (FIX-12 LOT 4 : « mixte » seulement si maisons ET appartements) ; ici on ne fait que RANGER
 *  la parenthèse de méthode dans le détail, pour que l'en-tête reste court (« 10 maisons »). */
function _typeEtMethode(typePrix: string | null | undefined): { type: string; methode: string | null } {
  const tp = (typePrix ?? 'ancien').trim()
  const m = /^(.*?)\s*\((recherche mixte)\)\s*$/i.exec(tp)
  return m ? { type: m[1].trim(), methode: m[2].toLowerCase() } : { type: tp, methode: null }
}

/** RÈGLE : terrain nu diffusable (médiane ≥ seuil) → série TERRAIN (prix + n + section) ; sinon repli
 *  sur l'ANCIEN (bâti) AVEC SON propre effectif/rayon/type ; terrain sous le seuil dit À PART. */
export function enteteMarche(terrain: TerrainSecteur | null | undefined, mb: MarcheAncien | null | undefined): EnteteMarche {
  const tN = terrain?.n_ventes ?? 0
  const tServable = terrain != null && terrain.mediane_prix_m2 != null
  const mbMed = mb?.median
  const mbN = mb?.n ?? 0
  const mbRayon = mb?.commune_fallback ? 'commune entière' : (mb?.radius_m != null ? `rayon ${fmtInt(mb.radius_m)} m` : null)
  let serie: EnteteMarche['serie'] = 'aucune'
  let valeur = '—'
  let contexte = 'comparables DVF'
  let methode: string | null = null
  if (tServable) {
    serie = 'terrain'
    valeur = `${fmtInt(terrain!.mediane_prix_m2)} €/m²`
    contexte = `terrain nu · ${_vent(tN)}${terrain?.perimetre ? ` · ${terrain.perimetre}` : ''} · DVF`
  } else if (mbMed != null) {
    serie = 'ancien'
    valeur = `${fmtInt(Number(mbMed))} €/m²`
    // FIX-13 LOT 5 — en-tête COURT : « {n} {type} » (ex. « 10 maisons ») quand le type est homogène et
    // trouvé par recherche mixte ; la méthode part au détail. Sinon libellé servi tel quel (ex. « mixte »).
    const { type: typeNu, methode: meth } = _typeEtMethode(mb?.type_prix)
    methode = meth
    const tete = meth ? `${mbN} ${typeNu}` : `${mb?.type_prix ?? 'ancien'} · ${_vent(mbN)}`
    contexte = `${tete}${mbRayon ? ` · ${mbRayon}` : ''} · DVF`
  }
  // terrain sous le seuil : dit À PART (jamais mêlé au prix affiché en tête).
  const terrainInsuffisant = (!tServable && tN > 0)
    ? `terrain : échantillon insuffisant, ${_vent(tN)}${terrain?.perimetre ? ` (${terrain.perimetre})` : ''}`
    : null
  return { serie, valeur, contexte, terrainInsuffisant, methode }
}
