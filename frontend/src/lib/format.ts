/** LOI-3 (revue UI/UX) — LES formats de l'app. Un nombre, une date, un montant :
 *  le même dessin partout (fr-FR, insécables, unités collées au chiffre).
 *  Aucun `toLocaleString` inline dans les surfaces : on passe par ici.
 *
 *  CIRCUIT-1 lot 7.2 — chaque formateur ACCEPTE un `chiffreId` optionnel (id du registre).
 *  Il est NO-OP sur la chaîne rendue (le rendu éteint est identique par construction) : c'est
 *  une DÉCLARATION au point d'appel — l'étiquette visuelle vit dans le composant `Trace`
 *  (lib/trace.tsx), posé sur les points d'affichage (LigneCarte, ScoreV2Block…). */


/** entier groupé fr : 431 663 */
export const fmtInt = (n: number | null | undefined, _chiffreId?: string): string =>
  n == null ? '—' : Math.round(n).toLocaleString('fr-FR')

/** décimal fr à p décimales (défaut 1) : 63,9 */
export const fmtDec = (n: number | null | undefined, p = 1, _chiffreId?: string): string =>
  n == null ? '—' : n.toLocaleString('fr-FR', { minimumFractionDigits: p, maximumFractionDigits: p })

/** montant € entier : 245 000 € (espace insécable avant €) */
export const fmtEur = (n: number | null | undefined, _chiffreId?: string): string =>
  n == null ? '—' : `${fmtInt(n)} €`

/** surface : 1 245 m² / 2,50 ha au-delà d'un hectare */
export const fmtM2 = (m2: number | null | undefined, _chiffreId?: string): string =>
  m2 == null ? '—' : m2 >= 10_000 ? `${fmtDec(m2 / 10_000, 2)} ha` : `${fmtInt(m2)} m²`

/** montant compact (cartes, badges) : 450 k€ / 2 M€ / 2,4 M€ */
export const fmtEurCompact = (n: number | null | undefined): string => {
  if (n == null) return '—'
  if (n >= 1_000_000) return `${fmtDec(n / 1_000_000, n % 1_000_000 === 0 ? 0 : 1)} M€`
  if (n >= 10_000) return `${fmtInt(n / 1000)} k€`
  return fmtEur(n)
}

/** pourcentage entier : 74 % */
export const fmtPct = (n: number | null | undefined, _chiffreId?: string): string =>
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

/** Date relative FR courte : « à l'instant », « il y a 5 min », « il y a 2 h », « il y a 3 j »,
 *  au-delà d'une semaine la date. Pour l'historique du Copilote (M78-quater #2). */
export const ilYA = (d: string | Date | null | undefined): string => {
  if (!d) return ''
  const t = new Date(d).getTime()
  if (Number.isNaN(t)) return ''
  const s = Math.max(0, Math.floor((Date.now() - t) / 1000))
  if (s < 60) return "à l'instant"
  const m = Math.floor(s / 60)
  if (m < 60) return `il y a ${m} min`
  const h = Math.floor(m / 60)
  if (h < 24) return `il y a ${h} h`
  const j = Math.floor(h / 24)
  if (j < 7) return `il y a ${j} j`
  return fmtDate(d)
}

/** IDU cadastral = code INSEE(5) + préfixe de section(3) + section(2) + numéro(4) = 14 car.
 *  LE SEUL formateur d'IDU de l'app (LOI-3 : un dessin, un seul endroit). Deux formes :
 *  - `iduComplet` : la chaîne BRUTE 14 car., sans espace ni séparateur. C'est elle qu'on
 *    affiche en position primaire et qu'on copie — collable telle quelle dans GPU/DVF/SIG.
 *  - `iduCourt`   : section + numéro (« IL 0061 »). AFFICHAGE SECONDAIRE uniquement, jamais
 *    à la place de la forme complète.
 *  Boussole : ne JAMAIS reconstruire un IDU absent — chaîne vide → chaîne vide (l'appelant
 *  affiche « Absent »). */
export const iduComplet = (idu: string | null | undefined): string =>
  (idu ?? '').trim().replace(/\s+/g, '')

export const iduCourt = (idu: string | null | undefined): string => {
  const s = iduComplet(idu)
  return s.length >= 14 ? `${s.slice(8, 10)} ${s.slice(10)}` : s
}

/** RECONNAISSANCE D'UN IDU (patron omnibox M137) — LE SEUL endroit où vit cette règle (LOI-3).
 *  Un IDU cadastral commence par ≥ 5 chiffres (code INSEE), suite contiguë sans espace, 6–14 car.
 *  On l'utilise pour distinguer, DANS UN SEUL CHAMP, une référence cadastrale d'une adresse : sur un
 *  IDU on N'interroge PAS la BAN (elle répondrait « aucune adresse » à tort). Partagé par
 *  AddressAutocomplete (skip BAN) et ParcelInput (aiguillage IDU/adresse) — chemin unique. */
export const estIdu = (s: string): boolean => /^\d{5}[0-9A-Za-z]{1,9}$/.test(iduComplet(s))

/** RETOURS-12 T1 — RÉFÉRENCE CADASTRALE COURTE (section + numéro), « le chiffre que les pros
 *  citent le plus ». Formes acceptées : `BW0917`, `BW 917`, `bw 0917`, `BW-917`. LE SEUL endroit
 *  où vit cette règle (LOI-3). Distincte d'un IDU (qui commence par 5 chiffres) : ici 1–2 lettres
 *  de section suivies de 1–4 chiffres de numéro. Sert d'aiguillage : sur une référence courte on
 *  N'interroge PAS la BAN, on résout via /parcels/search (fin d'IDU) avec désambiguïsation commune. */
export const estSectionNumero = (s: string): boolean =>
  /^[A-Za-z]{1,2}[\s-]?\d{1,4}$/.test((s ?? '').trim())

/** Normalise une référence courte : majuscules, sans espace ni tiret, numéro sur 4 chiffres
 *  (zéros de tête) — la forme que /parcels/search matche en fin d'IDU (« BW0917 »). */
export const normSectionNumero = (s: string): string => {
  const m = (s ?? '').trim().toUpperCase().replace(/[\s-]/g, '').match(/^([A-Z]{1,2})(\d{1,4})$/)
  if (!m) return (s ?? '').trim().toUpperCase().replace(/[\s-]/g, '')
  const [, sec, num] = m
  return `${sec.padStart(2, '0')}${num.padStart(4, '0')}`
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
