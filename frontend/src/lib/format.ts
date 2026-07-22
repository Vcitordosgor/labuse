/** LOI-3 (revue UI/UX) — LES formats de l'app. Un nombre, une date, un montant :
 *  le même dessin partout (fr-FR, insécables, unités collées au chiffre).
 *  Aucun `toLocaleString` inline dans les surfaces : on passe par ici. */

/** entier groupé fr : 431 663 */
export const fmtInt = (n: number | null | undefined): string =>
  n == null ? '—' : Math.round(n).toLocaleString('fr-FR')

/** décimal fr à p décimales (défaut 1) : 63,9 */
export const fmtDec = (n: number | null | undefined, p = 1): string =>
  n == null ? '—' : n.toLocaleString('fr-FR', { minimumFractionDigits: p, maximumFractionDigits: p })

/** montant € entier : 245 000 € (espace insécable avant €) */
export const fmtEur = (n: number | null | undefined): string =>
  n == null ? '—' : `${fmtInt(n)} €`

/** surface : 1 245 m² / 2,50 ha au-delà d'un hectare */
export const fmtM2 = (m2: number | null | undefined): string =>
  m2 == null ? '—' : m2 >= 10_000 ? `${fmtDec(m2 / 10_000, 2)} ha` : `${fmtInt(m2)} m²`

/** montant compact (cartes, badges) : 450 k€ / 2 M€ / 2,4 M€ */
export const fmtEurCompact = (n: number | null | undefined): string => {
  if (n == null) return '—'
  if (n >= 1_000_000) return `${fmtDec(n / 1_000_000, n % 1_000_000 === 0 ? 0 : 1)} M€`
  if (n >= 10_000) return `${fmtInt(n / 1000)} k€`
  return fmtEur(n)
}

/** pourcentage entier : 74 % */
export const fmtPct = (n: number | null | undefined): string =>
  n == null ? '—' : `${Math.round(n)} %`

/** date courte lisible : 12 juil. 2026 (jamais un ISO brut à l'écran) */
export const fmtDate = (d: string | Date | null | undefined): string => {
  if (!d) return '—'
  const dt = typeof d === 'string' ? new Date(d) : d
  return Number.isNaN(dt.getTime()) ? '—'
    : dt.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })
}

/** date numérique compacte (tables) : 12/07/2026 */
export const fmtDateNum = (d: string | Date | null | undefined): string => {
  if (!d) return '—'
  const dt = typeof d === 'string' ? new Date(d) : d
  return Number.isNaN(dt.getTime()) ? '—' : dt.toLocaleDateString('fr-FR')
}

/** B4 (BLOC B) — libellés BRUTS de source (PPR/Géorisques) : « INONDATION_MOUVEMENT_DE_TERRAIN »
 *  → « Inondation mouvement de terrain ». AFFICHAGE SEULEMENT, données intactes. Ne touche que
 *  les chaînes qui crient (tout-majuscules avec au moins un mot ≥ 4 lettres) ; les acronymes
 *  courts (PPR, ZAC…) et les mots-outils restent dignes. */
const STOP_FR = new Set(['DE', 'DU', 'LA', 'LE', 'LES', 'DES', 'ET', 'EN', 'AUX', 'AU', 'SUR', 'D', 'L'])
export const fmtLibelleBrut = (v: string | null | undefined): string => {
  if (!v) return v ?? ''
  const brut = v.replace(/_/g, ' ').trim()
  const mots = brut.split(/\s+/)
  const crie = /^[A-ZÀ-Ý0-9 '\-()/.]+$/.test(brut) && mots.some((m) => m.length >= 4)
  if (!crie) return v
  // la longueur se juge sur le cœur alphanumérique — « (R2) » reste « (R2) »
  const bas = mots.map((m) => {
    const coeur = m.replace(/[^A-ZÀ-Ý0-9]/g, '')
    return coeur.length <= 3 && !STOP_FR.has(coeur) ? m : m.toLowerCase()
  })
  const out = bas.join(' ')
  return out.charAt(0).toUpperCase() + out.slice(1)
}
