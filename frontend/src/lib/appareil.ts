// CHARGEMENT-1 (point 6) — LABUSE est un outil de bureau. Sur téléphone/tablette on n'ouvre PAS
// l'app : on affiche un écran unique qui renvoie vers l'ordinateur. La détection est faite UNE FOIS
// AU CHARGEMENT (pas au redimensionnement) : une fenêtre de bureau simplement rétrécie n'est donc
// jamais bloquée si l'ÉCRAN physique fait plus de 1 024 px.
//
// Règle (un seul des critères suffit) :
//   • appareil mobile/tablette annoncé par l'UA (Android, iPhone, iPad…) ;
//   • iPad récent — il se présente comme un Mac : plateforme Mac + écran tactile = tablette ;
//   • pointeur principal tactile (doigt), pas une souris ;
//   • largeur de l'écran physique < 1 024 px.
export function estAppareilMobile(): boolean {
  if (typeof navigator === 'undefined' || typeof window === 'undefined') return false
  const ua = navigator.userAgent || ''
  const tactile = (navigator.maxTouchPoints || 0) > 1
  const plateforme = navigator.platform || ''
  // iPad iOS 13+ ment sur son identité (« MacIntel ») : un Mac tactile EST un iPad.
  const iPadDeguiseEnMac = plateforme === 'MacIntel' && tactile
  const mobileUA = /Android|iPhone|iPod|iPad|Mobile|Tablet|BlackBerry|IEMobile|Opera Mini/i.test(ua)
  const pointeurTactilePrincipal =
    typeof window.matchMedia === 'function' && window.matchMedia('(pointer: coarse)').matches
  const largeurEcran = window.screen && window.screen.width ? window.screen.width : 9999
  const petitEcran = largeurEcran < 1024
  return mobileUA || iPadDeguiseEnMac || (tactile && pointeurTactilePrincipal) || petitEcran
}
