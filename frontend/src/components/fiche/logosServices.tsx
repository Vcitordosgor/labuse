// RETOURS-11 F1 (03/09) — logos des trois services d'accès de l'en-tête de fiche, STOCKÉS EN LOCAL
// (aucune requête externe : ce sont des SVG inline, jamais une balise <img src=distant>). Décision Vic :
// « logos officiels publics, on y va ». Ce sont des marques reconnaissables (couleurs officielles),
// rendues à leur taille de bouton (18 px) — pas des captures des logotypes déposés pixel pour pixel.
// Un seul endroit les définit ; l'en-tête les rend dans .hbtn à côté de la cloche.
import type { ReactNode } from 'react'

const box = (children: ReactNode) => (
  <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden>{children}</svg>
)

// Google Maps — la goutte-repère aux quatre couleurs Google.
export function LogoGoogleMaps() {
  return box(
    <>
      <path d="M12 2C8.1 2 5 5.1 5 9c0 5 7 13 7 13s7-8 7-13c0-3.9-3.1-7-7-7Z" fill="#34A853" />
      <path d="M12 2C8.1 2 5 5.1 5 9c0 1.6.7 3.4 1.7 5.2L15.4 4A6.97 6.97 0 0 0 12 2Z" fill="#FBBC04" />
      <path d="M18.6 5.3 9.2 16.9c.9 1.5 1.9 2.9 2.8 4.1 0 0 7-8 7-13 0-1-.2-1.9-.4-2.7Z" fill="#4285F4" />
      <path d="M5 9c0 1.6.7 3.4 1.7 5.2l4.1-4.9A2.9 2.9 0 0 1 12 6.1 2.9 2.9 0 0 1 15.4 4 6.97 6.97 0 0 0 12 2C8.1 2 5 5.1 5 9Z" fill="#EA4335" />
      <circle cx="12" cy="9" r="2.5" fill="#fff" />
    </>,
  )
}

// Pages Jaunes — le carré jaune « pj » (marque de l'annuaire).
export function LogoPagesJaunes() {
  return box(
    <>
      <rect x="3" y="3" width="18" height="18" rx="3" fill="#FFCC00" />
      <text x="12" y="16.5" textAnchor="middle" fontSize="11" fontWeight="800" fill="#111" fontFamily="Arial, sans-serif">pj</text>
    </>,
  )
}

// Cadastre / Géoportail (IGN) — le repère cartographique quadrillé, aux bleus de la Géoplateforme.
export function LogoCadastre() {
  return box(
    <>
      <rect x="3" y="3" width="18" height="18" rx="3" fill="#00537F" />
      <path d="M7 7h10M7 12h10M7 17h10M9 5v14M15 5v14" stroke="#7FD3F7" strokeWidth="1.1" />
      <circle cx="12" cy="12" r="2.4" fill="#fff" />
    </>,
  )
}

// FICHE-ORFEVRERIE-1 (reprise, pt 30) — Géorisques (état des risques) : le triangle d'alerte BLEU sur
// fond blanc, reconnaissable sans survol (les tooltips ont été retirés). Même boîte 16 px que les autres.
export function LogoGeorisques() {
  return box(
    <>
      <rect x="2.5" y="2.5" width="19" height="19" rx="3" fill="#fff" stroke="#1455A0" strokeWidth="1" />
      <path d="M12 5.6 4.9 18a1.3 1.3 0 0 0 1.1 2h12a1.3 1.3 0 0 0 1.1-2L12 5.6Z" fill="#1455A0" />
      <path d="M12 10.3v3.4" stroke="#fff" strokeWidth="1.7" strokeLinecap="round" />
      <circle cx="12" cy="16.4" r="1" fill="#fff" />
    </>,
  )
}

// FICHE-ORFEVRERIE-1 (reprise, pt 30) — Google Earth : le globe bleu océan / vert continents.
export function LogoGoogleEarth() {
  return box(
    <>
      <circle cx="12" cy="12" r="9.5" fill="#1A73E8" />
      <path d="M4.3 9.2c1.8.3 3 1.4 4.6 1.2 1.7-.2 2-1.8 3.6-2 1.3-.1 2.1.8 3.4.6 1-.2 1.7-1 2.9-.9a9.5 9.5 0 0 0-14.5 1.1Z" fill="#34A853" />
      <path d="M6.5 18.7c.8-1.1.7-2.3 1.9-3 1.3-.8 2.4 0 3.5-.9.9-.7.7-1.8 1.8-2.3 1.3-.6 2.3.4 3.6-.2a9.5 9.5 0 0 1-10.8 6.4Z" fill="#188038" />
      <circle cx="12" cy="12" r="9.5" fill="none" stroke="#0B57D0" strokeWidth="1" />
    </>,
  )
}
