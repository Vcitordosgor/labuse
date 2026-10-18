/** FIX-PRIX-ET-OPPORTUNITES (lot 1) — fourchette d'incertitude UNIQUE pour toute valeur de parcelle ESTIMÉE.
 *
 *  Miroir TypeScript de `src/labuse/estimation_prix.py` — les deux DOIVENT rester synchrones (même
 *  demi-largeur, même mention). Suite de VERITE-TERRAIN-2 (volet E) : le backtest prix a mesuré qu'une
 *  estimation « médiane du secteur × surface » s'écarte en médiane de 27 % du prix réel (17,5 % des
 *  ventes à ±10 %, 36,5 % à ±20 %, biais −5,6 %). Conséquence : plus aucune valeur estimée en chiffre
 *  sec — elle s'affiche en FOURCHETTE ±30 % avec une mention d'incertitude courte et vraie.
 *
 *  Demi-largeur ±30 % : au moins aussi large que l'écart médian mesuré (27,4 %) — le backtest porte sur
 *  l'estimateur sobre qui majore l'erreur du produit, la fourchette est donc prudente. */
import { fmtInt } from './format'

/** demi-largeur de la fourchette (±), en %. */
export const FOURCHETTE_DEMI_LARGEUR_PCT = 30

/** mention complète (survol / détail) — une phrase, chiffres mesurés. */
export const FOURCHETTE_MENTION =
  `Estimation indicative, pas une valeur vénale : fourchette ±${FOURCHETTE_DEMI_LARGEUR_PCT} %. ` +
  'Au dernier backtest (ventes DVF, VERITE-TERRAIN-2), ce type d’estimation s’écarte en médiane de ' +
  '27 % du prix réel et seulement 37 % des ventes tombaient à ±20 %.'

/** mention courte (chip / inline). */
export const FOURCHETTE_MENTION_COURTE =
  `estimation ±${FOURCHETTE_DEMI_LARGEUR_PCT} % (écart médian mesuré 27 %)`

const K = FOURCHETTE_DEMI_LARGEUR_PCT / 100

export type Fourchette = { centre: number; bas: number; haut: number }

/** pas d'arrondi lisible selon l'ordre de grandeur (jamais une borne à l'euro près sur une estimation). */
function pasArrondi(v: number): number {
  const a = Math.abs(v)
  if (a >= 1_000_000) return 50_000
  if (a >= 100_000) return 10_000
  if (a >= 10_000) return 1_000
  if (a >= 1_000) return 100
  return 50
}

/** arrondit une borne à son pas : bas vers le bas, haut vers le haut → la fourchette encadre la valeur. */
function arrondir(v: number, sens: 'bas' | 'haut'): number {
  const pas = pasArrondi(v)
  return (sens === 'bas' ? Math.floor(v / pas) : Math.ceil(v / pas)) * pas
}

/** Fourchette d'incertitude autour d'une valeur estimée (euros). null si valeur absente — on ne
 *  fabrique jamais une fourchette sur une absence. Bornes ARRONDIES (bas vers le bas, haut vers le
 *  haut) et ordonnées (la marge peut être négative). */
export function fourchette(valeur: number | null | undefined): Fourchette | null {
  if (valeur == null) return null
  const b1 = arrondir(valeur * (1 - K), 'bas')
  const b2 = arrondir(valeur * (1 + K), 'haut')
  const [bas, haut] = b1 <= b2 ? [b1, b2] : [b2, b1]
  return { centre: Math.round(valeur), bas, haut }
}

/** « 260 000 – 480 000 € » (tiret demi-cadratin, € une seule fois). null si valeur absente. */
export function fourchetteLibelleEur(valeur: number | null | undefined): string | null {
  const f = fourchette(valeur)
  if (f == null) return null
  return `${fmtInt(f.bas)} – ${fmtInt(f.haut)} €`
}
