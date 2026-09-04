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
