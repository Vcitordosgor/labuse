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

/** COHERENCE-FIX-1 (lot B) — % de densité consommée (SDP ou emprise) : exact jusqu'à 300,
 *  « > 300 » au-delà (bâti très au-delà du plafond de zone — le chiffre exact n'apporte rien
 *  au client, l'« i » porte le détail), « — » si absent (jamais un 0 à la place d'une absence).
 *  Rend la PARTIE NOMBRE seule (l'appelant pose l'unité %) pour garder les <small>%</small>. */
export const PCT_CONSOMME_SEUIL = 300
export const fmtPctConsomme = (n: number | null | undefined): string =>
  n == null ? '—' : n > PCT_CONSOMME_SEUIL ? '> 300' : String(Math.round(n))

/** CHASSE-INVARIANTS-FIX-1 (Lot 1, E-01) — TAUX D'OCCUPATION DU GABARIT (emprise bâtie ÷ emprise
 *  constructible). Au-delà de 100 % on n'affiche JAMAIS le pourcentage brut (c'était le « 19 569 % »
 *  de l'export) : le message « Saturé … » unique, mirroir du Python `fmt_taux_emprise`. '—' si absent. */
export const TAUX_EMPRISE_SATURE = 'Saturé : le bâti existant dépasse déjà le plafond d\'emprise du PLU actuel'
export const fmtTauxEmprise = (n: number | null | undefined): string => {
  if (n == null) return '—'
  const r = Math.round(n)              // on compare la valeur ARRONDIE (celle servie), comme le Python
  return r > 100 ? TAUX_EMPRISE_SATURE : `${r} %`
}

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

/** OUTILS-FIX-4 A3 — date Sit@del à granularité VARIABLE : la source ne connaît souvent que l'ANNÉE,
 *  stockée « AAAA-01-01 » (83 % des permits). La rendre « 01/01/2024 » ment sur la précision. Quand la
 *  date tombe au 1ᵉʳ janvier (= année seule connue), on affiche l'ANNÉE (« 2024 ») ; sinon la date réelle
 *  (jour/mois de mesure, format numérique). Présentation pure — aucune valeur inventée. */
export const fmtDateSitadel = (d: string | Date | null | undefined): string => {
  if (!d) return '—'
  const dt = typeof d === 'string' ? new Date(d) : d
  if (Number.isNaN(dt.getTime())) return '—'
  return dt.getMonth() === 0 && dt.getDate() === 1 ? String(dt.getFullYear()) : dt.toLocaleDateString('fr-FR')
}

/** FICHE-FIX-4 (Lot B) — Date SIRENE : la valeur « 1900 » (souvent 1900-01-01) = date de création
 *  INCONNUE chez l'INSEE, pas une vraie création → « n.c. ». Sinon JJ/MM/AAAA. Présentation pure. */
export const fmtDateSirene = (d: string | Date | null | undefined): string => {
  if (!d) return 'n.c.'
  const dt = typeof d === 'string' ? new Date(d) : d
  if (Number.isNaN(dt.getTime()) || dt.getFullYear() <= 1901) return 'n.c.'
  return dt.toLocaleDateString('fr-FR')
}

/** FICHE-FIX-4 (Lot B) — ANNÉE de création SIRENE (tuile « Créée · état ») : « 2005 », ou « n.c. »
 *  quand la source ne connaît que 1900 (année sentinelle). Accepte une date ISO ou une année. */
export const anneeSirene = (d: string | number | null | undefined): string => {
  if (d == null || d === '') return 'n.c.'
  const an = typeof d === 'number' ? d : parseInt(String(d).slice(0, 4), 10)
  return !Number.isFinite(an) || an <= 1901 ? 'n.c.' : String(an)
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

/** RECETTE-2 (T5) — distance : « 850 m » / « 1,25 km » (virgule décimale, unité collée). Entrée en mètres. */
export const fmtDist = (m: number | null | undefined): string =>
  m == null ? '—' : m < 1000 ? `${fmtInt(m)} m` : `${fmtDec(m / 1000, m % 1000 === 0 ? 0 : 2)} km`

/** RECETTE-2 (T5) — durée en années : « 1,1 an » / « 2,5 ans » (virgule, pluriel à partir de 2). */
export const fmtAns = (n: number | null | undefined, p = 1): string => {
  if (n == null) return '—'
  const txt = fmtDec(n, p)
  return `${txt} ${n < 2 ? 'an' : 'ans'}`
}

/** RECETTE-2 (T6) — intensité d'aléa : plus de code brut (`tres_fort` → « très fort »). */
const INTENSITE: Record<string, string> = {
  tres_faible: 'très faible', faible: 'faible', moyen: 'moyen', modere: 'modéré', moyennement_fort: 'moyennement fort',
  fort: 'fort', tres_fort: 'très fort', nul: 'nul', inconnu: 'inconnu',
}
export const fmtIntensite = (v: string | null | undefined): string =>
  v == null ? '—' : (INTENSITE[v.toLowerCase()] ?? v.replace(/_/g, ' '))

/** RECETTE-2 (T6) — nature d'aléa : plus de code brut (`mouvement_terrain` → « mouvement de terrain »). */
const ALEA: Record<string, string> = {
  mouvement_terrain: 'mouvement de terrain', inondation: 'inondation', inondation_crue: 'inondation (crue)',
  submersion_marine: 'submersion marine', houle: 'houle', cyclone: 'cyclone', vent_cyclonique: 'vent cyclonique',
  feux_foret: 'feux de forêt', feu_foret: 'feu de forêt', seisme: 'séisme', volcan: 'volcanique',
  eruption_volcanique: 'éruption volcanique', retrait_gonflement_argiles: 'retrait-gonflement des argiles',
  argiles: 'retrait-gonflement des argiles', radon: 'radon', chute_blocs: 'chute de blocs',
  glissement_terrain: 'glissement de terrain', rupture_barrage: 'rupture de barrage', tsunami: 'tsunami',
}
export const fmtAlea = (v: string | null | undefined): string =>
  v == null ? '—' : (ALEA[v.toLowerCase()] ?? v.replace(/_/g, ' '))

/** RECETTE-2 (A5c/T6) — libellé d'une servitude d'utilité publique (SUP) depuis sa catégorie
 *  (nomenclature nationale GPU). Code connu → libellé officiel ; inconnu → « Servitude <code> »
 *  (jamais un code brut à underscores comme « EL10_Reunion_ass »). Le code exact reste dans le `i`. */
const SUP_LABELS: Record<string, string> = {
  AC1: 'Monuments historiques', AC2: 'Sites inscrits et classés', AC4: 'Secteur sauvegardé / AVAP',
  AS1: 'Protection des eaux potables et minérales', A1: 'Forêts de protection',
  A4: "Servitude de passage le long des cours d'eau", A5: "Canalisations d'eau et d'assainissement",
  EL3: 'Halage et marchepied', EL7: 'Alignement des voies', EL9: 'Accès au rivage',
  EL11: 'Routes express et déviations', I3: 'Canalisations de gaz', I4: "Lignes électriques",
  I6: 'Stockage souterrain de gaz', PT1: 'Protection des réceptions radioélectriques',
  PT2: 'Protection des transmissions radioélectriques', PT3: 'Réseaux de télécommunications',
  T1: 'Voies ferrées', T5: 'Dégagement des aérodromes', T7: 'Balisage aéronautique',
  PM1: 'Plan de prévention des risques naturels', PM2: 'Risques technologiques', PM3: 'Risques miniers',
  INT1: 'Voisinage des cimetières',
}
export const fmtSup = (categorie: string | null | undefined): string => {
  if (!categorie) return 'Servitude'
  const c = categorie.toUpperCase().trim()
  return SUP_LABELS[c] ?? `Servitude ${c}`
}
